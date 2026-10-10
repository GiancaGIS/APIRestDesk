# Adeguamento della distribuzione alle licenze

10 ottobre 2026. Percorso autorizzato dal titolare: GNU GPL versione 3 soltanto (`GPL-3.0-only`). Questo aggiornamento documenta le correzioni successive a `LICENSE_AUDIT.md`; non certifica la conformità di tutte le distribuzioni precedenti.

## Correzioni nel progetto

- `LICENSE` contiene il testo originale GPLv3; `COPYRIGHT` conserva titolarità, data dell'aggiornamento, assenza di garanzia e diritti di redistribuzione. La precedente concessione MIT è conservata separatamente.
- README, metadati PEP 639 e schermata Informazioni dichiarano GPLv3. Il menu Licenze e sorgenti apre i documenti installati.
- Testi originali delle licenze e attribuzioni sono raccolti in `licenses/`, con una copia sincronizzata in `api_rest_desk/legal/` per eseguibili e pacchetti Python. I file Qt conservano i percorsi di provenienza e le attribuzioni della versione esatta.
- PyInstaller include questi documenti nel bundle, quindi Inno Setup li copia nell'installazione. Il wizard mostra il testo GPLv3 come informazione, senza imporre l'accettazione di un contratto per usare il programma.
- PDF e fallback software OpenGL, inutilizzati dal tool, sono esclusi dal bundle.
- Versioni runtime e di build sono vincolate; un controllo impedisce di usare un inventario legale non aggiornato rispetto all'ambiente verificato.
- `SOURCE_MANIFEST.toml` registra sorgenti e checksum. La procedura prepara separatamente sorgenti dell'app e archivi originali delle dipendenze, senza includere le raccolte JSON locali, `.venv` o file `.env`.
- La preparazione della release controlla documenti installati, checksum dei sorgenti, moduli Qt e dipendenze Python, e confronta il codice Python dell'app congelato con il codice sorgente corrente. Produce anche l'inventario dei file nativi effettivamente inclusi.

## Materiali da pubblicare insieme al nuovo installer

La procedura deposita i materiali in `dist/release/`: installer/ZIP binario, ZIP del codice applicativo, ZIP dei sorgenti delle dipendenze, inventario nativo, checksum e note della release con collegamenti ai sorgenti.

Gli archivi locali non sono accessibili agli utenti di GitHub finché non vengono caricati. Pubblicare tutti i materiali sullo stesso tag, con i collegamenti delle note accanto al download binario. Gli script non effettuano upload.

## Verifiche e limiti residui

Sono passati 48 test automatici. Sono state verificate la dichiarazione GPL-3.0-only nei metadati wheel, la presenza dei documenti legali nel pacchetto Python e nella build Windows, le licenze integrali GPL/LGPL, la corrispondenza del codice congelato con i sorgenti e l'esclusione dei componenti nativi inutilizzati. La build Windows si è avviata senza errori immediati con dati di prova isolati e aggiornamenti disabilitati; l'installer è stato compilato con Inno Setup 6.7.3. Non è stata eseguita un'installazione sul sistema dell'utente. La validazione corrente riguarda Windows; le procedure macOS devono essere provate su macOS prima di distribuirne un pacchetto.

Rimangono da verificare la provenienza e gli eventuali patch dei wheel binari upstream, le condizioni di redistribuzione dei runtime Microsoft, i componenti nativi non identificabili dai soli metadati e la titolarità dei contenuti storici. Le versioni Windows di libffi, xz e zlib-ng derivano dalle impostazioni di build CPython 3.14.5, non da una lettura autonoma di tutte le versioni nei binari; zstd e la famiglia zlib-ng sono stati osservati nel runtime.

Gli installer 1.0.3 e 1.0.4 già online non sono stati sostituiti né estratti in questa attività. `packaging/RELEASING.md` descrive come recuperarne le versioni effettive, ricostruirli con gli avvisi corretti e rendere disponibili i relativi sorgenti. Cambiare la licenza corrente non li regolarizza automaticamente.

Nessuna dichiarazione di piena conformità legale viene dedotta dalla sola generazione di questi file.
