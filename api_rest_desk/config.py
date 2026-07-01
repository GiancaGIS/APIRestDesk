from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
APP_NAME = "APIRestDesk 🚀"
AUTHOR = "GiancaGIS"
APP_VERSION = "1.0.2"
COLLECTION_FILE = ROOT_DIR / "rest_client_collection.json"
FOLDERS_FILE = ROOT_DIR / "rest_client_folders.json"
HISTORY_FILE = ROOT_DIR / "rest_client_history.json"
WORKFLOWS_FILE = ROOT_DIR / "rest_client_workflows.json"
SETTINGS_FILE = ROOT_DIR / "rest_client_settings.json"
COOKIES_FILE = ROOT_DIR / "rest_client_cookies.json"
HISTORY_LIMIT = 250
DEFAULT_COLLECTION = "Generale"
HTTP_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")

COMMON_HEADERS = (
    "Accept",
    "Accept-Charset",
    "Accept-Encoding",
    "Accept-Language",
    "Authorization",
    "Cache-Control",
    "Content-Type",
    "Cookie",
    "If-Match",
    "If-None-Match",
    "Origin",
    "Referer",
    "User-Agent",
    "X-API-Key",
    "X-Auth-Token",
    "X-Request-ID",
    "X-Correlation-ID",
)
