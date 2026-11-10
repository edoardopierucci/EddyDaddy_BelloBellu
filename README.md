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
Il protocollo è testuale. Ogni messaggio è una riga che termina con \n e usa | come separatore. Il primo campo indica il tipo di messaggio. Il timestamp è definito da ISO 8601. Il server accetta anche righe senza \n finale.
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
**COME SI AVVIA IL SERVER DI EDDYDADDY E BELLOBELLU?**
Per prima cosa entriamo nel terminale, poi con il comando "cd desktop/chat" entriamo nella cartella chat\ presente nel desktop.
Una volta entrati bisogna attivare il venv con il comando "source venv/bin/activate", che dovrà dare come risultato "(venv) federicobellucci@air03 chat %".
Come ultimo passaggio bisogna scrivere il comando "python server.py", se tutto è andato bene nel terminale comparirà la scritta "Chat attiva su http://0.0.0.0:8000".


