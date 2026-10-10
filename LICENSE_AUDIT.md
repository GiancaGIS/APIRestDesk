# Audit delle licenze di APIRestDesk

Data: 10 ottobre 2026. Esito: **la conformità della distribuzione non è dimostrata; sono necessarie correzioni prima di considerarla completa**.

Questo è il risultato dell'audit iniziale, precedente alle correzioni. Lo stato dell'adeguamento autorizzato successivamente è descritto in [LICENSE_REMEDIATION.md](LICENSE_REMEDIATION.md).

Questo documento è un audit tecnico e documentale, non un parere legale. Non modifica la licenza del progetto e non costituisce una certificazione dei pacchetti pubblicati.

## Ambito e prove esaminate

- `LICENSE`, `pyproject.toml`, `requirements.txt`, README, import del codice e asset presenti nel workspace.
- Specifica PyInstaller, installer Inno Setup e script Windows/macOS.
- Metadati e testi delle licenze dei pacchetti installati nella `.venv`.
- Build Windows locale `dist/APIRestDesk`: DLL, plugin, dati e contenuto degli archivi PyInstaller. Nessun eseguibile è stato avviato durante l'audit.
- Tag Git locale `1.0.4`: dipendenze e specifica PyInstaller.
- API pubblica GitHub: repository pubblico, licenza rilevata MIT, installer allegati alle release `1.0.3` e `1.0.4`. La release più recente rilevata è [1.0.4](https://github.com/GiancaGIS/APIRestDesk/releases/tag/1.0.4), con `APIRestDesk-1.0.4-Setup.exe`; la versione locale dichiarata è 1.0.5.
- Conferma del titolare del progetto: vengono utilizzati i pacchetti gratuiti PyQt installati tramite pip, senza licenza commerciale Riverbank.

Gli installer remoti non sono stati scaricati né estratti. I rilievi sul loro contenuto sono quindi da verificare sugli asset pubblicati, mentre quelli sul pacchetto locale sono osservazioni dirette. Non è stato esaminato un bundle macOS o Linux. Il workspace contiene modifiche non ancora pubblicate.

## Rilievi principali

### 1. Alta priorità: MIT sul codice e GPL sul programma distribuito

`LICENSE`, i metadati del progetto e il badge del README dichiarano MIT. PyQt6 6.11.0 installato dichiara invece `GPL-3.0-only`. Lo stesso pacchetto è una dipendenza del tag 1.0.4.

Riverbank offre PyQt sotto GPLv3 oppure licenza commerciale, **non LGPL**. Qt e PyQt hanno licenze distinte. La distribuzione dell'applicazione che integra PyQt gratuito deve rispettare i termini GPL applicabili al programma complessivo. [Licenze PyQt](https://www.riverbankcomputing.com/software/pyqt/), [FAQ Riverbank](https://www.riverbankcomputing.com/commercial/license-faq).

MIT è compatibile con GPL: non è necessario eliminare automaticamente la licenza MIT dai file originali. È però insufficiente descrivere l'intero eseguibile come soggetto soltanto a MIT. Occorre dichiarare e soddisfare i termini GPL del programma combinato, conservando le licenze e i copyright dei suoi componenti. Essere gratuito oppure avere i sorgenti su GitHub non soddisfa, da solo, tutti questi obblighi.

### 2. Alta priorità: licenze e attribuzioni assenti nella build locale

La scansione della cartella distribuita e dell'archivio dell'eseguibile non ha trovato file `LICENSE`, `COPYING`, `NOTICE` o equivalenti. La specifica PyInstaller aggiunge esplicitamente soltanto l'icona PNG tra i dati del progetto.

Inno Setup mostra il `LICENSE` MIT tramite `LicenseFile`, ma la sezione `[Files]` copia soltanto la cartella `dist/APIRestDesk`. Non installa separatamente la licenza del progetto o quelle delle dipendenze.

Serve una raccolta dei testi originali delle licenze, copyright e attribuzioni dei componenti effettivamente redistribuiti, inclusi Python e le librerie native. Un elenco di nomi o un collegamento generico a GitHub non sostituisce i testi richiesti dalle singole licenze.

### 3. Alta priorità: accesso ai sorgenti corrispondenti da documentare

Le descrizioni delle release esaminate riportano soltanto il changelog. Non è stata individuata una procedura documentata per ottenere i sorgenti corrispondenti dei componenti GPL/LGPL redistribuiti e le istruzioni necessarie alla ricostruzione.

La GPLv3, sezioni 5 e 6, richiede termini GPL sul lavoro complessivo e una modalità conforme di accesso al Corresponding Source. Per download online, la sezione 6(d) permette sorgenti su un altro server, anche di terzi, con indicazioni chiare accanto al download e responsabilità del distributore sulla disponibilità. Non basta presumere che lo ZIP automatico del repository includa anche PyQt e Qt.

Il testo GPL è stato verificato nel pacchetto locale `pyqt6-6.11.0.dist-info/licenses/LICENSE`; i tentativi di consultare il sito GNU tramite browser sono falliti. [Testo ufficiale GPLv3](https://www.gnu.org/licenses/gpl-3.0.html).

Qt LGPL richiede inoltre avvisi, testi di licenza, accesso ai sorgenti della libreria e possibilità per l'utente di sostituire o modificare le librerie secondo i termini applicabili. La disposizione attuale con DLL separate è utile, ma non dimostra da sola la conformità. [Obblighi Qt GPL/LGPL](https://www.qt.io/development/open-source-lgpl-obligations).

## Inventario delle dipendenze Python

Le versioni seguenti sono quelle dell'ambiente locale al momento dell'audit. La presenza dei pacchetti runtime è stata confermata nel contenuto PyInstaller; le versioni dei moduli Python congelati non sono state ricavate autonomamente dagli installer remoti.

| Componente | Versione locale | Licenza rilevata | Conseguenza principale |
| --- | --- | --- | --- |
| Codice APIRestDesk | 1.0.5 dichiarata | MIT | Conservare licenza e copyright; distinguere i termini dell'app combinata. |
| PyQt6 | 6.11.0 | GPL-3.0-only | Obblighi GPL sulla distribuzione che lo integra. |
| PyQt6-Qt6 | 6.11.1 | LGPLv3 dichiarata nel pacchetto | Testi, avvisi, sorgenti e condizioni LGPL; verificare i singoli moduli. |
| PyQt6-sip | 13.11.1 | BSD-2-Clause | Conservare testo e attribuzioni; non confonderlo con PyQt6. |
| httpx | 0.28.1 | BSD-3-Clause | Conservare testo, copyright e disclaimer nella distribuzione. |
| httpcore | 1.0.9 | BSD-3-Clause | Come sopra. |
| anyio | 4.14.2 | MIT | Conservare testo e copyright. |
| h11 | 0.16.0 | MIT | Conservare testo e copyright. |
| idna | 3.18 | BSD-3-Clause | Conservare testo, copyright e disclaimer. |
| certifi / bundle CA | 2026.6.17 | MPL-2.0 | Conservare avvisi e adempiere agli obblighi sui file coperti. |
| PyInstaller, strumento di build | 6.21.0 | GPL con eccezione di distribuzione; alcuni file Apache-2.0 | L'eccezione consente bundle con altre licenze, rispettando quelle delle dipendenze. |

Le licenze sono state lette nei file `*.dist-info`, oltre ai metadati. Per certifi la MPL riguarda i file coperti e non impone automaticamente MPL all'intera applicazione. Il bundle `cacert.pem` è presente nella distribuzione locale. [FAQ Mozilla MPL](https://www.mozilla.org/en-US/MPL/2.0/FAQ/).

PyInstaller non impone la GPL al programma generato tramite il semplice uso dello strumento, grazie alla sua eccezione. Nessuna modifica a PyInstaller è stata rilevata nel repository. [Licenza PyInstaller 6.21.0](https://pyinstaller.org/en/v6.21.0/license.html).

## Componenti nativi e strumenti di packaging

La build locale include Python 3.14.5, OpenSSL 3.0.20, libffi, runtime Microsoft VC++, estensioni della libreria standard e plugin Qt. Python usa PSF e licenze dei componenti incorporati; OpenSSL 3 usa Apache-2.0. Occorre raccogliere i testi e gli avvisi relativi alla versione effettivamente inclusa. [Licenze Python e componenti](https://docs.python.org/3.14/license.html).

Sono presenti Qt Core, GUI, Widgets, Network, SVG e PDF, plugin immagini e `opengl32sw.dll`. Qt Core e Qt PDF dichiarano versione 6.11.1; gli hash di Qt Core, Qt PDF e SIP coincidono con quelli della `.venv`.

Qt PDF e il plugin `qpdf.dll` sono inclusi anche senza un import esplicito di QtPdf nel codice applicativo. Il modulo contiene PDFium e ulteriori componenti con licenze proprie. La documentazione Qt 6.11 indica opzioni LGPLv3/GPLv2/commerciale per Qt PDF: **non è stato classificato automaticamente come GPL-only**. [Licenze Qt PDF](https://doc.qt.io/qt-6.11/qtpdf-licensing.html).

L'inventario nativo non è una SBOM completa: non sono stati determinati tutti i componenti staticamente incorporati nelle DLL, né validati i diritti di redistribuzione dei runtime Microsoft. La documentazione Qt consultata per la serie 6.11 descrive attualmente 6.11.2; attribuzioni e sorgenti finali devono corrispondere alla build 6.11.1 effettivamente usata. [Componenti di terzi in Qt](https://doc.qt.io/qt-6.11/licenses-used-in-qt.html).

La licenza ufficiale Inno Setup consente anche uso commerciale e non richiede un ringraziamento nel prodotto; impone di conservare gli avvisi previsti per i suoi componenti. La versione installata e il contenuto interno degli installer pubblicati non sono stati verificati. [Licenza Inno Setup](https://jrsoftware.org/files/is/license.txt).

## Asset, titolarità e riproducibilità

- La nuova icona ha sorgente SVG disegnato nel progetto; il banner generato ha provenienza documentata in `images/branding.md`. Non è stata rilevata l'importazione di un pacchetto di icone esterno. Questo non certifica titolarità o esclusività dell'opera generata.
- Gli screenshot esistenti non hanno una provenienza separata documentata: va confermata la titolarità di eventuali contenuti di terzi visibili.
- Non sono presenti file di font negli asset esaminati. Il riferimento a font di sistema non equivale alla loro redistribuzione.
- La cronologia Git locale riporta GiancaGIS come autore; questo non prova autonomamente la titolarità di tutto il codice o l'assenza di parti copiate.
- Le dipendenze di build e alcune transitive non sono fissate completamente. Le prossime build possono cambiare versioni, componenti inclusi e relativi obblighi: conservare un inventario per ciascuna release.

## Percorsi di correzione

| Obiettivo | Percorso | Lavoro necessario |
| --- | --- | --- |
| Mantenere PyQt6 gratuito | Distribuire l'app combinata secondo GPLv3 | Dichiarazioni coerenti, testi e attribuzioni, sorgenti corrispondenti e packaging verificato. Il codice originale può mantenere MIT compatibile. |
| Mantenere MIT sul proprio codice con un binding LGPL | Valutare una migrazione a PySide6 | Porting, verifica dei moduli Qt, testi e obblighi LGPL, sostituibilità delle librerie e nuovo controllo dei bundle. |
| Mantenere PyQt6 senza il vincolo GPL del binding | Licenza commerciale Riverbank adeguata | Verificare copertura e termini; restano gli obblighi di Qt e delle altre dipendenze. L'acquisto futuro non dimostra la conformità delle distribuzioni precedenti. |

PySide6 appartiene a Qt for Python, che prevede LGPL/licenza commerciale e licenze separate per parti di terzi. La migrazione va valutata sui moduli realmente utilizzati e distribuiti, non soltanto cambiando gli import. [Licenze Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html).

In tutti i percorsi occorre preparare `THIRD_PARTY_NOTICES` e i testi originali delle licenze, includerli in eseguibili e installer, documentare i sorgenti e verificare il contenuto dei pacchetti prodotti. Applicare una correzione alla prossima release non corregge automaticamente gli installer già pubblicati: esaminare anche 1.0.3 e 1.0.4 e predisporre la relativa regolarizzazione.

L'audit lascia aperti la scelta del percorso, la verifica completa dei componenti nativi e degli asset remoti, e l'implementazione delle correzioni. Non sono stati modificati `LICENSE`, dipendenze, installer o release GitHub.
