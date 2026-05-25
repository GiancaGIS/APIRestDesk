from __future__ import annotations

import copy
import difflib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from api_rest_desk.exceptions import ExtractionError, ExtractorParseError
from api_rest_desk.http_client import RestClient
from api_rest_desk.models import HttpResponseData, RestCall, Workflow
from api_rest_desk.settings import load_settings


TEMPLATE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")
PATH_TOKEN_PATTERN = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*)(?:\[(\d+)])?")
CAMEL_BOUNDARY_PATTERN = re.compile(r"([a-z0-9])([A-Z])")
NAME_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")
AUTO_PARAM_SCORE_THRESHOLD = 0.78


@dataclass(frozen=True)
class AutoParamCandidate:
    """Scalar JSON response value that can feed following request params."""

    name: str
    path: str
    value: Any


@dataclass
class WorkflowStepResult:
    """Result of a single workflow step execution."""

    step_name: str
    call_name: str
    status: int | None
    reason: str = ""
    response_headers: dict[str, str] = field(default_factory=dict)
    response_body: str = ""
    elapsed_ms: float | None = None
    extracted: dict[str, Any] = field(default_factory=dict)
    auto_params: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass
class WorkflowRunResult:
    """Aggregated result of a complete workflow run."""

    variables: dict[str, Any]
    steps: list[WorkflowStepResult]


class WorkflowRunner:
    """Executes a :class:`Workflow` by running each step sequentially,
    rendering ``{{variable}}`` templates and extracting variables
    from JSON responses between steps.
    """

    def __init__(self, client: RestClient | None = None) -> None:
        self.client = client or RestClient()

    def run(self, workflow: Workflow, calls: list[RestCall]) -> WorkflowRunResult:
        """Execute all steps of *workflow* in order.

        For each step the runner resolves ``{{variable}}`` placeholders
        in the request fields, sends the HTTP call, and extracts
        variables from the response for subsequent steps.  Execution
        stops early when a step returns HTTP 4xx/5xx or extraction fails.

        Args:
            workflow: The workflow definition with ordered steps.
            calls: All available REST calls (looked up by ``call_id``).

        Returns:
            A :class:`WorkflowRunResult` with per-step outcomes and the
            accumulated variable dictionary.
        """
        variables: dict[str, Any] = self._environment_variables()
        auto_candidates: list[AutoParamCandidate] = []
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

            rendered_call, auto_params = self._prepare_call(
                source_call,
                variables,
                auto_candidates,
                workflow.auto_map_params,
            )
            response = self.client.send(rendered_call)
            try:
                extracted = self._extract_variables(response, step.extractors)
            except (KeyError, TypeError, ValueError) as error:
                results.append(
                    WorkflowStepResult(
                        step_name=step.name or f"Step {index}",
                        call_name=source_call.name,
                        status=response.status,
                        reason=response.reason,
                        response_headers=response.headers,
                        response_body=response.body,
                        elapsed_ms=response.elapsed_ms,
                        auto_params=auto_params,
                        error=self._clean_error_message(error),
                    )
                )
                break

            variables.update(extracted)
            if workflow.auto_map_params:
                new_candidates = self._response_auto_candidates(response)
                auto_candidates.extend(new_candidates)
                self._merge_auto_variables(variables, new_candidates)
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
                    auto_params=auto_params,
                )
            )

            if response.status >= 400:
                break

        return WorkflowRunResult(variables=variables, steps=results)

    @staticmethod
    def _clean_error_message(error: Exception) -> str:
        message = str(error)
        if isinstance(error, KeyError):
            message = message.strip("'")
        return message

    @staticmethod
    def _environment_variables() -> dict[str, Any]:
        """Load user-defined environment variables from application settings."""
        environment = load_settings().get("environment")
        if not isinstance(environment, dict):
            return {}
        return {str(key): value for key, value in environment.items()}

    def _prepare_call(
        self,
        call: RestCall,
        variables: dict[str, Any],
        auto_candidates: list[AutoParamCandidate],
        auto_map_params: bool,
    ) -> tuple[RestCall, dict[str, Any]]:
        rendered = self._render_call(
            call,
            variables,
            auto_candidates if auto_map_params else [],
        )
        if not auto_map_params:
            return rendered, {}
        auto_params = self._auto_fill_query_params(rendered.query_params, auto_candidates)
        return rendered, auto_params

    def _render_call(
        self,
        call: RestCall,
        variables: dict[str, Any],
        auto_candidates: list[AutoParamCandidate] | None = None,
    ) -> RestCall:
        """Return a deep copy of *call* with all ``{{variable}}``
        placeholders replaced by their current values.
        """
        candidates = auto_candidates or []
        rendered = copy.deepcopy(call)
        rendered.url = self._render_text(rendered.url, variables, candidates)
        rendered.body = self._render_text(rendered.body, variables, candidates)
        rendered.auth_username = self._render_text(rendered.auth_username, variables, candidates)
        rendered.auth_password = self._render_text(rendered.auth_password, variables, candidates)
        rendered.auth_token = self._render_text(rendered.auth_token, variables, candidates)
        rendered.auth_key_name = self._render_text(rendered.auth_key_name, variables, candidates)
        rendered.auth_key_value = self._render_text(rendered.auth_key_value, variables, candidates)
        rendered.query_params = {
            self._render_text(name, variables, candidates): self._render_text(value, variables, candidates)
            for name, value in rendered.query_params.items()
        }
        rendered.headers = {
            self._render_text(name, variables, candidates): self._render_text(value, variables, candidates)
            for name, value in rendered.headers.items()
        }
        return rendered

    @staticmethod
    def _render_text(
        text: str,
        variables: dict[str, Any],
        auto_candidates: list[AutoParamCandidate] | None = None,
    ) -> str:
        """Replace ``{{variable}}`` placeholders in *text* with values
        from the *variables* dictionary.
        """
        def replace(match: re.Match[str]) -> str:
            variable_name = match.group(1)
            if variable_name in variables:
                value = variables[variable_name]
            else:
                candidate = WorkflowRunner._best_auto_candidate(variable_name, auto_candidates or [])
                value = candidate.value if candidate is not None else ""
            if isinstance(value, str):
                return value
            return json.dumps(value, ensure_ascii=False)

        return TEMPLATE_PATTERN.sub(replace, text)

    def _auto_fill_query_params(
        self,
        query_params: dict[str, str],
        auto_candidates: list[AutoParamCandidate],
    ) -> dict[str, Any]:
        """Fill blank query params from previous JSON response fields."""
        auto_params: dict[str, Any] = {}
        if not auto_candidates:
            return auto_params

        for param_name, current_value in list(query_params.items()):
            if str(current_value).strip():
                continue
            candidate = self._best_auto_candidate(param_name, auto_candidates)
            if candidate is None:
                continue
            query_params[param_name] = self._stringify_value(candidate.value)
            auto_params[param_name] = candidate.value
        return auto_params

    @classmethod
    def _best_auto_candidate(
        cls,
        target_name: str,
        candidates: list[AutoParamCandidate],
    ) -> AutoParamCandidate | None:
        best: AutoParamCandidate | None = None
        best_score = 0.0
        for candidate in reversed(candidates):
            score = max(
                cls._name_similarity(target_name, candidate.name),
                cls._name_similarity(target_name, candidate.path),
            )
            if score < AUTO_PARAM_SCORE_THRESHOLD:
                continue
            if score > best_score:
                best = candidate
                best_score = score
        return best

    @classmethod
    def _name_similarity(cls, left: str, right: str) -> float:
        left_tokens = cls._name_tokens(left)
        right_tokens = cls._name_tokens(right)
        if not left_tokens or not right_tokens:
            return 0.0

        left_normalized = "".join(left_tokens)
        right_normalized = "".join(right_tokens)
        if left_normalized == right_normalized:
            return 1.0

        sequence_score = difflib.SequenceMatcher(None, left_normalized, right_normalized).ratio()
        shared_tokens = set(left_tokens) & set(right_tokens)
        token_score = len(shared_tokens) / max(len(set(left_tokens)), len(set(right_tokens)))

        suffix_score = 0.0
        if len(left_normalized) >= 4 and right_normalized.endswith(left_normalized):
            suffix_score = 0.88
        elif len(right_normalized) >= 4 and left_normalized.endswith(right_normalized):
            suffix_score = 0.88

        return max(sequence_score, token_score, suffix_score)

    @staticmethod
    def _name_tokens(value: str) -> list[str]:
        spaced = CAMEL_BOUNDARY_PATTERN.sub(r"\1 \2", value)
        return [token.lower() for token in NAME_TOKEN_PATTERN.findall(spaced)]

    @staticmethod
    def _stringify_value(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)):
            return str(value).lower() if isinstance(value, bool) else str(value)
        return json.dumps(value, ensure_ascii=False)

    def _response_auto_candidates(self, response: HttpResponseData) -> list[AutoParamCandidate]:
        try:
            payload = json.loads(response.body)
        except json.JSONDecodeError:
            return []
        return list(self._iter_auto_candidates(payload))

    def _iter_auto_candidates(self, value: Any, path: str = ""):
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}" if path else key_text
                yield from self._iter_auto_candidates(item, child_path)
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                child_path = f"{path}[{index}]" if path else f"[{index}]"
                yield from self._iter_auto_candidates(item, child_path)
            return
        if path and isinstance(value, (str, int, float, bool)):
            name = self._leaf_name(path)
            if name:
                yield AutoParamCandidate(name=name, path=path, value=value)

    @staticmethod
    def _leaf_name(path: str) -> str:
        clean_path = re.sub(r"\[\d+]", "", path)
        return clean_path.rsplit(".", 1)[-1]

    @staticmethod
    def _merge_auto_variables(
        variables: dict[str, Any],
        candidates: list[AutoParamCandidate],
    ) -> None:
        for candidate in candidates:
            if TEMPLATE_PATTERN.fullmatch(f"{{{{{candidate.name}}}}}") and candidate.name not in variables:
                variables[candidate.name] = candidate.value

    def _extract_variables(
        self,
        response: HttpResponseData,
        extractors: dict[str, str],
    ) -> dict[str, Any]:
        """Parse the response body as JSON and extract variables
        defined by *extractors* (mapping variable names to JSON paths).

        Raises:
            ExtractionError: When the body is not valid JSON or a path
                cannot be resolved.
        """
        if not extractors:
            return {}

        try:
            payload = json.loads(response.body)
        except json.JSONDecodeError as error:
            raise ExtractionError("extraction_not_json", status=response.status) from error

        extracted: dict[str, Any] = {}
        for variable_name, path in extractors.items():
            extracted[variable_name] = self.extract_path(payload, path)
        return extracted

    @staticmethod
    def extract_path(payload: Any, path: str) -> Any:
        """Traverse a parsed JSON structure following a dot-separated path.

        Supports array indexing via ``key[0]`` notation.

        Args:
            payload: The parsed JSON object (dict/list).
            path: Dot-separated path, e.g. ``"data.items[0].id"``.

        Returns:
            The value found at the given path.

        Raises:
            ExtractionError: On invalid path syntax, missing keys,
                or type mismatches.
        """
        if "{{" in path or "}}" in path:
            raise ExtractionError("extraction_template_in_path")

        current = payload
        for part in path.split("."):
            if not part:
                continue

            match = PATH_TOKEN_PATTERN.fullmatch(part)
            if match is None:
                raise ExtractionError("extraction_invalid_path", path=path)

            key, index = match.groups()
            if not isinstance(current, dict) or key not in current:
                raise ExtractionError("extraction_key_not_found", key=key)

            current = current[key]
            if index is not None:
                if not isinstance(current, list):
                    raise ExtractionError("extraction_not_list", key=key)
                current = current[int(index)]

        return current


def parse_extractors(text: str) -> dict[str, str]:
    """Parse a multi-line extractor definition text into a dictionary.

    Each line should follow the format ``variable_name=json.path``.
    Lines can be separated by newlines, semicolons, or commas.

    Raises:
        ExtractorParseError: When a line does not match the expected format.
    """
    extractors: dict[str, str] = {}
    normalized = text.replace(";", "\n").replace(",", "\n")
    for raw_line in normalized.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        name, separator, path = line.partition("=")
        if not separator or not name.strip() or not path.strip():
            raise ExtractorParseError("extractor_format")
        extractors[name.strip()] = path.strip()
    return extractors


def format_extractors(extractors: dict[str, str]) -> str:
    """Serialize an extractors dictionary back into a semicolon-separated
    display string (e.g. ``"token=data.token; id=data.id"``).
    """
    return "; ".join(f"{name}={path}" for name, path in extractors.items())
