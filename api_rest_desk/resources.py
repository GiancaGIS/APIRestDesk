from __future__ import annotations

from importlib.resources import files


def app_icon_path() -> str:
    return str(files("api_rest_desk").joinpath("assets", "app_icon.png"))
