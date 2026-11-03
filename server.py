import asyncio
from http import HTTPStatus
from pathlib import Path

from websockets import broadcast
from websockets.asyncio.server import serve

HOST, PORT = "127.0.0.1", 8000
PAGINA = Path(__file__).with_name("index.html")

connessioni = set()


async def chat(ws):
    connessioni.add(ws)
    try:
        async for messaggio in ws:
            broadcast(connessioni, messaggio)  # per ora rimandiamo tutto a tutti
    finally:
        connessioni.discard(ws)


async def serve_pagina(connection, request):
    if request.path == "/ws":
        return None
    if request.path == "/":
        return connection.respond(HTTPStatus.OK, PAGINA.read_text(encoding="utf-8"))
    return connection.respond(HTTPStatus.NOT_FOUND, "Non trovato\n")


async def main():
    async with serve(chat, HOST, PORT, process_request=serve_pagina) as server:
        print(f"Chat attiva su http://{HOST}:{PORT}")
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
