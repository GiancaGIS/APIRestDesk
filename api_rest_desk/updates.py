from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from api_rest_desk.config import APP_VERSION, GITHUB_REPOSITORY


class UpdateCheckError(Exception):
    """An update failure identified by a translation key."""


def version_tuple(version: str) -> tuple[int, ...]:
    """Compare numeric release tags, accepting a v prefix and build metadata."""
    match = re.fullmatch(r"[vV]?(\d+(?:\.\d+){1,3})(?:\+[0-9A-Za-z.-]+)?", version.strip())
    if match is None:
        raise UpdateCheckError("update_invalid_version")
    parts = tuple(int(part) for part in match.group(1).split("."))
    return parts + (0,) * (4 - len(parts))


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    url: str

    def is_newer_than(self, installed: str = APP_VERSION) -> bool:
        return version_tuple(self.version) > version_tuple(installed)


def check_latest_release() -> ReleaseInfo | None:
    """Fetch the latest public stable release, without credentials or app cookies."""
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(
                f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest",
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2026-03-10",
                    "User-Agent": f"APIRestDesk/{APP_VERSION}",
                },
            )
        if response.status_code == 404:
            return None
        if response.status_code in (403, 429):
            raise UpdateCheckError("update_rate_limited")
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise UpdateCheckError("update_unavailable") from error

    try:
        payload = response.json()
    except ValueError as error:
        raise UpdateCheckError("update_invalid_response") from error
    if not isinstance(payload, dict):
        raise UpdateCheckError("update_invalid_response")
    if payload.get("draft") or payload.get("prerelease"):
        return None
    tag = payload.get("tag_name")
    url = payload.get("html_url")
    if not isinstance(tag, str) or not isinstance(url, str):
        raise UpdateCheckError("update_invalid_response")
    version_tuple(tag)
    try:
        parsed = urlsplit(url)
        valid_url = (
            parsed.scheme == "https"
            and parsed.netloc == "github.com"
            and parsed.path.startswith(f"/{GITHUB_REPOSITORY}/releases/tag/")
        )
    except ValueError:
        valid_url = False
    if not valid_url:
        raise UpdateCheckError("update_invalid_response")
    return ReleaseInfo(tag.strip(), url)
