from __future__ import annotations

import json
import time

import httpx

from api_rest_desk.models import HttpResponseData, RestCall


class RestClient:
    def __init__(self, timeout: float = 30.0, follow_redirects: bool = True) -> None:
        self.timeout = timeout
        self.follow_redirects = follow_redirects

    def send(self, call: RestCall) -> HttpResponseData:
        headers = dict(call.headers)
        headers.setdefault("User-Agent", "PyQt RestClient/0.1")
        params: dict[str, str] = dict(call.query_params)
        auth: tuple[str, str] | None = None

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
        if call.method not in {"GET", "DELETE"} and call.body.strip():
            content = call.body.encode("utf-8")
            headers.setdefault("Content-Type", self._guess_content_type(call.body))

        started = time.perf_counter()
        with httpx.Client(timeout=self.timeout, follow_redirects=self.follow_redirects) as client:
            response = client.request(
                method=call.method,
                url=call.url,
                headers=headers,
                data=params,
                #params=params or None,
                #content=content,
                auth=auth,
            )
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

        return HttpResponseData(
            status=response.status_code,
            reason=response.reason_phrase,
            headers=dict(response.headers),
            body=response.text,
            elapsed_ms=elapsed_ms,
            size_bytes=len(response.content),
        )

    @staticmethod
    def _guess_content_type(body: str) -> str:
        try:
            json.loads(body)
        except json.JSONDecodeError:
            return "text/plain; charset=utf-8"
        return "application/json; charset=utf-8"
