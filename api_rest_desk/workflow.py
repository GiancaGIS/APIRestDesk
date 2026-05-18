from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any

from api_rest_desk.http_client import RestClient
from api_rest_desk.models import HttpResponseData, RestCall, Workflow


TEMPLATE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")
PATH_TOKEN_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*)(?:\[(\d+)])?")


@dataclass
class WorkflowStepResult:
    step_name: str
    call_name: str
    status: int | None
    reason: str = ""
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str = ""
    elapsed_ms: float | None = None
    extracted: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class WorkflowRunResult:
    variables: dict[str, Any]
    steps: list[WorkflowStepResult]


class WorkflowRunner:
    def __init__(self, client: RestClient | None = None) -> None:
        self.client = client or RestClient()

    def run(self, workflow: Workflow, calls: list[RestCall]) -> WorkflowRunResult:
        variables: dict[str, Any] = {}
        results: list[WorkflowStepResult] = []
        calls_by_id = {call.id: call for call in calls}

        for index, step in enumerate(workflow.steps, start=1):
            source_call = calls_by_id.get(step.call_id)
            if source_call is None:
                results.append(
                    WorkflowStepResult(
                        step_name=step.name or f"Step {index}",
                        call_name="-",
                        status=None,
                        error="Chiamata non trovata nella raccolta.",
                    )
                )
                break

            rendered_call = self._render_call(source_call, variables)
            response = self.client.send(rendered_call)
            extracted = self._extract_variables(response, step.extractors)
            variables.update(extracted)
            results.append(
                WorkflowStepResult(
                    step_name=step.name or f"Step {index}",
                    call_name=source_call.name,
                    status=response.status,
                    reason=response.reason,
                    response_headers=response.headers,
                    response_body=response.body,
                    elapsed_ms=response.elapsed_ms,
                    extracted=extracted,
                )
            )

            if response.status >= 400:
                break

        return WorkflowRunResult(variables=variables, steps=results)

    def _render_call(self, call: RestCall, variables: dict[str, Any]) -> RestCall:
        rendered = copy.deepcopy(call)
        rendered.url = self._render_text(rendered.url, variables)
        rendered.body = self._render_text(rendered.body, variables)
        rendered.auth_username = self._render_text(rendered.auth_username, variables)
        rendered.auth_password = self._render_text(rendered.auth_password, variables)
        rendered.auth_token = self._render_text(rendered.auth_token, variables)
        rendered.auth_key_name = self._render_text(rendered.auth_key_name, variables)
        rendered.auth_key_value = self._render_text(rendered.auth_key_value, variables)
        rendered.query_params = {
            self._render_text(name, variables): self._render_text(value, variables)
            for name, value in rendered.query_params.items()
        }
        rendered.headers = {
            self._render_text(name, variables): self._render_text(value, variables)
            for name, value in rendered.headers.items()
        }
        return rendered

    @staticmethod
    def _render_text(text: str, variables: dict[str, Any]) -> str:
        def replace(match: re.Match[str]) -> str:
            value = variables.get(match.group(1), "")
            if isinstance(value, str):
                return value
            return json.dumps(value, ensure_ascii=False)

        return TEMPLATE_PATTERN.sub(replace, text)

    def _extract_variables(
        self,
        response: HttpResponseData,
        extractors: dict[str, str],
    ) -> dict[str, Any]:
        if not extractors:
            return {}

        try:
            payload = json.loads(response.body)
        except json.JSONDecodeError as error:
            raise ValueError(f"La risposta di '{response.status}' non e un JSON valido.") from error

        extracted: dict[str, Any] = {}
        for variable_name, path in extractors.items():
            extracted[variable_name] = self.extract_path(payload, path)
        return extracted

    @staticmethod
    def extract_path(payload: Any, path: str) -> Any:
        if "{{" in path or "}}" in path:
            raise ValueError(
                "Percorso JSON non valido: non usare {{variabile}} nelle Estrazioni. "
                "Qui va indicato il percorso nella response, ad esempio token=token oppure token=data.access_token. "
                "Usa poi {{token}} negli step successivi."
            )

        current = payload
        for part in path.split("."):
            if not part:
                continue

            match = PATH_TOKEN_PATTERN.fullmatch(part)
            if match is None:
                raise ValueError(f"Percorso JSON non valido: {path}")

            key, index = match.groups()
            if not isinstance(current, dict) or key not in current:
                raise KeyError(f"Chiave non trovata: {key}")

            current = current[key]
            if index is not None:
                if not isinstance(current, list):
                    raise TypeError(f"'{key}' non e una lista.")
                current = current[int(index)]

        return current


def parse_extractors(text: str) -> dict[str, str]:
    extractors: dict[str, str] = {}
    normalized = text.replace(";", "\n").replace(",", "\n")
    for raw_line in normalized.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        name, separator, path = line.partition("=")
        if not separator or not name.strip() or not path.strip():
            raise ValueError("Usa il formato 'variabile=percorso.json'.")
        extractors[name.strip()] = path.strip()
    return extractors


def format_extractors(extractors: dict[str, str]) -> str:
    return "; ".join(f"{name}={path}" for name, path in extractors.items())
