# APIRestDesk

APIRestDesk is a PyQt6 desktop REST client for collecting, testing, saving, and composing REST calls. It is designed as a lightweight Postman-like tool with local persistence, request history, authentication helpers, and visual workflow composition.

Current version: **1.0.0**

## Highlights

- Local REST request collection organized in folders.
- Persistent request history.
- HTTP methods: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`.
- Async HTTP execution with `httpx`, keeping the GUI responsive.
- Request editor for URL, headers, params, auth, and body.
- Suggested common HTTP headers.
- Auth modes: no auth, Basic Auth, Bearer Token, API Key in header or query string.
- Query params editor with key/value rows.
- Body modes: `Raw`, `JSON`, `Form URL Encoded`.
- JSON formatting and validation.
- Response viewer with `Pretty`, `Raw`, `Headers`, search, copy, and save.
- Status badges and colors for HTTP results.
- Toast notifications in the top-right corner.
- Light and dark themes.
- Italian/English language setting.
- `About` menu with the application version.

## Workflow Composer

The workflow composer chains saved REST calls. Each step executes a saved request and can extract values from its JSON response for use in following steps.

Available workflow modes:

- **Linear**: table-based step editor.
- **Vertical blocks**: one card per step, arranged top-to-bottom.
- **Visual canvas**: draggable nodes with connections.

The workflow window can be maximized. The result area has a vertical splitter, so the lower output panel can be resized. After a workflow run, APIRestDesk shows:

- a workflow summary with extracted variables, status codes, timings, and response sizes;
- each step's response body and headers;
- status badges on blocks or canvas nodes.

### Extracting Values From JSON

In the `Extractors` field, use:

```text
variable_name=json.path
```

Example response:

```json
{
  "token": "ABC123",
  "features": [
    {
      "attributes": {
        "OBJECTID": 10
      }
    }
  ]
}
```

Extractors:

```text
token=token; object_id=features[0].attributes.OBJECTID
```

Following steps can use those variables with:

```text
{{token}}
{{object_id}}
```

Examples:

```text
Authorization: Bearer {{token}}
```

```text
token={{token}}
```

```text
where=OBJECTID={{object_id}}
```

Do not write `{{token}}` inside the `Extractors` field. Curly-brace variables are used only when consuming an extracted value in later steps.

## ArcGIS Server Notes

APIRestDesk works well for ArcGIS REST endpoints.

ArcGIS services usually need this parameter to return JSON:

```text
f=json
```

or:

```text
f=pjson
```

For `MapServer` or `FeatureServer` query operations, target the specific layer:

```text
.../MapServer/0/query
.../FeatureServer/0/query
```

Example `GET`:

```text
https://server/arcgis/rest/services/ServiceName/MapServer/0/query?where=1%3D1&outFields=*&returnGeometry=true&f=json
```

Recommended ArcGIS `POST` setup:

- method: `POST`
- URL: `https://server/arcgis/rest/services/ServiceName/MapServer/0/query`
- body type: `Form URL Encoded`
- body table:

```text
where            1=1
outFields        *
returnGeometry   true
f                json
```

Many ArcGIS REST endpoints do not interpret raw JSON bodies like this:

```json
{
  "where": "1=1",
  "outFields": "*",
  "f": "json"
}
```

Use `Form URL Encoded` instead. APIRestDesk sends:

```text
where=1%3D1&outFields=%2A&f=json
```

with:

```text
Content-Type: application/x-www-form-urlencoded
```

## Local Data Files

Data is stored as JSON files in the project root:

- `rest_client_collection.json`: saved request collection.
- `rest_client_folders.json`: collection folders.
- `rest_client_history.json`: request history.
- `rest_client_workflows.json`: saved workflows.
- `rest_client_settings.json`: language, theme, and settings.

The history limit is configured in `api_rest_desk/config.py`:

```python
HISTORY_LIMIT = 250
```

## Installation

Requirements:

- Python 3.11 or newer.
- Windows, Linux, or macOS with PyQt6 support.

Install runtime dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Install the project in editable mode:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

## Running

Direct launcher:

```powershell
.\.venv\Scripts\python.exe launch_api_rest_desk.py
```

Python module:

```powershell
.\.venv\Scripts\python.exe -m api_rest_desk
```

Installed entry point:

```powershell
.\.venv\Scripts\api-rest-desk.exe
```

## Packaging

The project includes a `pyproject.toml` with:

- package name: `api-rest-desk`
- version: `1.0.0`
- dependencies: `PyQt6`, `httpx`
- entry point: `api-rest-desk = api_rest_desk.__main__:main`

Build a Python distribution:

```powershell
.\.venv\Scripts\python.exe -m pip install build
.\.venv\Scripts\python.exe -m build
```

## Project Structure

```text
api_rest_desk/
  __main__.py              Package entry point
  config.py                App constants, version, data file paths
  http_client.py           httpx-based HTTP wrapper
  i18n.py                  Italian/English translations
  main_window.py           Main PyQt6 window
  models.py                Dataclasses for requests, history, workflows
  settings.py              Settings persistence
  settings_dialog.py       Settings dialog
  storage.py               Local JSON read/write helpers
  theme.py                 Light/dark theme and status badges
  toast.py                 Animated toast notifications
  widgets.py               Reusable widgets: headers, auth, key/value
  workers.py               Qt workers for HTTP and workflow execution
  workflow.py              Workflow engine, templating, JSON path extraction
  workflow_canvas.py       Visual workflow canvas
  workflow_dialog.py       Workflow composer
```

Root files:

```text
launch_api_rest_desk.py    Desktop launcher
pyproject.toml             Python packaging metadata
requirements.txt           Runtime dependencies
README.md                  Documentation
```

## Technical Notes

- HTTP requests run in Qt worker threads.
- History stores request headers, params, body, status, response headers, and response body.
- Auth credentials are stored in the local request collection.
- History entries do not restore auth credentials, to avoid duplicating tokens/passwords.
- Workflows reference saved collection requests. If a request changes, workflow steps use the updated request.
- The `{{variable}}` template is applied to URLs, headers, body, params, and auth fields.
- Extractors read JSON responses with paths such as `token`, `data.access_token`, `features[0].attributes.OBJECTID`.

---

# APIRestDesk - Italiano

APIRestDesk e un client desktop REST scritto in Python con PyQt6. Serve per raccogliere chiamate REST, provarle, salvarle, consultare lo storico e comporre workflow di chiamate concatenate.

Versione corrente: **1.0.0**

## Funzioni principali

- Raccolta locale di chiamate REST organizzata in cartelle.
- Storico persistente delle richieste inviate.
- Metodi HTTP: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`.
- Invio asincrono tramite `httpx`, senza bloccare l'interfaccia.
- Editor per URL, headers, params, auth e body.
- Suggerimenti per headers comuni.
- Modalita Auth: nessuna auth, Basic Auth, Bearer Token, API Key in header o query string.
- Query params con tabella chiave/valore.
- Body `Raw`, `JSON` e `Form URL Encoded`.
- Formattazione e validazione JSON.
- Viewer response con `Pretty`, `Raw`, `Headers`, ricerca, copia e salvataggio.
- Badge colorati per gli esiti HTTP.
- Toast notification in alto a destra.
- Tema chiaro/scuro.
- Lingua italiano/inglese dalle impostazioni.
- Menu `Informazioni` con versione applicativa.

## Workflow

Il composer workflow concatena chiamate salvate nella raccolta. Ogni step esegue una richiesta e puo estrarre valori dalla response JSON per passarli agli step successivi.

Modalita disponibili:

- **Lineare**: editor a tabella.
- **Blocchi verticali**: card verticali, una per ogni step.
- **Canvas visuale**: nodi trascinabili con connessioni.

La finestra workflow e massimizzabile. L'area risultati ha uno splitter verticale per allargare il pannello sotto. Dopo l'esecuzione vengono mostrati:

- riepilogo workflow con variabili estratte, status, tempi e dimensioni;
- body e headers di ogni singolo step;
- badge di stato su blocchi o nodi canvas.

### Estrarre valori da JSON

Nel campo `Estrazioni` si usa:

```text
nome_variabile=percorso.nel.json
```

Esempio:

```json
{
  "token": "ABC123",
  "features": [
    {
      "attributes": {
        "OBJECTID": 10
      }
    }
  ]
}
```

Estrazioni:

```text
token=token; object_id=features[0].attributes.OBJECTID
```

Negli step successivi puoi usare:

```text
{{token}}
{{object_id}}
```

Esempi:

```text
Authorization: Bearer {{token}}
```

```text
token={{token}}
```

```text
where=OBJECTID={{object_id}}
```

Nel campo `Estrazioni` non va scritto `{{token}}`: le doppie graffe servono solo quando usi una variabile in uno step successivo.

## Note ArcGIS Server

Per ottenere JSON dagli endpoint ArcGIS REST serve di solito:

```text
f=json
```

oppure:

```text
f=pjson
```

Per `MapServer` o `FeatureServer` devi interrogare il layer specifico:

```text
.../MapServer/0/query
.../FeatureServer/0/query
```

Esempio `GET`:

```text
https://server/arcgis/rest/services/NomeServizio/MapServer/0/query?where=1%3D1&outFields=*&returnGeometry=true&f=json
```

Esempio `POST` consigliato:

- metodo: `POST`
- URL: `https://server/arcgis/rest/services/NomeServizio/MapServer/0/query`
- body type: `Form URL Encoded`
- body table:

```text
where            1=1
outFields        *
returnGeometry   true
f                json
```

Molti endpoint ArcGIS REST non interpretano body JSON raw. Usa `Form URL Encoded`, cosi l'app invia:

```text
where=1%3D1&outFields=%2A&f=json
```

con:

```text
Content-Type: application/x-www-form-urlencoded
```

## File locali

I dati vengono salvati in file JSON nella root del progetto:

- `rest_client_collection.json`: raccolta chiamate.
- `rest_client_folders.json`: cartelle.
- `rest_client_history.json`: storico.
- `rest_client_workflows.json`: workflow.
- `rest_client_settings.json`: lingua, tema e impostazioni.

## Installazione e avvio

Installazione dipendenze:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Installazione editable:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

Avvio con launcher:

```powershell
.\.venv\Scripts\python.exe launch_api_rest_desk.py
```

Avvio come modulo:

```powershell
.\.venv\Scripts\python.exe -m api_rest_desk
```

Avvio tramite entry point:

```powershell
.\.venv\Scripts\api-rest-desk.exe
```

## Packaging

Il `pyproject.toml` dichiara:

- package name: `api-rest-desk`
- versione: `1.0.0`
- dipendenze: `PyQt6`, `httpx`
- entry point: `api-rest-desk = api_rest_desk.__main__:main`

Build:

```powershell
.\.venv\Scripts\python.exe -m pip install build
.\.venv\Scripts\python.exe -m build
```
