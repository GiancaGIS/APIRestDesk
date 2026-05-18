from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RestCall:
    name: str
    method: str = "GET"
    url: str = ""
    collection: str = "Generale"
    headers: dict[str, str] = field(default_factory=dict)
    query_params: dict[str, str] = field(default_factory=dict)
    body: str = ""
    body_type: str = "raw"
    auth_type: str = "none"
    auth_username: str = ""
    auth_password: str = ""
    auth_token: str = ""
    auth_key_name: str = ""
    auth_key_value: str = ""
    auth_key_location: str = "header"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RestCall":
        return cls(
            id=str(data.get("id") or uuid.uuid4().hex),
            name=str(data.get("name") or "Nuova chiamata"),
            method=str(data.get("method") or "GET").upper(),
            url=str(data.get("url") or ""),
            collection=str(data.get("collection") or "Generale"),
            headers=dict(data.get("headers") or {}),
            query_params=dict(data.get("query_params") or {}),
            body=str(data.get("body") or ""),
            body_type=str(data.get("body_type") or "raw"),
            auth_type=str(data.get("auth_type") or "none"),
            auth_username=str(data.get("auth_username") or ""),
            auth_password=str(data.get("auth_password") or ""),
            auth_token=str(data.get("auth_token") or ""),
            auth_key_name=str(data.get("auth_key_name") or ""),
            auth_key_value=str(data.get("auth_key_value") or ""),
            auth_key_location=str(data.get("auth_key_location") or "header"),
        )


@dataclass
class HttpResponseData:
    status: int
    reason: str
    headers: dict[str, str]
    body: str
    elapsed_ms: float
    size_bytes: int


@dataclass
class CallHistory:
    timestamp: str
    name: str
    method: str
    url: str
    request_headers: dict[str, str] = field(default_factory=dict)
    request_query_params: dict[str, str] = field(default_factory=dict)
    request_body: str = ""
    request_body_type: str = "raw"
    status: int | None = None
    reason: str = ""
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str = ""
    elapsed_ms: float | None = None
    size_bytes: int | None = None
    error: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CallHistory":
        status = data.get("status")
        return cls(
            id=str(data.get("id") or uuid.uuid4().hex),
            timestamp=str(data.get("timestamp") or ""),
            name=str(data.get("name") or "Chiamata"),
            method=str(data.get("method") or "GET").upper(),
            url=str(data.get("url") or ""),
            request_headers=dict(data.get("request_headers") or {}),
            request_query_params=dict(data.get("request_query_params") or {}),
            request_body=str(data.get("request_body") or ""),
            request_body_type=str(data.get("request_body_type") or "raw"),
            status=int(status) if isinstance(status, int) else None,
            reason=str(data.get("reason") or ""),
            response_headers=dict(data.get("response_headers") or {}),
            response_body=str(data.get("response_body") or ""),
            elapsed_ms=data.get("elapsed_ms") if isinstance(data.get("elapsed_ms"), (int, float)) else None,
            size_bytes=data.get("size_bytes") if isinstance(data.get("size_bytes"), int) else None,
            error=str(data.get("error") or ""),
        )


@dataclass
class WorkflowStep:
    call_id: str
    name: str = ""
    extractors: dict[str, str] = field(default_factory=dict)
    position_x: float | None = None
    position_y: float | None = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowStep":
        position_x = data.get("position_x")
        position_y = data.get("position_y")
        return cls(
            id=str(data.get("id") or uuid.uuid4().hex),
            call_id=str(data.get("call_id") or ""),
            name=str(data.get("name") or ""),
            extractors=dict(data.get("extractors") or {}),
            position_x=float(position_x) if isinstance(position_x, (int, float)) else None,
            position_y=float(position_y) if isinstance(position_y, (int, float)) else None,
        )


@dataclass
class Workflow:
    name: str
    mode: str = "linear"
    steps: list[WorkflowStep] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workflow":
        raw_steps = data.get("steps") or []
        return cls(
            id=str(data.get("id") or uuid.uuid4().hex),
            name=str(data.get("name") or "Nuovo workflow"),
            mode=str(data.get("mode") or "linear"),
            steps=[WorkflowStep.from_dict(item) for item in raw_steps if isinstance(item, dict)],
        )
