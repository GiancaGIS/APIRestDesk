import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QCheckBox, QLineEdit

from api_rest_desk.http_client import RestClient
from api_rest_desk.models import RestCall
from api_rest_desk.storage import load_collection, save_collection
from api_rest_desk.widgets import KeyValueEditor
from api_rest_desk.workflow import AutoParamCandidate, WorkflowRunner


class _FakeResponse:
    status_code = 200
    reason_phrase = "OK"
    headers: dict[str, str] = {}
    text = ""
    content = b""


class _FakeClient:
    last_params = None

    def __init__(self, **kwargs) -> None:
        del kwargs
        self.cookies: dict[str, str] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        del exc_type, exc_value, traceback

    def request(self, **kwargs):
        type(self).last_params = kwargs["params"]
        return _FakeResponse()


class DisabledQueryParamsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_editor_keeps_disabled_row_but_greys_its_inputs(self) -> None:
        editor = KeyValueEditor(checkable=True)
        editor.set_values({"active": "1", "inactive": "2"}, ["inactive"])

        checkbox = editor.table.cellWidget(1, 0)
        key_input = editor.table.cellWidget(1, 1)
        value_input = editor.table.cellWidget(1, 2)

        self.assertIsInstance(checkbox, QCheckBox)
        self.assertIsInstance(key_input, QLineEdit)
        self.assertIsInstance(value_input, QLineEdit)
        self.assertFalse(checkbox.isChecked())
        self.assertFalse(key_input.isEnabled())
        self.assertFalse(value_input.isEnabled())
        self.assertEqual(editor.values(), {"active": "1", "inactive": "2"})
        self.assertEqual(editor.disabled_keys(), ["inactive"])

        checkbox.setChecked(True)
        self.assertTrue(key_input.isEnabled())
        self.assertTrue(value_input.isEnabled())
        self.assertEqual(editor.disabled_keys(), [])

    def test_disabled_state_round_trips_and_old_data_stays_compatible(self) -> None:
        call = RestCall.from_dict(
            {
                "name": "Example",
                "query_params": {"active": "1", "inactive": "2"},
                "disabled_query_params": ["inactive"],
            }
        )

        self.assertEqual(call.disabled_query_params, ["inactive"])
        self.assertEqual(call.active_query_params(), {"active": "1"})
        self.assertEqual(
            RestCall.from_dict({"name": "Old data"}).disabled_query_params,
            [],
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "collection.json"
            save_collection([call], path)
            restored = load_collection(path)[0]
        self.assertEqual(restored.query_params, call.query_params)
        self.assertEqual(restored.disabled_query_params, ["inactive"])

    def test_http_client_sends_only_active_query_params(self) -> None:
        call = RestCall(
            name="Example",
            url="https://example.test",
            query_params={"active": "1", "inactive": "2"},
            disabled_query_params=["inactive"],
        )

        with patch("api_rest_desk.http_client.httpx.Client", _FakeClient):
            RestClient().send(call)

        self.assertEqual(_FakeClient.last_params, {"active": "1"})

    def test_workflow_preserves_disabled_param_after_template_rendering(self) -> None:
        call = RestCall(
            name="Example",
            query_params={"{{param_name}}": "", "active": ""},
            disabled_query_params=["{{param_name}}"],
        )
        rendered, auto_params = WorkflowRunner()._prepare_call(
            call,
            {"param_name": "inactive"},
            [
                AutoParamCandidate("inactive", "inactive", "skip"),
                AutoParamCandidate("active", "active", "use"),
            ],
            auto_map_params=True,
        )

        self.assertEqual(rendered.disabled_query_params, ["inactive"])
        self.assertEqual(rendered.query_params["inactive"], "")
        self.assertEqual(rendered.query_params["active"], "use")
        self.assertEqual(auto_params, {"active": "use"})


if __name__ == "__main__":
    unittest.main()
