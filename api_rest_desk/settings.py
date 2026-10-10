from __future__ import annotations

import json
from copy import deepcopy
from typing import Any

from api_rest_desk.config import SETTINGS_FILE


DEFAULT_SETTINGS: dict[str, Any] = {
    "language": "it",
    "theme": "light",
    "layout": "side_by_side",
    "environment": {},
    "environments": {"development": {}, "test": {}, "production": {}},
    "active_environment": "development",
    "check_updates_automatically": True,
}


def normalize_settings(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate legacy variables and keep the active environment consistent."""
    settings = deepcopy(DEFAULT_SETTINGS)
    settings.update(deepcopy(data))
    raw_environments = data.get("environments")
    environments = {
        str(name): {str(key): value for key, value in variables.items()}
        for name, variables in (raw_environments.items() if isinstance(raw_environments, dict) else [])
        if str(name).strip() and isinstance(variables, dict)
    }
    if not environments:
        environments = deepcopy(DEFAULT_SETTINGS["environments"])
        legacy = data.get("environment")
        if isinstance(legacy, dict):
            environments["development"] = {str(key): value for key, value in legacy.items()}
    active = settings.get("active_environment")
    if not isinstance(active, str) or active not in environments:
        active = next(iter(environments))
    settings["environments"] = environments
    settings["active_environment"] = active
    # Retain the legacy field for compatibility with older workspace exports.
    settings["environment"] = deepcopy(environments[active])
    return settings


def active_environment_variables(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = normalize_settings(settings) if settings is not None else load_settings()
    return deepcopy(settings["environments"][settings["active_environment"]])


def load_settings() -> dict[str, Any]:
    """Load application settings from disk, merged with defaults.

    Returns ``DEFAULT_SETTINGS`` when the file is missing or unreadable.
    """
    if not SETTINGS_FILE.exists():
        return normalize_settings({})

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return normalize_settings({})

    if not isinstance(data, dict):
        return normalize_settings({})

    return normalize_settings(data)


def save_settings(settings: dict[str, Any]) -> None:
    """Persist application settings to disk, merged with defaults."""
    payload = normalize_settings(settings)
    SETTINGS_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def update_setting(key: str, value: Any) -> None:
    """Update a single setting key and persist immediately."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
