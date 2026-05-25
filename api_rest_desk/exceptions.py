from __future__ import annotations


ERROR_MESSAGES: dict[str, dict[str, str]] = {
    "it": {
        "no_http_response": "Nessuna risposta HTTP ricevuta.",
        "curl_no_url": "cURL senza URL.",
        "curl_option_no_value": "Opzione cURL senza valore: {option}",
        "curl_parse_failed": "cURL non valido: {detail}",
        "openapi_root_not_object": "Il documento OpenAPI deve essere un oggetto JSON.",
        "openapi_no_paths": "Il documento OpenAPI non contiene l'oggetto paths.",
        "import_root_not_object": "Il file importato deve essere un oggetto JSON.",
        "extraction_not_json": "La risposta con status '{status}' non e un JSON valido.",
        "extraction_invalid_path": "Percorso JSON non valido: {path}",
        "extraction_key_not_found": "Chiave non trovata: {key}",
        "extraction_not_list": "'{key}' non e una lista.",
        "extraction_template_in_path": (
            "Percorso JSON non valido: non usare {{{{variabile}}}} nelle Estrazioni. "
            "Qui va indicato il percorso nella response, ad esempio token=token "
            "oppure token=data.access_token. "
            "Usa poi {{{{token}}}} negli step successivi."
        ),
        "extractor_format": "Usa il formato 'variabile=percorso.json'.",
        "header_missing_name": "Riga {row}: seleziona o scrivi il nome dell'header.",
        "assertion_unknown": "Assertion non riconosciuta.",
    },
    "en": {
        "no_http_response": "No HTTP response received.",
        "curl_no_url": "cURL without URL.",
        "curl_option_no_value": "cURL option without value: {option}",
        "curl_parse_failed": "Invalid cURL: {detail}",
        "openapi_root_not_object": "OpenAPI document must be a JSON object.",
        "openapi_no_paths": "OpenAPI document has no paths object.",
        "import_root_not_object": "Imported file must be a JSON object.",
        "extraction_not_json": "Response with status '{status}' is not valid JSON.",
        "extraction_invalid_path": "Invalid JSON path: {path}",
        "extraction_key_not_found": "Key not found: {key}",
        "extraction_not_list": "'{key}' is not a list.",
        "extraction_template_in_path": (
            "Invalid JSON path: do not use {{{{variable}}}} in Extractors. "
            "Specify the response path here, e.g. token=token "
            "or token=data.access_token. "
            "Then use {{{{token}}}} in subsequent steps."
        ),
        "extractor_format": "Use the format 'variable=json.path'.",
        "header_missing_name": "Row {row}: select or type the header name.",
        "assertion_unknown": "Unknown assertion.",
    },
}

_current_language: str = "it"


def set_error_language(language: str) -> None:
    """Set the active language for exception messages.

    Args:
        language: ISO language code (``"it"`` or ``"en"``).
            Ignored when the code is not present in *ERROR_MESSAGES*.
    """
    global _current_language
    if language in ERROR_MESSAGES:
        _current_language = language


def _err(key: str, **kwargs: object) -> str:
    """Resolve an error message key into a human-readable string
    using the currently active language.

    Args:
        key: Lookup key in the *ERROR_MESSAGES* dictionary.
        **kwargs: Format parameters to interpolate into the message template.

    Returns:
        The localized message string.
    """
    messages = ERROR_MESSAGES.get(_current_language, ERROR_MESSAGES["it"])
    text = messages.get(key, key)
    return text.format(**kwargs) if kwargs else text


# ── Eccezione base ───────────────────────────────────────────

class RestDeskError(Exception):
    """Base exception for all application-level errors.

    Accepts a translation key and optional format parameters.
    The user-facing message is resolved at raise-time in the
    currently active language.
    """

    def __init__(self, key: str, /, **kwargs: object) -> None:
        self.key = key
        self.params = kwargs
        super().__init__(_err(key, **kwargs))


# ── HTTP Client ──────────────────────────────────────────────

class HttpClientError(RestDeskError):
    """Generic HTTP client error."""


class NoResponseError(HttpClientError):
    """No HTTP response was received after all retry attempts."""


# ── cURL ─────────────────────────────────────────────────────

class CurlParseError(RestDeskError):
    """Failed to parse a cURL command string."""


# ── OpenAPI ──────────────────────────────────────────────────

class OpenApiParseError(RestDeskError):
    """Failed to parse an OpenAPI document."""


# ── Import / Export workspace ────────────────────────────────

class ImportExportError(RestDeskError):
    """Error during workspace import or export."""


# ── Workflow ─────────────────────────────────────────────────

class WorkflowError(RestDeskError):
    """Generic error during workflow execution."""


class ExtractionError(WorkflowError):
    """Failed to extract variables from a JSON response body."""


class ExtractorParseError(WorkflowError):
    """Invalid extractor definition format."""


# ── Assertions ───────────────────────────────────────────────

class AssertionAPIError(RestDeskError):
    """Failed to evaluate a test assertion expression."""


# ── Headers ──────────────────────────────────────────────────

class HeaderParseError(RestDeskError):
    """Invalid or incomplete HTTP header definition."""
