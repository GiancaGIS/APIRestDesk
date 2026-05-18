from __future__ import annotations

import json
from typing import Any

from api_rest_desk.config import SETTINGS_FILE


DEFAULT_SETTINGS: dict[str, Any] = {
    "language": "it",
    "theme": "light",
    "layout": "side_by_side",
}


def load_settings() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return dict(DEFAULT_SETTINGS)

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_SETTINGS)

    if not isinstance(data, dict):
        return dict(DEFAULT_SETTINGS)

    settings = dict(DEFAULT_SETTINGS)
    settings.update(data)
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    payload = dict(DEFAULT_SETTINGS)
    payload.update(settings)
    SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def update_setting(key: str, value: Any) -> None:
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
