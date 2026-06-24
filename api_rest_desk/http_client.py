from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import parse_qsl

import httpx

from api_rest_desk.config import APP_NAME
from api_rest_desk.exceptions import NoResponseError
from api_rest_desk.models import HttpResponseData, RestCall


class RestClient:
    """Synchronous HTTP client that wraps *httpx* to execute :class:`RestCall` requests.

    Handles authentication (Basic, Bearer, API Key), body serialization
    (raw, JSON, form-urlencoded), retry logic, and session cookies.
    """

    def __init__(
        self,
        timeout: float = 30.0,
        follow_redirects: bool = True,
        session_cookies: dict[str, str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.follow_redirects = follow_redirects
        self.session_cookies = session_cookies or {}
        self._content_type: dict[str, str] = {"urlencoded": "application/x-www-form-urlencoded",
                                              "json": "application/json; charset=utf-8"}
        self._label_content_type = "Content-Type"

    def send(self, call: RestCall) -> HttpResponseData:
        """Execute an HTTP request described by *call* and return the response.

        Resolves authentication headers/params, serializes the body according
        to ``call.body_type`` (``"raw"``, ``"json"``, or ``"form"``), and
        retries on configurable status codes.

        When ``body_type`` is ``"form"`` and the body is empty, any
        ``query_params`` are moved into the POST body as form data instead
        of being appended to the URL query string.

        Args:
            call: Fully populated request descriptor.

        Returns:
            An :class:`HttpResponseData` with status, headers, body, timing
            and cookies gathered from the server response.

        Raises:
            NoResponseError: If no response is received after all attempts.
            httpx.HTTPError: On transport-level failures (DNS, timeout, etc.).
        """
        headers = dict(call.headers)
        headers.setdefault("User-Agent", f"PyQt {APP_NAME.split(' ')[0]}/0.1")
        params: dict[str, str] = dict(call.query_params)
        auth: tuple[str, str] | None = None
        retry_statuses = self._parse_retry_statuses(call.retry_statuses)
        attempts = max(1, int(call.retry_count) + 1)
        timeout = max(0.1, float(call.timeout or self.timeout))

        if call.auth_type == "basic" and (call.auth_username or call.auth_password):
            auth = (call.auth_username, call.auth_password)
        elif call.auth_type == "bearer" and call.auth_token:
            headers["Authorization"] = f"Bearer {call.auth_token}"
        elif call.auth_type == "api_key" and call.auth_key_name and call.auth_key_value:
            if call.auth_key_location == "query":
                params[call.auth_key_name] = call.auth_key_value
            else:
                headers[call.auth_key_name] = call.auth_key_value

        content: bytes | None = None
        json_data: Any = None
        form_data: dict[str, str] | None = None

        if call.method not in {"GET", "DELETE"} and call.body.strip():
            body_type = getattr(call, "body_type", "raw")
            if body_type == "json":
                try:
                    json_data = json.loads(call.body)
                except json.JSONDecodeError:
                    content = call.body.encode("utf-8")
                    headers.setdefault(self._label_content_type, self._content_type['json'])
            elif body_type == "form":
                form_data = dict(parse_qsl(call.body, keep_blank_values=True))
                if params:
                    for k, v in params.items():
                        form_data.setdefault(k, v)
                    params = {}
                headers.setdefault(self._label_content_type, self._content_type['urlencoded'])
            else:
                content = call.body.encode("utf-8")
                headers.setdefault(self._label_content_type, self._guess_content_type(call.body))
        elif call.method not in {"GET", "DELETE"} and getattr(call, "body_type", "raw") == "form" and params:
            # Body vuoto ma query_params presenti con body_type "form":
            # invia i params come form data nel body, non nella query string.
            form_data = dict(params)
            params = {}
            headers.setdefault(self._label_content_type, self._content_type['urlencoded'])

        started = time.perf_counter()
        cookies = self.session_cookies if call.use_session_cookies else None
        with httpx.Client(timeout=timeout, follow_redirects=call.follow_redirects, cookies=cookies, verify=call.verify) as client:
            response: httpx.Response | None = None
            for attempt in range(attempts):
                response = client.request(
                    method=call.method,
                    url=call.url,
                    headers=headers,
                    params=params or None,
                    content=content,
                    data=form_data,
                    json=json_data,
                    auth=auth,
                )
                if attempt == attempts - 1 or response.status_code not in retry_statuses:
                    break
                time.sleep(min(0.25 * (attempt + 1), 1.0))
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        if response is None:
            raise NoResponseError("no_http_response")

        return HttpResponseData(
            status=response.status_code,
            reason=response.reason_phrase,
            headers=dict(response.headers),
            body=response.text,
            elapsed_ms=elapsed_ms,
            size_bytes=len(response.content),
            cookies=dict(client.cookies),
        )

    @staticmethod
    def _guess_content_type(body: str) -> str:
        """Guess the Content-Type for a raw body string.

        Returns ``application/json`` when the body is valid JSON,
        otherwise ``text/plain``.
        """
        try:
            json.loads(body)
        except json.JSONDecodeError:
            return "text/plain; charset=utf-8"
        return "application/json; charset=utf-8"

    @staticmethod
    def _parse_retry_statuses(value: str) -> set[int]:
        """Parse a comma- or semicolon-separated string of HTTP status codes
        into a set of integers.

        Only values between 100 and 599 are included; invalid tokens are
        silently ignored.
        """
        statuses: set[int] = set()
        for item in value.replace(";", ",").split(","):
            item = item.strip()
            if not item:
                continue
            try:
                status = int(item)
            except ValueError:
                continue
            if 100 <= status <= 599:
                statuses.add(status)
        return statuses
