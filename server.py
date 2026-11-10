"""Chat WebSocket con una sola dipendenza (websockets >= 13). Tutto il resto è libreria standard.

Protocollo testuale: ogni messaggio è una riga che termina con \\n e usa "|" come separatore.

Client -> Server
    L|id_utente|password\\n              login
    R|id_utente|password\\n              registrazione (estensione: serve per creare gli utenti)
    M|id_utente|timestamp|corpo\\n       messaggio di chat (dopo il login)

Server -> Client
    C|Login effettuato\\n                esito positivo
    C|errore credenziali\\n              esito negativo (o altro errore: "C|errore <motivo>\\n")
    M|id_utente|timestamp|corpo\\n       messaggio inoltrato a tutti
    U|id_utente1|id_utente2|...\\n       lista degli utenti online

Note: mittente e timestamp (ISO 8601) dei messaggi inoltrati sono sempre impostati dal server,
così un client non può spacciarsi per un altro utente.
"""
import asyncio
import hashlib
import hmac
import os
import re
import sqlite3
from contextlib import closing
from datetime import datetime
from http import HTTPStatus
from pathlib import Path

from websockets import broadcast
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

HOST, PORT = "0.0.0.0", 8000
DB_PATH = "chat.db"
PAGINA = Path(__file__).with_name("index.html")
MAX_TENTATIVI = 5

utenti: dict[str, object] = {}  # id_utente -> connessione attiva


# --- Database e password (libreria standard) --------------------------------
def esegui(sql: str, params: tuple = ()):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        with conn:  # commit automatico
            return conn.execute(sql, params).fetchone()


# PRIMARY KEY + COLLATE NOCASE: "Marco" e "marco" sono lo stesso utente
# e l'unicità è garantita dal database anche con richieste simultanee.
esegui(
    "CREATE TABLE IF NOT EXISTS utenti ("
    "nome TEXT PRIMARY KEY COLLATE NOCASE, salt BLOB NOT NULL, hash BLOB NOT NULL)"
)


def calcola_hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)


def registra(nome: str, password: str):
    salt = os.urandom(16)
    try:
        esegui("INSERT INTO utenti VALUES (?, ?, ?)", (nome, salt, calcola_hash(password, salt)))
    except sqlite3.IntegrityError:
        return None, "nickname già in uso"
    return nome, None


def verifica(nome: str, password: str):
    riga = esegui("SELECT nome, salt, hash FROM utenti WHERE nome = ?", (nome,))
    # Hash calcolato anche se l'utente non esiste: stesso tempo di risposta.
    salt = riga[1] if riga else bytes(16)
    atteso = riga[2] if riga else bytes(32)
    corretta = hmac.compare_digest(calcola_hash(password, salt), atteso)
    if riga and corretta:
        return riga[0], None
    return None, "credenziali"


# --- Protocollo -------------------------------------------------------------
def adesso() -> str:
    """Timestamp ISO 8601 con fuso orario, es. 2026-10-30T14:05:09+01:00"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def pulisci(testo: str) -> str:
    """Il '\\n' è il terminatore del messaggio: non può comparire nel corpo."""
    return " ".join(testo.splitlines()).strip()


async def rispondi(ws, tipo: str, testo: str):
    await ws.send(f"{tipo}|{testo}\n")


def invia_messaggio(autore: str, corpo: str):
    riga = f"M|{autore}|{adesso()}|{corpo}\n"
    broadcast(list(utenti.values()), riga)


def invia_lista_utenti():
    riga = "U|" + "|".join(sorted(utenti)) + "\n"
    broadcast(list(utenti.values()), riga)


# --- Autenticazione ---------------------------------------------------------
async def autentica(ws) -> str | None:
    """Gestisce il primo scambio. Restituisce l'id_utente, o None se fallisce."""
    for _ in range(MAX_TENTATIVI):
        grezzo = await asyncio.wait_for(ws.recv(), timeout=30)

        # Formato atteso: L|id_utente|password  (la password può contenere '|')
        parti = grezzo.rstrip("\r\n").split("|", 2) if isinstance(grezzo, str) else []
        if len(parti) != 3 or parti[0] not in ("L", "R"):
            await rispondi(ws, "C", "errore richiesta non valida")
            continue
        comando, nome, password = parti

        if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", nome):
            await rispondi(ws, "C", "errore nickname: 3-20 caratteri (lettere, numeri, _)")
            continue
        if comando == "R" and not 8 <= len(password) <= 128:
            await rispondi(ws, "C", "errore la password deve avere almeno 8 caratteri")
            continue

        funzione = registra if comando == "R" else verifica
        # scrypt è volutamente lento: lo spostiamo in un thread per non bloccare gli altri utenti
        nome_valido, errore = await asyncio.to_thread(funzione, nome, password)
        if errore:
            await rispondi(ws, "C", f"errore {errore}")
            continue
        return nome_valido

    await ws.close(4003, "Troppi tentativi")
    return None


# --- Handler della connessione ----------------------------------------------
async def chat(ws):
    nome = None
    try:
        nome = await autentica(ws)
        if nome is None:
            return
        await rispondi(ws, "C", "Login effettuato")

        vecchia = utenti.get(nome)
        utenti[nome] = ws
        if vecchia:  # stesso utente da un'altra scheda: chiudiamo la sessione vecchia
            await vecchia.close(4000, "Accesso da un'altra sessione")
        invia_lista_utenti()

        async for grezzo in ws:  # il ciclo termina da solo alla chiusura
            if not isinstance(grezzo, str):
                continue
            # Formato atteso: M|id_utente|timestamp|corpo  (il corpo può contenere '|')
            parti = grezzo.rstrip("\r\n").split("|", 3)
            if len(parti) != 4 or parti[0] != "M":
                continue
            corpo = pulisci(parti[3])[:500]
            if corpo:
                # mittente e timestamp sono quelli del server, non quelli dichiarati dal client
                invia_messaggio(nome, corpo)

    except (ConnectionClosed, TimeoutError):
        pass
    finally:
        # Rimuoviamo l'utente solo se la connessione registrata è ancora questa
        if nome and utenti.get(nome) is ws:
            del utenti[nome]
            invia_lista_utenti()


# --- Pagina HTML servita sulla stessa porta ---------------------------------
async def serve_pagina(connection, request):
    if request.path == "/ws":
        return None  # prosegue con l'handshake WebSocket
    if request.path == "/":
        risposta = connection.respond(HTTPStatus.OK, PAGINA.read_text(encoding="utf-8"))
        del risposta.headers["Content-Type"]
        risposta.headers["Content-Type"] = "text/html; charset=utf-8"
        return risposta
    return connection.respond(HTTPStatus.NOT_FOUND, "Non trovato\n")


async def main():
    async with serve(chat, HOST, PORT, process_request=serve_pagina, max_size=4096) as server:
        print(f"Chat attiva su http://{HOST}:{PORT}")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
