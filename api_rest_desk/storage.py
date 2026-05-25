from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from api_rest_desk.config import (
    COLLECTION_FILE,
    COOKIES_FILE,
    DEFAULT_COLLECTION,
    FOLDERS_FILE,
    HISTORY_FILE,
    HISTORY_LIMIT,
    WORKFLOWS_FILE,
)
from api_rest_desk.models import CallHistory, RestCall, Workflow


class StorageError(RuntimeError):
    """Raised when a storage read/write operation fails."""
    pass


def default_collection() -> list[RestCall]:
    """Return a starter collection with sample GET and POST requests."""
    return [
        RestCall(
            name="Esempio GET",
            method="GET",
            url="https://httpbin.org/get",
            collection=DEFAULT_COLLECTION,
            headers={"Accept": "application/json"},
        ),
        RestCall(
            name="Esempio POST JSON",
            method="POST",
            url="https://httpbin.org/post",
            collection=DEFAULT_COLLECTION,
            headers={"Accept": "application/json"},
            body=json.dumps({"message": "ciao"}, indent=2),
        ),
    ]


def load_collection(path: Path = COLLECTION_FILE) -> list[RestCall]:
    """Load the saved REST call collection from disk.

    Returns the default sample collection when the file does not exist.

    Raises:
        StorageError: If the file cannot be read or parsed.
    """
    if not path.exists():
        return default_collection()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(str(error)) from error

    return [RestCall.from_dict(item) for item in data if isinstance(item, dict)]


def save_collection(calls: list[RestCall], path: Path = COLLECTION_FILE) -> None:
    """Persist the REST call collection to disk as JSON."""
    payload = [asdict(call) for call in calls]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_folders(path: Path = FOLDERS_FILE) -> list[str]:
    """Load the ordered list of collection folder names.

    Raises:
        StorageError: If the file cannot be read or parsed.
    """
    if not path.exists():
        return [DEFAULT_COLLECTION]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(str(error)) from error

    folders = [str(item).strip() for item in data if str(item).strip()]
    return folders or [DEFAULT_COLLECTION]


def save_folders(folders: list[str], path: Path = FOLDERS_FILE) -> None:
    """Persist the folder list to disk, ensuring the default collection
    folder is always first and duplicates are removed.
    """
    normalized = []
    for folder in [DEFAULT_COLLECTION, *folders]:
        if folder and folder not in normalized:
            normalized.append(folder)
    path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")


def load_history(path: Path = HISTORY_FILE) -> list[CallHistory]:
    """Load the request/response history from disk.

    Raises:
        StorageError: If the file cannot be read or parsed.
    """
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(str(error)) from error

    return [CallHistory.from_dict(item) for item in data if isinstance(item, dict)]


def save_history(history: list[CallHistory], path: Path = HISTORY_FILE) -> None:
    """Persist the history to disk, truncated to ``HISTORY_LIMIT`` entries."""
    payload = [asdict(item) for item in history[:HISTORY_LIMIT]]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_workflows(path: Path = WORKFLOWS_FILE) -> list[Workflow]:
    """Load saved workflows from disk.

    Raises:
        StorageError: If the file cannot be read or parsed.
    """
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(str(error)) from error

    return [Workflow.from_dict(item) for item in data if isinstance(item, dict)]


def save_workflows(workflows: list[Workflow], path: Path = WORKFLOWS_FILE) -> None:
    """Persist all workflows to disk as JSON."""
    payload = [asdict(item) for item in workflows]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_session_cookies(path: Path = COOKIES_FILE) -> dict[str, str]:
    """Load persisted session cookies from disk.

    Raises:
        StorageError: If the file cannot be read or parsed.
    """
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(str(error)) from error

    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}


def save_session_cookies(cookies: dict[str, str], path: Path = COOKIES_FILE) -> None:
    """Persist the current session cookies to disk."""
    path.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
