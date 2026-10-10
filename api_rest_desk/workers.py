from __future__ import annotations

import asyncio
import threading
from copy import deepcopy
from dataclasses import asdict

import httpx
from PyQt6.QtCore import QThread, pyqtSignal

from api_rest_desk.exceptions import RestDeskError
from api_rest_desk.http_client import RestClient
from api_rest_desk.models import RestCall, Workflow
from api_rest_desk.workflow import WorkflowRunner
from api_rest_desk.updates import UpdateCheckError, check_latest_release
from api_rest_desk.settings import active_environment_variables, load_settings


class UpdateCheckWorker(QThread):
    """Check GitHub releases without blocking the UI."""

    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            release = check_latest_release()
        except UpdateCheckError as error:
            self.failed.emit(str(error))
            return
        self.finished_ok.emit(release)


class CancellableWorker(QThread):
    """Own an asyncio loop in a Qt thread and cancel its task safely from the UI."""

    finished_ok = pyqtSignal(dict)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cancel_event = threading.Event()
        self._task_lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task | None = None

    @property
    def cancel_requested(self) -> bool:
        return self._cancel_event.is_set()

    def cancel(self) -> None:
        with self._task_lock:
            if self._cancel_event.is_set():
                return
            self._cancel_event.set()
            if self._loop is not None and self._task is not None:
                self._loop.call_soon_threadsafe(self._task.cancel)

    async def _run_async(self) -> dict:
        with self._task_lock:
            self._loop = asyncio.get_running_loop()
            self._task = asyncio.current_task()
        try:
            if self.cancel_requested:
                raise asyncio.CancelledError
            return await self._execute()
        finally:
            with self._task_lock:
                self._loop = None
                self._task = None

    def run(self) -> None:
        try:
            result = asyncio.run(self._run_async())
        except asyncio.CancelledError:
            self.cancelled.emit(self._cancelled_result())
            return
        except (httpx.HTTPError, httpx.InvalidURL, RestDeskError, ValueError) as error:
            if self.cancel_requested:
                self.cancelled.emit(self._cancelled_result())
            else:
                self.failed.emit(str(error))
            return
        if self.cancel_requested:
            self.cancelled.emit(self._cancelled_result())
        else:
            self.finished_ok.emit(result)

    async def _execute(self) -> dict:
        raise NotImplementedError

    def _cancelled_result(self):
        return None


class HttpWorker(CancellableWorker):
    """Execute a snapshot of one request with cancellable async HTTP I/O."""

    def __init__(self, call: RestCall, client: RestClient | None = None, parent=None) -> None:
        super().__init__(parent)
        self.call = deepcopy(call)
        self.client = client or RestClient()

    async def _execute(self) -> dict:
        response = await self.client.send_async(self.call)
        return asdict(response)


class WorkflowWorker(CancellableWorker):
    """Execute a workflow snapshot and retain completed steps on cancellation."""

    progress = pyqtSignal(int, int, str)

    def __init__(
        self, workflow: Workflow, calls: list[RestCall], client: RestClient | None = None, parent=None
    ) -> None:
        super().__init__(parent)
        self.workflow = deepcopy(workflow)
        self.calls = deepcopy(calls)
        settings = load_settings()
        self.environment_name = settings["active_environment"]
        self.runner = WorkflowRunner(
            client=client, environment=active_environment_variables(settings), progress=self.progress.emit
        )

    async def _execute(self) -> dict:
        result = await self.runner.run_async(self.workflow, self.calls)
        return {"environment": self.environment_name, **asdict(result)}

    def _cancelled_result(self):
        return {"environment": self.environment_name, **asdict(self.runner.last_result)}
