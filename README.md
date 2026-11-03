# EddyDaddy_BelloBellu
**Cosa stiamo facendo?**
In questo progetto stiamo sviluppando un server websocket in linguaggio python, che gestisce il login, la lista degli utenti connessi e l'inoltro dei messaggi in broadcast.
**Compiti del server**
-gestire il login per ogni utente
-ricevere il messaggio del client e inoltrarlo in broadcast
-fornire al client una lista di utenti online
-salvare le password
-impostare mittente e timestamp
**Protocollo usato**
Il protocollo è testuale. Ogni messaggio è una riga che termina con \n e usa | come separatore. Il primo campo indica il tipo di messaggio. Il timestamp  Il server accetta anche righe senza \n finale.
**Client → Server**
*Messaggio:*	                                          *  Significato:*
L|id_utente|password\n	                            Login
R|id_utente|password\n	                    Registrazione (estensione necessaria per creare gli utenti)
M|id_utente|timestamp|corpo\n	            Messaggio di chat (solo dopo il login)

**Server → Client**
*Messaggio:*                                                 *Significato:*
C|Login effettuato\n	                            Esito positivo
C|errore credenziali\n	                            Credenziali errate
C|errore <motivo>\n	                            Altro errore (richiesta non valida, nickname già in uso, ecc.)
M|id_utente|timestamp|corpo\n	            Messaggio completo inoltrato a tutti
U|id_utente1|id_utente2|...\n	                    Lista degli utenti online


