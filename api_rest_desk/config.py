from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
APP_NAME = "APIRestDesk 🚀"
APP_FOLDER_NAME = "APIRestDesk"
APP_BUNDLE_ID = "com.giancagis.apirestdesk"
AUTHOR = "GiancaGIS"
APP_VERSION = "1.0.3"


def _default_data_dir() -> Path:
    if not getattr(sys, "frozen", False):
        return ROOT_DIR

    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_FOLDER_NAME
        return Path.home() / "AppData" / "Roaming" / APP_FOLDER_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_FOLDER_NAME

    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base) / APP_FOLDER_NAME
    return Path.home() / ".local" / "share" / APP_FOLDER_NAME


DATA_DIR = Path(os.environ.get("API_REST_DESK_DATA_DIR", _default_data_dir())).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)
COLLECTION_FILE = DATA_DIR / "rest_client_collection.json"
FOLDERS_FILE = DATA_DIR / "rest_client_folders.json"
HISTORY_FILE = DATA_DIR / "rest_client_history.json"
WORKFLOWS_FILE = DATA_DIR / "rest_client_workflows.json"
SETTINGS_FILE = DATA_DIR / "rest_client_settings.json"
COOKIES_FILE = DATA_DIR / "rest_client_cookies.json"
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
