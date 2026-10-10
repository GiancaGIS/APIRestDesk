import asyncio
import json
import os
import tempfile
import threading
import time
import unittest
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qsl, urlencode

import httpx

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtTest import QSignalSpy, QTest
from PyQt6.QtWidgets import QApplication, QMessageBox

from api_rest_desk.exceptions import MissingVariablesError
from api_rest_desk.http_client import RestClient
from api_rest_desk.i18n import Translator
from api_rest_desk.main_window import RestClientWindow
from api_rest_desk.models import CallHistory, HttpResponseData, RestCall, Workflow, WorkflowStep
from api_rest_desk.settings import active_environment_variables, load_settings, normalize_settings, save_settings, update_setting
from api_rest_desk.settings_dialog import SettingsDialog
from api_rest_desk.storage import load_history, save_history
from api_rest_desk.workflow import WorkflowRunner, ensure_resolved_variables
from api_rest_desk.workflow_dialog import WorkflowDialog
from api_rest_desk.workers import HttpWorker, WorkflowWorker


def response():
    return HttpResponseData(200, "OK", {}, '{"token":"abc"}', 1.0, 15)


class WaitingClient:
    def __init__(self, completed_calls=0):
        self.calls = []
        self.completed_calls = completed_calls
        self.waiting = threading.Event()
        self.cleaned_up = threading.Event()

    async def send_async(self, call):
        self.calls.append(call)
        if len(self.calls) <= self.completed_calls:
            await asyncio.sleep(0)
            return response()
        self.waiting.set()
        try:
            await asyncio.sleep(600)
        finally:
            self.cleaned_up.set()


class ModelOptionsTest(unittest.TestCase):
    def test_tls_defaults_are_safe_for_legacy_and_invalid_data(self):
        for value in (None, "false", 0, {}, []):
            with self.subTest(value=value):
                self.assertTrue(RestCall.from_dict({"name": "Test", "verify": value}).verify)
        self.assertTrue(RestCall.from_dict({"name": "Legacy"}).verify)
        self.assertTrue(CallHistory.from_dict({}).request_verify)
        self.assertFalse(RestCall.from_dict({"name": "Test", "verify": False}).verify)

    def test_history_round_trip_preserves_tls_and_disabled_parameters(self):
        history = CallHistory(
            timestamp="2026-10-10T12:00:00", name="Test", method="GET", url="https://example.test",
            request_verify=False, request_query_params={"active": "1", "disabled": "2"},
            request_disabled_query_params=["disabled"],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            save_history([history], path)
            restored = load_history(path)[0]
        self.assertEqual(asdict(restored), asdict(history))


class EnvironmentDataTest(unittest.TestCase):
    def test_legacy_variables_migrate_without_loss(self):
        settings = normalize_settings({"environment": {"base_url": "https://dev.test", "token": "secret"}})
        self.assertEqual(settings["active_environment"], "development")
        self.assertEqual(settings["environments"]["development"], settings["environment"])
        self.assertEqual(active_environment_variables(settings)["token"], "secret")
        self.assertEqual(set(settings["environments"]), {"development", "test", "production"})

    def test_named_environments_are_authoritative_and_invalid_selection_is_repaired(self):
        settings = normalize_settings({
            "environments": {"staging": {"base_url": "https://stage.test"}},
            "environment": {"base_url": "stale"}, "active_environment": "missing",
        })
        self.assertEqual(settings["active_environment"], "staging")
        self.assertEqual(settings["environment"]["base_url"], "https://stage.test")

    def test_settings_and_variables_are_independent_copies(self):
        first = normalize_settings({})
        first["environments"]["development"]["token"] = "private"
        self.assertEqual(normalize_settings({})["environments"]["development"], {})
        copied = active_environment_variables(first)
        copied["token"] = "modified"
        self.assertEqual(first["environments"]["development"]["token"], "private")

    def test_missing_variables_ignore_disabled_params_and_inactive_auth(self):
        call = RestCall(
            name="Test", url="https://example.test", query_params={"skip": "{{missing}}"},
            disabled_query_params=["skip"], auth_token="{{unused}}",
        )
        ensure_resolved_variables(call)
        call.auth_type = "bearer"
        with self.assertRaises(MissingVariablesError):
            ensure_resolved_variables(call)

    def test_form_variables_are_decoded_rendered_and_encoded_once(self):
        call = RestCall(name="Form", method="POST", url="https://example.test", body_type="form", body=urlencode({"token": "{{token}}", "{{field}}": ""}))
        rendered = WorkflowRunner()._render_call(call, {"token": "a+b&c", "field": "label"})
        self.assertEqual(dict(parse_qsl(rendered.body, keep_blank_values=True)), {"token": "a+b&c", "label": ""})
        ensure_resolved_variables(rendered)
        with self.assertRaises(MissingVariablesError):
            ensure_resolved_variables(call)

    def test_workflow_checks_variables_after_previous_extractions(self):
        calls = [RestCall(name="Login", url="https://example.test/login"), RestCall(name="Data", url="https://example.test/data", auth_type="bearer", auth_token="{{token}}")]

        class Client:
            def send(self, call):
                self.token = call.auth_token
                return response()

        client = Client()
        workflow = Workflow(name="Test", steps=[WorkflowStep(calls[0].id, extractors={"token": "token"}), WorkflowStep(calls[1].id)])
        result = WorkflowRunner(client, environment={}).run(workflow, calls)
        self.assertEqual(len(result.steps), 2)
        self.assertEqual(client.token, "abc")


class AsyncHttpTest(unittest.IsolatedAsyncioTestCase):
    async def test_sync_and_async_transports_send_the_same_request(self):
        real_sync, real_async = httpx.Client, httpx.AsyncClient
        requests = []

        def handle(request):
            requests.append((request.method, str(request.url), request.headers.get("Authorization"), request.content))
            return httpx.Response(200, json={"ok": True})

        transport = httpx.MockTransport(handle)
        with patch("api_rest_desk.http_client.httpx.Client", side_effect=lambda **kwargs: real_sync(transport=transport, **kwargs)), patch("api_rest_desk.http_client.httpx.AsyncClient", side_effect=lambda **kwargs: real_async(transport=transport, **kwargs)):
            for call in [
                RestCall(name="GET", url="https://example.test", query_params={"active": "1", "disabled": "2"}, disabled_query_params=["disabled"], auth_type="bearer", auth_token="abc"),
                RestCall(name="JSON", method="POST", url="https://example.test", body_type="json", body='{"hello":"world"}', verify=False),
                RestCall(name="Form", method="POST", url="https://example.test", body_type="form", body="a=1&b=2"),
            ]:
                sync_result = RestClient().send(call)
                async_result = await RestClient().send_async(call)
                self.assertEqual(requests[-2], requests[-1])
                self.assertEqual(sync_result.body, async_result.body)
        self.assertNotIn("disabled", requests[0][1])

    async def test_cancellation_interrupts_response_read_and_closes_stream(self):
        entered, closed = asyncio.Event(), asyncio.Event()

        class Stream(httpx.AsyncByteStream):
            async def __aiter__(self):
                entered.set()
                await asyncio.sleep(600)
                yield b"never"

            async def aclose(self):
                closed.set()

        real_client = httpx.AsyncClient
        transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=Stream()))
        with patch("api_rest_desk.http_client.httpx.AsyncClient", side_effect=lambda **kwargs: real_client(transport=transport, **kwargs)):
            task = asyncio.create_task(RestClient().send_async(RestCall(name="Slow", url="https://example.test", timeout=600)))
            await asyncio.wait_for(entered.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, 1)
            self.assertTrue(closed.is_set())

    async def test_cancellation_during_retry_delay_does_not_send_again(self):
        entered = asyncio.Event()
        attempts = []

        def handle(request):
            attempts.append(request)
            entered.set()
            return httpx.Response(503)

        real_client = httpx.AsyncClient
        with patch("api_rest_desk.http_client.httpx.AsyncClient", side_effect=lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs)):
            task = asyncio.create_task(RestClient().send_async(RestCall(name="Retry", url="https://example.test", retry_count=10)))
            await asyncio.wait_for(entered.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, 1)
            self.assertEqual(len(attempts), 1)


class WindowBehaviorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.directory = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch("api_rest_desk.settings.SETTINGS_FILE", self.directory / "settings.json"))
        save_settings({"language": "en", "check_updates_automatically": False, "environments": {
            "development": {"base_url": "https://dev.test"},
            "production": {"base_url": "https://prod.test"},
        }, "active_environment": "development"})
        self.calls = []
        for name, value in [("load_collection", self.calls), ("load_folders", []), ("load_history", []), ("load_session_cookies", {})]:
            self.stack.enter_context(patch(f"api_rest_desk.main_window.{name}", return_value=value))
        for name in ("save_collection", "save_folders", "save_history"):
            self.stack.enter_context(patch(f"api_rest_desk.main_window.{name}"))
        self.stack.enter_context(patch("api_rest_desk.workflow_dialog.save_workflows"))
        self.window = RestClientWindow()
        self.workers = []
        self.dialogs = []
        self.addCleanup(self.cleanup_windows)

    def cleanup_windows(self):
        workers = self.workers + [self.window.current_worker]
        if self.window._workflow_dialog is not None:
            workers.append(self.window._workflow_dialog.current_worker)
        for worker in workers:
            if worker is not None:
                worker.cancel()
                worker.wait(2000)
        self.app.processEvents()
        for dialog in self.dialogs:
            dialog.close()
            dialog.deleteLater()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def wait_for(self, predicate):
        deadline = time.monotonic() + 2
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertTrue(predicate())

    def test_request_duplication_preserves_every_option_and_uses_a_new_id(self):
        call = RestCall(name="All options", url="https://example.test", verify=False, timeout=45, follow_redirects=False, retry_count=2, use_session_cookies=True, assertions="status == 200", query_params={"disabled": "2"}, disabled_query_params=["disabled"])
        self.calls.append(call)
        self.window._populate_call_list()
        self.window._select_call(call.id)
        self.window._duplicate_call()
        duplicate = self.calls[-1]
        self.assertNotEqual(call.id, duplicate.id)
        for key, value in asdict(call).items():
            if key not in {"name", "id"}:
                self.assertEqual(getattr(duplicate, key), value)

    def test_history_restore_and_import_reset_all_editor_options(self):
        history = CallHistory(timestamp="", name="History", method="GET", url="https://example.test", request_verify=False, request_query_params={"off": "1"}, request_disabled_query_params=["off"])
        self.window.history.append(history)
        self.window._populate_history_list()
        self.window.history_list.setCurrentRow(0)
        self.window._load_current_history_request()
        self.assertFalse(self.window.verify_rest_call.isChecked())
        self.assertEqual(self.window.params_editor.disabled_keys(), ["off"])
        self.window.use_session_cookies_check.setChecked(True)
        self.window.assertions_editor.setPlainText("status == 500")
        self.window._apply_call_to_editor(RestCall(name="Imported"))
        self.assertTrue(self.window.verify_rest_call.isChecked())
        self.assertFalse(self.window.use_session_cookies_check.isChecked())
        self.assertEqual(self.window.assertions_editor.toPlainText(), "")

    def test_selector_changes_request_rendering_and_persists_active_environment(self):
        call = RestCall(name="Test", url="{{base_url}}/resource")
        self.assertEqual(self.window._render_call_for_send(call).url, "https://dev.test/resource")
        combo = self.window.environment_selector.combo
        combo.setCurrentIndex(combo.findData("production"))
        self.assertEqual(load_settings()["active_environment"], "production")
        self.assertEqual(self.window._render_call_for_send(call).url, "https://prod.test/resource")
        self.assertEqual(call.url, "{{base_url}}/resource")

    def test_settings_keep_edits_when_switching_and_cancel_does_not_save(self):
        dialog = SettingsDialog(Translator("en"))
        self.dialogs.append(dialog)
        dialog.environment_editor.set_values({"base_url": "https://changed.test"})
        combo = dialog.environment_combo
        combo.setCurrentIndex(combo.findData("production"))
        dialog.environment_editor.set_values({"token": "production-token"})
        combo.setCurrentIndex(combo.findData("development"))
        self.assertEqual(dialog.environment_editor.values()["base_url"], "https://changed.test")
        dialog.reject()
        self.assertEqual(active_environment_variables()["base_url"], "https://dev.test")
        dialog.accept()
        self.assertEqual(load_settings()["environments"]["production"], {"token": "production-token"})

    def test_settings_add_rename_delete_and_prevent_deleting_the_last_environment(self):
        dialog = SettingsDialog(Translator("en"))
        self.dialogs.append(dialog)
        with patch("api_rest_desk.settings_dialog.QInputDialog.getText", return_value=("Staging", True)):
            dialog._add_environment()
        dialog.environment_editor.set_values({"base_url": "https://staging.test"})
        with patch("api_rest_desk.settings_dialog.QInputDialog.getText", return_value=("Preview", True)):
            dialog._rename_environment()
        self.assertEqual(dialog.environments["Preview"]["base_url"], "https://staging.test")
        with patch("api_rest_desk.settings_dialog.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            dialog._delete_environment()
            dialog._delete_environment()
            dialog._delete_environment()
        self.assertEqual(len(dialog.environments), 1)
        self.assertFalse(dialog.delete_environment_button.isEnabled())
        dialog.accept()
        self.assertEqual(len(load_settings()["environments"]), 1)

    def test_missing_variables_stop_request_before_worker_start(self):
        self.window.url_input.setText("{{unknown_base}}/resource")
        with patch("api_rest_desk.main_window.QMessageBox.warning") as warning:
            self.window._send_current_call()
            warning.assert_called_once()
        self.assertIsNone(self.window.current_worker)
        self.assertEqual(self.window.history, [])

    def test_cancel_request_releases_worker_and_allows_another_request(self):
        client = WaitingClient()
        self.window.url_input.setText("{{base_url}}/slow")
        with patch("api_rest_desk.main_window.RestClient", return_value=client):
            self.window._send_current_call()
            self.wait_for(client.waiting.is_set)
            self.assertEqual(client.calls[0].url, "https://dev.test/slow")
            self.assertFalse(self.window.send_action.isEnabled())
            worker = self.window.current_worker
            self.window._send_current_call()
            self.assertIs(self.window.current_worker, worker)
            self.window.cancel_request_button.click()
            self.wait_for(lambda: self.window.current_worker is None)
        self.assertTrue(client.cleaned_up.is_set())
        self.assertIsNone(self.window.pending_call)
        self.assertEqual(self.window.history, [])
        self.assertTrue(self.window.send_button.isEnabled())
        self.assertTrue(self.window.send_action.isEnabled())

    def test_cancel_before_worker_start_emits_only_cancellation(self):
        client = WaitingClient()
        worker = HttpWorker(RestCall(name="Test"), client)
        self.workers.append(worker)
        cancelled, failed, success = QSignalSpy(worker.cancelled), QSignalSpy(worker.failed), QSignalSpy(worker.finished_ok)
        worker.cancel()
        worker.start()
        self.wait_for(lambda: len(cancelled) == 1 and not worker.isRunning())
        self.assertEqual(len(failed), 0)
        self.assertEqual(len(success), 0)
        self.assertEqual(client.calls, [])

    def test_cancel_workflow_preserves_completed_steps_and_environment_snapshot(self):
        calls = [RestCall(name="First", url="{{base_url}}/first"), RestCall(name="Second", url="{{base_url}}/second", auth_type="bearer", auth_token="{{token}}"), RestCall(name="Third", url="{{base_url}}/third")]
        workflow = Workflow(name="Test", steps=[WorkflowStep(calls[0].id, extractors={"token": "token"}), WorkflowStep(calls[1].id), WorkflowStep(calls[2].id)])
        client = WaitingClient(completed_calls=1)
        worker = WorkflowWorker(workflow, calls, client)
        self.workers.append(worker)
        cancelled, progress = QSignalSpy(worker.cancelled), QSignalSpy(worker.progress)
        update_setting("active_environment", "production")
        worker.start()
        self.wait_for(client.waiting.is_set)
        worker.cancel()
        worker.cancel()
        self.wait_for(lambda: len(cancelled) == 1 and not worker.isRunning())
        result = cancelled[0][0]
        self.assertEqual(result["environment"], "development")
        self.assertEqual(len(result["steps"]), 1)
        self.assertEqual(result["variables"]["token"], "abc")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(client.calls[1].url, "https://dev.test/second")
        self.assertEqual(client.calls[1].auth_token, "abc")
        self.assertEqual([entry[0] for entry in progress], [1, 2])

    def open_workflow(self, calls):
        workflow = Workflow(name="Test", steps=[WorkflowStep(call.id) for call in calls])
        self.window.calls = calls
        with patch("api_rest_desk.workflow_dialog.load_workflows", return_value=[workflow]):
            self.window._open_workflow_dialog()
        return self.window._workflow_dialog

    def test_main_and_workflow_selectors_stay_in_sync(self):
        dialog = self.open_workflow([RestCall(name="Step", url="https://example.test")])
        combo = dialog.environment_selector.combo
        combo.setCurrentIndex(combo.findData("production"))
        self.assertEqual(self.window.environment_selector.combo.currentData(), "production")
        combo = self.window.environment_selector.combo
        combo.setCurrentIndex(combo.findData("development"))
        self.assertEqual(dialog.environment_selector.combo.currentData(), "development")

    def test_closing_main_window_cancels_request_and_workflow_without_destroying_threads(self):
        self.window.show()
        calls = [RestCall(name="Step", url="https://example.test")]
        dialog = self.open_workflow(calls)
        request_client, workflow_client = WaitingClient(), WaitingClient()
        self.window.url_input.setText("https://example.test")
        with patch("api_rest_desk.main_window.RestClient", return_value=request_client), patch("api_rest_desk.workers.RestClient", return_value=workflow_client), patch("api_rest_desk.workflow.RestClient", return_value=workflow_client):
            self.window._send_current_call()
            dialog._run_current_workflow()
            self.wait_for(lambda: request_client.waiting.is_set() and workflow_client.waiting.is_set())
            self.assertFalse(self.window.close())
            self.wait_for(lambda: not self.window.isVisible())
        self.assertTrue(request_client.cleaned_up.is_set())
        self.assertTrue(workflow_client.cleaned_up.is_set())

    def test_escape_cancels_workflow_and_defers_dialog_close_until_cleanup(self):
        dialog = self.open_workflow([RestCall(name="Step", url="https://example.test")])
        client = WaitingClient()
        with patch("api_rest_desk.workflow.RestClient", return_value=client):
            dialog._run_current_workflow()
            self.wait_for(client.waiting.is_set)
            dialog.reject()
            self.assertIsNotNone(dialog.current_worker)
            self.wait_for(lambda: self.window._workflow_dialog is None)
        self.assertTrue(client.cleaned_up.is_set())


if __name__ == "__main__":
    unittest.main()
