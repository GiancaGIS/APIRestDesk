import os
import tempfile
import threading
import time
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import httpx

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from api_rest_desk.config import APP_VERSION, GITHUB_REPOSITORY, UPDATE_CHECK_INTERVAL_MS
from api_rest_desk.i18n import Translator
from api_rest_desk.main_window import RestClientWindow
from api_rest_desk.settings import load_settings, save_settings
from api_rest_desk.settings_dialog import SettingsDialog
from api_rest_desk.updates import ReleaseInfo, UpdateCheckError, check_latest_release, version_tuple


NEW_VERSION = f"v{int(APP_VERSION.split('.')[0]) + 1}.0.0"
RELEASE_URL = f"https://github.com/{GITHUB_REPOSITORY}/releases/tag/{NEW_VERSION}"


class UpdateLookupTest(unittest.TestCase):
    def lookup(self, status=200, payload=None, content=None, error=None):
        real_client = httpx.Client

        def handle(request):
            self.assertEqual(str(request.url), f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest")
            self.assertEqual(request.headers["Accept"], "application/vnd.github+json")
            self.assertEqual(request.headers["User-Agent"], f"APIRestDesk/{APP_VERSION}")
            self.assertNotIn("Authorization", request.headers)
            self.assertNotIn("Cookie", request.headers)
            if error:
                raise error
            if content is not None:
                return httpx.Response(status, content=content)
            return httpx.Response(status, json=payload)

        def client_factory(**kwargs):
            self.assertEqual(kwargs["timeout"], 10.0)
            return real_client(transport=httpx.MockTransport(handle), **kwargs)

        with patch("api_rest_desk.updates.httpx.Client", side_effect=client_factory):
            return check_latest_release()

    def test_numeric_version_comparison(self):
        for latest, installed, expected in [
            (NEW_VERSION, "1.0.4", True),
            ("1.0.10", "1.0.9", True),
            ("V2.0", "1.99.99", True),
            ("1.0.4+build.3", "1.0.4", False),
            ("1.0.4.0", "1.0.4", False),
            ("1.0.3", "1.0.4", False),
        ]:
            with self.subTest(latest=latest):
                self.assertEqual(ReleaseInfo(latest, RELEASE_URL).is_newer_than(installed), expected)
        for tag in ["v1.0.5-rc.1", "release-1.0.5", "", "banana"]:
            with self.subTest(tag=tag), self.assertRaises(UpdateCheckError):
                version_tuple(tag)

    def test_published_release(self):
        release = self.lookup(payload={"tag_name": NEW_VERSION, "html_url": RELEASE_URL, "draft": False, "prerelease": False})
        self.assertEqual(release, ReleaseInfo(NEW_VERSION, RELEASE_URL))
        self.assertTrue(release.is_newer_than())

    def test_no_release_and_unstable_releases(self):
        self.assertIsNone(self.lookup(status=404))
        for flag in ("draft", "prerelease"):
            with self.subTest(flag=flag):
                self.assertIsNone(self.lookup(payload={flag: True}))

    def test_errors_are_reported_without_crashing(self):
        for status, key in [(403, "update_rate_limited"), (429, "update_rate_limited"), (500, "update_unavailable")]:
            with self.subTest(status=status), self.assertRaisesRegex(UpdateCheckError, key):
                self.lookup(status=status)
        with self.assertRaisesRegex(UpdateCheckError, "update_unavailable"):
            self.lookup(error=httpx.ConnectError("offline"))
        with self.assertRaisesRegex(UpdateCheckError, "update_unavailable"):
            self.lookup(error=httpx.ReadTimeout("timeout"))

    def test_invalid_payload_and_version(self):
        for payload in [[], {}, {"tag_name": 105, "html_url": RELEASE_URL}]:
            with self.subTest(payload=payload), self.assertRaisesRegex(UpdateCheckError, "update_invalid_response"):
                self.lookup(payload=payload)
        with self.assertRaisesRegex(UpdateCheckError, "update_invalid_response"):
            self.lookup(content=b"not JSON")
        with self.assertRaisesRegex(UpdateCheckError, "update_invalid_version"):
            self.lookup(payload={"tag_name": "not-a-version", "html_url": RELEASE_URL})

    def test_release_links_are_limited_to_the_project_on_github(self):
        for url in [
            "https://example.com/update",
            "http://github.com/GiancaGIS/APIRestDesk/releases/tag/v1.0.5",
            "https://github.com/another/project/releases/tag/v1.0.5",
            "file:///tmp/update.exe",
            "https://[broken",
        ]:
            with self.subTest(url=url), self.assertRaisesRegex(UpdateCheckError, "update_invalid_response"):
                self.lookup(payload={"tag_name": NEW_VERSION, "html_url": url})


class UpdateWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        directory = self.stack.enter_context(tempfile.TemporaryDirectory())
        self.stack.enter_context(patch("api_rest_desk.settings.SETTINGS_FILE", Path(directory) / "settings.json"))
        for name, value in [("load_collection", []), ("load_folders", []), ("load_history", []), ("load_session_cookies", {})]:
            self.stack.enter_context(patch(f"api_rest_desk.main_window.{name}", return_value=value))
        self.settings = {"check_updates_automatically": True, "language": "en"}
        save_settings(self.settings)
        self.window = RestClientWindow()
        self.addCleanup(self.close_window)

    def close_window(self):
        if self.window._update_dialog is not None:
            self.window._update_dialog.reject()
        if self.window._update_worker is not None:
            self.window._update_worker.wait(2000)
            self.app.processEvents()
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def wait_for(self, predicate):
        deadline = time.monotonic() + 2
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertTrue(predicate())

    def test_automatic_checks_can_be_disabled_and_reenabled(self):
        self.assertTrue(self.window._update_startup_timer.isActive())
        self.assertEqual(self.window._update_timer.interval(), UPDATE_CHECK_INTERVAL_MS)
        self.settings["check_updates_automatically"] = False
        save_settings(self.settings)
        self.window._configure_update_checks()
        self.assertFalse(self.window._update_timer.isActive())
        self.assertFalse(self.window._update_startup_timer.isActive())
        with patch.object(self.window, "_check_updates") as check:
            self.window._check_updates_automatically()
            check.assert_not_called()
        self.settings["check_updates_automatically"] = True
        save_settings(self.settings)
        self.window._configure_update_checks()
        self.assertTrue(self.window._update_timer.isActive())
        self.assertTrue(self.window._update_startup_timer.isActive())

    def test_old_settings_enable_updates_and_checkbox_persists(self):
        save_settings({"language": "en"})
        self.assertTrue(load_settings()["check_updates_automatically"])
        dialog = SettingsDialog(Translator("en"))
        self.assertTrue(dialog.auto_updates_check.isChecked())
        dialog.auto_updates_check.setChecked(False)
        dialog.accept()
        self.assertFalse(load_settings()["check_updates_automatically"])
        dialog.deleteLater()

    def test_new_release_is_announced_once_and_manual_check_can_announce_again(self):
        release = ReleaseInfo(NEW_VERSION, RELEASE_URL)
        self.window._update_check_succeeded(release)
        self.assertIsNotNone(self.window._update_dialog)
        self.assertIn(NEW_VERSION, self.window._update_dialog.text())
        self.window._update_dialog.reject()
        self.assertIsNone(self.window._update_dialog)
        self.window._update_check_succeeded(release)
        self.assertIsNone(self.window._update_dialog)
        self.window._update_manual = True
        self.window._update_check_succeeded(release)
        self.assertIsNotNone(self.window._update_dialog)

    def test_open_release_uses_browser_only_after_button_click(self):
        with patch("api_rest_desk.main_window.QDesktopServices.openUrl", return_value=True) as open_url:
            self.window._update_check_succeeded(ReleaseInfo(NEW_VERSION, RELEASE_URL))
            open_url.assert_not_called()
            button = next(button for button in self.window._update_dialog.buttons() if button.text() == "Open release")
            button.click()
            self.assertEqual(open_url.call_args.args[0].toString(), RELEASE_URL)
            self.assertIsNone(self.window._update_dialog)

    def test_manual_results_and_errors_while_automatic_checks_stay_quiet(self):
        with patch("api_rest_desk.main_window.QMessageBox.information") as info, patch("api_rest_desk.main_window.QMessageBox.warning") as warning:
            self.window._update_check_succeeded(None)
            self.window._update_check_succeeded(ReleaseInfo(APP_VERSION, RELEASE_URL))
            self.window._update_check_failed("update_unavailable")
            info.assert_not_called()
            warning.assert_not_called()
            self.window._update_manual = True
            self.window._update_check_succeeded(None)
            self.assertIn("No published stable release", info.call_args.args[2])
            self.window._update_check_succeeded(ReleaseInfo(APP_VERSION, RELEASE_URL))
            self.assertIn("up to date", info.call_args.args[2])
            self.window._update_check_failed("update_rate_limited")
            self.assertIn("limited requests", warning.call_args.args[2])

    def test_disabling_checks_suppresses_an_inflight_automatic_result(self):
        self.settings["check_updates_automatically"] = False
        save_settings(self.settings)
        self.window._update_check_succeeded(ReleaseInfo(NEW_VERSION, RELEASE_URL))
        self.assertIsNone(self.window._update_dialog)

    def test_manual_check_runs_in_background_even_when_automatic_checks_are_disabled(self):
        self.settings["check_updates_automatically"] = False
        save_settings(self.settings)
        self.window._configure_update_checks()
        with patch("api_rest_desk.workers.check_latest_release", return_value=ReleaseInfo(NEW_VERSION, RELEASE_URL)) as lookup:
            self.window.check_updates_action.trigger()
            self.assertFalse(self.window.check_updates_action.isEnabled())
            self.window._check_updates(manual=True)
            self.wait_for(lambda: self.window._update_worker is None)
            self.assertTrue(self.window.check_updates_action.isEnabled())
            self.assertIsNotNone(self.window._update_dialog)
            lookup.assert_called_once()

    def test_network_failure_worker_cleans_up_and_allows_retry(self):
        with patch("api_rest_desk.workers.check_latest_release", side_effect=UpdateCheckError("update_unavailable")), patch("api_rest_desk.main_window.QMessageBox.warning") as warning:
            self.window._check_updates(manual=True)
            self.wait_for(lambda: self.window._update_worker is None)
            warning.assert_called_once()
            self.assertTrue(self.window.check_updates_action.isEnabled())

    def test_window_remains_responsive_and_closes_after_running_check_finishes(self):
        gate = threading.Event()
        ticks = []

        def slow_lookup():
            gate.wait(2)
            return ReleaseInfo(NEW_VERSION, RELEASE_URL)

        self.window.show()
        with patch("api_rest_desk.workers.check_latest_release", side_effect=slow_lookup):
            try:
                self.window._check_updates()
                QTimer.singleShot(0, lambda: ticks.append(True))
                self.wait_for(lambda: bool(ticks))
                self.assertIsNotNone(self.window._update_worker)
                self.assertFalse(self.window.close())
                self.assertTrue(self.window._closing_for_update)
            finally:
                gate.set()
            self.wait_for(lambda: self.window._update_worker is None)
            self.assertFalse(self.window.isVisible())
            self.assertIsNone(self.window._update_dialog)


if __name__ == "__main__":
    unittest.main()
