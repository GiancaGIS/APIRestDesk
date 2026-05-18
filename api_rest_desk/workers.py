from __future__ import annotations

import httpx
from PyQt6.QtCore import QThread, pyqtSignal

from api_rest_desk.http_client import RestClient
from api_rest_desk.models import RestCall, Workflow
from api_rest_desk.workflow import WorkflowRunner


class HttpWorker(QThread):
    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, call: RestCall, client: RestClient | None = None) -> None:
        super().__init__()
        self.call = call
        self.client = client or RestClient()

    def run(self) -> None:
        try:
            response = self.client.send(self.call)
        except httpx.HTTPError as error:
            self.failed.emit(str(error))
            return
        except ValueError as error:
            self.failed.emit(str(error))
            return

        self.finished_ok.emit(
            {
                "status": response.status,
                "reason": response.reason,
                "headers": response.headers,
                "body": response.body,
                "elapsed_ms": response.elapsed_ms,
                "size_bytes": response.size_bytes,
            }
        )


class WorkflowWorker(QThread):
    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, workflow: Workflow, calls: list[RestCall]) -> None:
        super().__init__()
        self.workflow = workflow
        self.calls = calls

    def run(self) -> None:
        try:
            result = WorkflowRunner().run(self.workflow, self.calls)
        except httpx.HTTPError as error:
            self.failed.emit(str(error))
            return
        except (KeyError, TypeError, ValueError) as error:
            self.failed.emit(str(error))
            return

        self.finished_ok.emit(
            {
                "variables": result.variables,
                "steps": [
                    {
                        "step_name": step.step_name,
                        "call_name": step.call_name,
                        "status": step.status,
                        "reason": step.reason,
                        "response_headers": step.response_headers,
                        "response_body": step.response_body,
                        "elapsed_ms": step.elapsed_ms,
                        "extracted": step.extracted,
                        "error": step.error,
                    }
                    for step in result.steps
                ],
            }
        )
