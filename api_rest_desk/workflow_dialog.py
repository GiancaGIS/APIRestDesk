from __future__ import annotations

import json

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from api_rest_desk.exceptions import ExtractorParseError
from api_rest_desk.models import RestCall, Workflow, WorkflowStep
from api_rest_desk.storage import StorageError, load_workflows, save_workflows
from api_rest_desk.i18n import Translator
from api_rest_desk.theme import apply_theme
from api_rest_desk.toast import ToastNotification
from api_rest_desk.workflow import format_extractors, parse_extractors
from api_rest_desk.workflow_canvas import WorkflowCanvas
from api_rest_desk.workers import WorkflowWorker


class WorkflowDialog(QDialog):
    navigate_to_call = pyqtSignal(str)

    def __init__(
        self,
        calls: list[RestCall],
        translator: Translator | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Workflow")
        self.resize(980, 660)
        self.setMinimumSize(900, 560)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.calls = calls
        self.translator = translator or Translator()
        self.t = self.translator.t
        self.workflows = self._read_workflows()
        self.current_worker: WorkflowWorker | None = None
        self.toast: ToastNotification | None = None
        self._active_mode = "linear"

        self._build_ui()
        self._apply_style()
        self.toast = ToastNotification(self)
        self.retranslate_ui()
        self._populate_workflows()

        if self.workflows:
            self.workflow_list.setCurrentRow(0)
        else:
            self._new_workflow()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        left = QFrame()
        left.setObjectName("Panel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)
        self.workflow_title = QLabel()
        self.workflow_title.setObjectName("SectionTitle")
        left_layout.addWidget(self.workflow_title)

        self.workflow_list = QListWidget()
        self.workflow_list.currentItemChanged.connect(self._load_selected_workflow)
        left_layout.addWidget(self.workflow_list, 1)

        workflow_buttons = QHBoxLayout()
        self.new_button = QPushButton()
        self.delete_button = QPushButton()
        self.delete_button.setObjectName("Danger")
        self.new_button.clicked.connect(self._new_workflow)
        self.delete_button.clicked.connect(self._delete_workflow)
        workflow_buttons.addWidget(self.new_button)
        workflow_buttons.addWidget(self.delete_button)
        left_layout.addLayout(workflow_buttons)

        right = QFrame()
        right.setObjectName("Panel")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(12)

        name_row = QHBoxLayout()
        self.name_label = QLabel()
        name_row.addWidget(self.name_label)
        self.name_input = QLineEdit()
        name_row.addWidget(self.name_input, 1)
        self.mode_label = QLabel()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("", "linear")
        self.mode_combo.addItem("", "canvas")
        self.mode_combo.currentIndexChanged.connect(self._handle_mode_changed)
        name_row.addWidget(self.mode_label)
        name_row.addWidget(self.mode_combo)
        right_layout.addLayout(name_row)

        self.auto_params_checkbox = QCheckBox()
        right_layout.addWidget(self.auto_params_checkbox)

        self.workflow_splitter = QSplitter(Qt.Orientation.Vertical)
        right_layout.addWidget(self.workflow_splitter, 1)

        editor_area = QWidget()
        editor_area_layout = QVBoxLayout(editor_area)
        editor_area_layout.setContentsMargins(0, 0, 0, 0)
        editor_area_layout.setSpacing(10)

        self.mode_stack = QStackedWidget()
        editor_area_layout.addWidget(self.mode_stack, 1)

        self.linear_view = QWidget()
        linear_layout = QVBoxLayout(self.linear_view)
        linear_layout.setContentsMargins(0, 0, 0, 0)
        linear_layout.setSpacing(10)

        self.steps_table = QTableWidget(0, 3)
        self.steps_table.setHorizontalHeaderLabels(("Step", "Chiamata", "Estrazioni"))
        self.steps_table.verticalHeader().setVisible(False)
        self.steps_table.setColumnWidth(0, 180)
        self.steps_table.setColumnWidth(1, 280)
        self.steps_table.horizontalHeader().setStretchLastSection(True)
        linear_layout.addWidget(self.steps_table, 1)

        step_buttons = QHBoxLayout()
        self.add_step_button = QPushButton()
        self.remove_step_button = QPushButton()
        self.move_up_button = QPushButton()
        self.move_down_button = QPushButton()
        self.add_step_button.clicked.connect(self._add_step)
        self.remove_step_button.clicked.connect(self._remove_selected_step)
        self.move_up_button.clicked.connect(lambda: self._move_selected_step(-1))
        self.move_down_button.clicked.connect(lambda: self._move_selected_step(1))
        step_buttons.addWidget(self.add_step_button)
        step_buttons.addWidget(self.remove_step_button)
        step_buttons.addWidget(self.move_up_button)
        step_buttons.addWidget(self.move_down_button)
        step_buttons.addStretch(1)

        self.canvas_view = QWidget()
        canvas_layout = QVBoxLayout(self.canvas_view)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(10)
        self.canvas_hint = QLabel()
        self.canvas_hint.setObjectName("MutedLabel")
        self.canvas_hint.setWordWrap(True)
        canvas_layout.addWidget(self.canvas_hint)
        self.workflow_canvas = WorkflowCanvas(self.calls, self.translator)
        canvas_layout.addWidget(self.workflow_canvas, 1)

        self.mode_stack.addWidget(self.linear_view)
        self.mode_stack.addWidget(self.canvas_view)
        editor_area_layout.addLayout(step_buttons)

        action_buttons = QHBoxLayout()
        self.save_button = QPushButton()
        self.save_button.setObjectName("Secondary")
        self.run_button = QPushButton()
        self.run_button.setObjectName("Primary")
        self.save_button.clicked.connect(self._save_current_workflow)
        self.run_button.clicked.connect(self._run_current_workflow)
        action_buttons.addStretch(1)
        action_buttons.addWidget(self.save_button)
        action_buttons.addWidget(self.run_button)
        editor_area_layout.addLayout(action_buttons)

        result_area = QWidget()
        result_area.setMinimumHeight(260)
        result_layout = QVBoxLayout(result_area)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(8)
        self.result_title = QLabel()
        self.result_title.setObjectName("SectionTitle")
        result_layout.addWidget(self.result_title)

        result_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumWidth(320)
        result_splitter.addWidget(self.output)

        step_output_area = QWidget()
        step_output_area.setMinimumWidth(360)
        step_output_layout = QVBoxLayout(step_output_area)
        step_output_layout.setContentsMargins(0, 0, 0, 0)
        step_output_layout.setSpacing(8)
        self.step_outputs_title = QLabel()
        self.step_outputs_title.setObjectName("SectionTitle")
        self.step_output_combo = QComboBox()
        self.step_output_combo.setMinimumHeight(36)
        self.step_output_combo.currentIndexChanged.connect(self._show_selected_step_output)
        self.step_output_tabs = QTabWidget()
        self.step_output_body = QPlainTextEdit()
        self.step_output_body.setReadOnly(True)
        self.step_output_headers = QPlainTextEdit()
        self.step_output_headers.setReadOnly(True)
        self.step_output_tabs.addTab(self.step_output_body, "")
        self.step_output_tabs.addTab(self.step_output_headers, "")
        step_output_layout.addWidget(self.step_outputs_title)
        step_output_layout.addWidget(self.step_output_combo)
        step_output_layout.addWidget(self.step_output_tabs, 1)
        result_splitter.addWidget(step_output_area)
        result_splitter.setSizes([360, 420])
        result_layout.addWidget(result_splitter, 1)

        self.workflow_splitter.addWidget(editor_area)
        self.workflow_splitter.addWidget(result_area)
        self.workflow_splitter.setSizes([380, 280])

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([240, 740])

    def _apply_style(self) -> None:
        apply_theme(self)

    def retranslate_ui(self) -> None:
        self.t = self.translator.t
        self.setWindowTitle(self.t("workflow"))
        self.workflow_title.setText(self.t("workflow"))
        self.new_button.setText(self.t("workflow_new"))
        self.delete_button.setText(self.t("delete"))
        self.name_label.setText(self.t("name"))
        self.name_input.setPlaceholderText(self.t("workflow_name_placeholder"))
        self.mode_label.setText(self.t("workflow_mode"))
        self.mode_combo.setItemText(0, self.t("workflow_mode_linear"))
        self.mode_combo.setItemText(1, self.t("workflow_mode_canvas"))
        self.auto_params_checkbox.setText(self.t("workflow_auto_params"))
        self.auto_params_checkbox.setToolTip(self.t("workflow_auto_params_tooltip"))
        self.canvas_hint.setText(self.t("workflow_mode_canvas_info"))
        self.workflow_canvas.retranslate_ui()
        self.steps_table.setHorizontalHeaderLabels(
            (self.t("step"), self.t("call"), self.t("extractors"))
        )
        self.add_step_button.setText(self.t("add_step"))
        self.remove_step_button.setText(self.t("remove_step"))
        self.move_up_button.setText(self.t("move_up"))
        self.move_down_button.setText(self.t("move_down"))
        self.save_button.setText(self.t("save_workflow"))
        self.run_button.setText(self.t("run_workflow"))
        self.result_title.setText(self.t("workflow_result_summary"))
        self.step_outputs_title.setText(self.t("workflow_step_outputs"))
        self.step_output_tabs.setTabText(0, self.t("body"))
        self.step_output_tabs.setTabText(1, self.t("headers"))
        self.output.setPlaceholderText(self.t("workflow_output_placeholder"))
        self._sync_mode_view()

    def _read_workflows(self) -> list[Workflow]:
        try:
            return load_workflows()
        except StorageError as error:
            QMessageBox.warning(self, self.t("workflow_read_error"), str(error))
            return []

    def _populate_workflows(self) -> None:
        self.workflow_list.clear()
        for workflow in self.workflows:
            item = QListWidgetItem(workflow.name)
            item.setData(Qt.ItemDataRole.UserRole, workflow.id)
            self.workflow_list.addItem(item)

    def _selected_workflow(self) -> Workflow | None:
        item = self.workflow_list.currentItem()
        if item is None:
            return None
        workflow_id = item.data(Qt.ItemDataRole.UserRole)
        return next((workflow for workflow in self.workflows if workflow.id == workflow_id), None)

    def _load_selected_workflow(self) -> None:
        workflow = self._selected_workflow()
        if workflow is None:
            return

        self.name_input.setText(workflow.name)
        self.auto_params_checkbox.setChecked(workflow.auto_map_params)
        index = self.mode_combo.findData(workflow.mode)
        self.mode_combo.setCurrentIndex(index if index >= 0 else 0)
        self.steps_table.setRowCount(0)
        self.workflow_canvas.set_steps(workflow.steps)
        for step in workflow.steps:
            self._add_step_row(step)
        self._sync_mode_view()
        self._active_mode = str(self.mode_combo.currentData() or "linear")

    def _new_workflow(self) -> None:
        workflow = Workflow(name=self.t("workflow_new"), mode="linear")
        self.workflows.append(workflow)
        self._populate_workflows()
        self._select_workflow(workflow.id)

    def _delete_workflow(self) -> None:
        workflow = self._selected_workflow()
        if workflow is None:
            return

        self.workflows = [item for item in self.workflows if item.id != workflow.id]
        save_workflows(self.workflows)
        self._populate_workflows()
        if self.workflows:
            self.workflow_list.setCurrentRow(0)
        else:
            self._new_workflow()

    def _select_workflow(self, workflow_id: str) -> None:
        for row in range(self.workflow_list.count()):
            item = self.workflow_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == workflow_id:
                self.workflow_list.setCurrentRow(row)
                return

    def _add_step_row(self, step: WorkflowStep | None = None) -> None:
        if not isinstance(step, WorkflowStep):
            step = None

        row = self.steps_table.rowCount()
        self.steps_table.insertRow(row)
        self.steps_table.setRowHeight(row, 42)

        name_item = QTableWidgetItem(step.name if step else f"{self.t('step')} {row + 1}")
        self.steps_table.setItem(row, 0, name_item)

        call_combo = QComboBox()
        for call in self.calls:
            label = f"{call.collection} / {call.method} {call.name}"
            call_combo.addItem(label, call.id)
        if step is not None:
            index = call_combo.findData(step.call_id)
            if index >= 0:
                call_combo.setCurrentIndex(index)
        self.steps_table.setCellWidget(row, 1, call_combo)

        extracts_item = QTableWidgetItem(format_extractors(step.extractors) if step else "")
        extracts_item.setToolTip("Formato: token=token; id=features[0].attributes.OBJECTID")
        self.steps_table.setItem(row, 2, extracts_item)

    def _add_step(self) -> None:
        mode = str(self.mode_combo.currentData() or "linear")
        if mode == "canvas":
            self.workflow_canvas.add_step()
        elif mode == "linear":
            self._add_step_row()

    def _remove_selected_step(self) -> None:
        if str(self.mode_combo.currentData() or "linear") == "canvas":
            self.workflow_canvas.remove_selected()
            return

        rows = sorted({index.row() for index in self.steps_table.selectedIndexes()}, reverse=True)
        if not rows and self.steps_table.rowCount() > 0:
            rows = [self.steps_table.rowCount() - 1]
        for row in rows:
            self.steps_table.removeRow(row)

    def _move_selected_step(self, direction: int) -> None:
        if str(self.mode_combo.currentData() or "linear") == "canvas":
            self.workflow_canvas.move_selected(direction)
            return

        row = self.steps_table.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= self.steps_table.rowCount():
            return

        workflow = self._workflow_from_ui()
        workflow.steps[row], workflow.steps[target] = workflow.steps[target], workflow.steps[row]
        self.steps_table.setRowCount(0)
        for step in workflow.steps:
            self._add_step_row(step)
        self.steps_table.selectRow(target)

    def _workflow_from_ui(self) -> Workflow:
        selected = self._selected_workflow()
        workflow = Workflow(
            name=self.name_input.text().strip() or self.t("workflow_new"),
            mode=str(self.mode_combo.currentData() or "linear"),
            auto_map_params=self.auto_params_checkbox.isChecked(),
        )
        if selected is not None:
            workflow.id = selected.id

        workflow.steps = self._steps_from_mode(workflow.mode)

        return workflow

    def _steps_from_mode(self, mode: str) -> list[WorkflowStep]:
        if mode == "canvas":
            return self.workflow_canvas.steps()
        return self._steps_from_table()

    def _replace_steps_in_mode(self, mode: str, steps: list[WorkflowStep]) -> None:
        if mode == "canvas":
            self.workflow_canvas.set_steps(steps)
        else:
            self.steps_table.setRowCount(0)
            for step in steps:
                self._add_step_row(step)

    def _steps_from_table(self) -> list[WorkflowStep]:
        steps: list[WorkflowStep] = []
        for row in range(self.steps_table.rowCount()):
            call_combo = self.steps_table.cellWidget(row, 1)
            if not isinstance(call_combo, QComboBox):
                continue

            name_item = self.steps_table.item(row, 0)
            extracts_item = self.steps_table.item(row, 2)
            steps.append(
                WorkflowStep(
                    name=name_item.text().strip() if name_item else f"{self.t('step')} {row + 1}",
                    call_id=str(call_combo.currentData() or ""),
                    extractors=parse_extractors(extracts_item.text() if extracts_item else ""),
                )
            )
        return steps

    def _save_current_workflow(self) -> Workflow | None:
        try:
            workflow = self._workflow_from_ui()
        except ExtractorParseError as error:
            QMessageBox.warning(self, self.t("invalid_extractors_title"), str(error))
            return None

        selected = self._selected_workflow()
        if selected is None:
            self.workflows.append(workflow)
        else:
            workflow.id = selected.id
            index = self.workflows.index(selected)
            self.workflows[index] = workflow

        save_workflows(self.workflows)
        self._populate_workflows()
        self._select_workflow(workflow.id)
        return workflow

    def _run_current_workflow(self) -> None:
        workflow = self._save_current_workflow()
        if workflow is None:
            return
        if workflow.mode not in {"linear", "canvas"}:
            QMessageBox.information(self, self.t("workflow"), self.t("workflow_mode_not_runnable"))
            return
        if not workflow.steps:
            QMessageBox.information(self, self.t("workflow"), self.t("workflow_empty_message"))
            return

        self.run_button.setDisabled(True)
        self.run_button.setText(self.t("workflow_running"))
        self.output.setPlainText(self.t("workflow_running"))
        self._clear_step_outputs()
        self._update_block_statuses({"steps": []})

        self.current_worker = WorkflowWorker(workflow, self.calls)
        self.current_worker.finished_ok.connect(self._show_run_result)
        self.current_worker.failed.connect(self._show_run_error)
        self.current_worker.finished.connect(self._reset_run_button)
        self.current_worker.start()

    def _reset_run_button(self) -> None:
        self.run_button.setDisabled(False)
        self.run_button.setText(self.t("run_workflow"))

    def _show_run_result(self, result: dict) -> None:
        self.output.setPlainText(json.dumps(self._summary_result(result), indent=2, ensure_ascii=False))
        self._populate_step_outputs(result)
        self._update_block_statuses(result)
        if self._result_has_step_error(result):
            self._show_toast(self.t("workflow_completed_with_errors"), "warning")
        else:
            self._show_toast(self.t("workflow_completed"), "success")

    def _show_run_error(self, error: str) -> None:
        self.output.setPlainText(error)
        self._clear_step_outputs()
        self._update_block_statuses({"steps": []})
        self._show_toast(self.t("workflow_failed"), "error")

    def _summary_result(self, result: dict) -> dict:
        if not isinstance(result, dict):
            return {}
        summary = {"variables": result.get("variables", {}), "steps": []}
        steps = result.get("steps") if isinstance(result.get("steps"), list) else []
        for step in steps:
            if not isinstance(step, dict):
                continue
            body = str(step.get("response_body") or "")
            summary["steps"].append(
                {
                    "step_name": step.get("step_name"),
                    "call_name": step.get("call_name"),
                    "status": step.get("status"),
                    "reason": step.get("reason"),
                    "elapsed_ms": step.get("elapsed_ms"),
                    "extracted": step.get("extracted", {}),
                    "auto_params": step.get("auto_params", {}),
                    "response_size": len(body.encode("utf-8")),
                    "error": step.get("error", ""),
                }
            )
        return summary

    @staticmethod
    def _result_has_step_error(result: dict) -> bool:
        steps = result.get("steps") if isinstance(result, dict) else []
        if not isinstance(steps, list):
            return False
        return any(isinstance(step, dict) and bool(step.get("error")) for step in steps)

    def _populate_step_outputs(self, result: dict) -> None:
        self._clear_step_outputs()
        steps = result.get("steps") if isinstance(result, dict) else []
        if not isinstance(steps, list):
            return

        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue
            status = step.get("status")
            status_text = "ERR" if step.get("error") else (str(status) if isinstance(status, int) else "-")
            label = f"{index}. {status_text}  {step.get('step_name') or step.get('call_name') or 'Step'}"
            self.step_output_combo.addItem(label, step)

        if self.step_output_combo.count() > 0:
            self.step_output_combo.setCurrentIndex(0)

    def _clear_step_outputs(self) -> None:
        self.step_output_combo.clear()
        self.step_output_body.clear()
        self.step_output_headers.clear()

    def _show_selected_step_output(self, index: int) -> None:
        if index < 0:
            self.step_output_body.clear()
            self.step_output_headers.clear()
            return
        step = self.step_output_combo.itemData(index)
        if not isinstance(step, dict):
            return
        body = str(step.get("response_body") or step.get("error") or "")
        headers = step.get("response_headers")
        self.step_output_body.setPlainText(self._format_body(body))
        self.step_output_headers.setPlainText(self._headers_to_text(headers if isinstance(headers, dict) else {}))

    @staticmethod
    def _headers_to_text(headers: dict[str, str]) -> str:
        return "\n".join(f"{key}: {value}" for key, value in headers.items())

    @staticmethod
    def _format_body(body: str) -> str:
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            return body
        return json.dumps(parsed, indent=2, ensure_ascii=False)

    def _show_toast(self, message: str, kind: str = "info") -> None:
        if self.toast is not None:
            self.toast.show_message(message, kind)

    def _update_block_statuses(self, result: dict) -> None:
        mode = str(self.mode_combo.currentData() or "linear")
        if mode == "canvas":
            self.workflow_canvas.update_statuses(result)

    def _handle_mode_changed(self) -> None:
        new_mode = str(self.mode_combo.currentData() or "linear")
        old_mode = self._active_mode

        if old_mode != new_mode:
            try:
                steps = self._steps_from_mode(old_mode)
                self._replace_steps_in_mode(new_mode, steps)
            except ExtractorParseError as error:
                QMessageBox.warning(self, self.t("invalid_extractors_title"), str(error))
                previous_index = self.mode_combo.findData(old_mode)
                if previous_index >= 0:
                    self.mode_combo.blockSignals(True)
                    self.mode_combo.setCurrentIndex(previous_index)
                    self.mode_combo.blockSignals(False)
                self._sync_mode_view()
                return

        self._active_mode = new_mode
        self._sync_mode_view()

    def _sync_mode_view(self) -> None:
        mode = str(self.mode_combo.currentData() or "linear")
        index_by_mode = {"linear": 0, "canvas": 1}
        self.mode_stack.setCurrentIndex(index_by_mode.get(mode, 0))
        editable = mode in {"linear", "canvas"}
        for button in (
            self.add_step_button,
            self.remove_step_button,
            self.move_up_button,
            self.move_down_button,
        ):
            button.setEnabled(editable)
