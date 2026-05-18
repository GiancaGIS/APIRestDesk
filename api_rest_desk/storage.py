from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from api_rest_desk.config import (
    COLLECTION_FILE,
    DEFAULT_COLLECTION,
    FOLDERS_FILE,
    HISTORY_FILE,
    HISTORY_LIMIT,
    WORKFLOWS_FILE,
)
from api_rest_desk.models import CallHistory, RestCall, Workflow


class StorageError(RuntimeError):
    pass


def default_collection() -> list[RestCall]:
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
    if not path.exists():
        return default_collection()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(str(error)) from error

    return [RestCall.from_dict(item) for item in data if isinstance(item, dict)]


def save_collection(calls: list[RestCall], path: Path = COLLECTION_FILE) -> None:
    payload = [asdict(call) for call in calls]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_folders(path: Path = FOLDERS_FILE) -> list[str]:
    if not path.exists():
        return [DEFAULT_COLLECTION]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(str(error)) from error

    folders = [str(item).strip() for item in data if str(item).strip()]
    return folders or [DEFAULT_COLLECTION]


def save_folders(folders: list[str], path: Path = FOLDERS_FILE) -> None:
    normalized = []
    for folder in [DEFAULT_COLLECTION, *folders]:
        if folder and folder not in normalized:
            normalized.append(folder)
    path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")


def load_history(path: Path = HISTORY_FILE) -> list[CallHistory]:
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(str(error)) from error

    return [CallHistory.from_dict(item) for item in data if isinstance(item, dict)]


def save_history(history: list[CallHistory], path: Path = HISTORY_FILE) -> None:
    payload = [asdict(item) for item in history[:HISTORY_LIMIT]]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_workflows(path: Path = WORKFLOWS_FILE) -> list[Workflow]:
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StorageError(str(error)) from error

    return [Workflow.from_dict(item) for item in data if isinstance(item, dict)]


def save_workflows(workflows: list[Workflow], path: Path = WORKFLOWS_FILE) -> None:
    payload = [asdict(item) for item in workflows]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
