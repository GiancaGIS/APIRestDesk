from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from api_rest_desk.i18n import Translator
from api_rest_desk.models import RestCall, WorkflowStep
from api_rest_desk.settings import load_settings
from api_rest_desk.theme import set_status_badge, status_class
from api_rest_desk.workflow import format_extractors, parse_extractors


class WorkflowCanvasNode(QGraphicsObject):
    WIDTH = 230
    HEIGHT = 96

    def __init__(self, canvas: WorkflowCanvas, step: WorkflowStep, index: int) -> None:
        super().__init__()
        self.canvas = canvas
        self.step = step
        self.index = index
        self.status: int | None = None
        self.network_error = False
        self.status_text = "-"
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsObject.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.WIDTH, self.HEIGHT)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        del option, widget
        dark = self.canvas.dark_mode
        background = QColor("#0f172a" if dark else "#ffffff")
        border = QColor("#60a5fa" if self.isSelected() else ("#475569" if dark else "#cbd5e1"))
        text = QColor("#f8fafc" if dark else "#101828")
        muted = QColor("#cbd5e1" if dark else "#667085")

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(border, 2 if self.isSelected() else 1))
        painter.setBrush(background)
        painter.drawRoundedRect(self.boundingRect().adjusted(1, 1, -1, -1), 8, 8)

        badge_rect = QRectF(self.WIDTH - 58, 12, 42, 24)
        badge_bg, badge_fg = self._badge_colors()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(badge_bg)
        painter.drawRoundedRect(badge_rect, 12, 12)
        painter.setPen(badge_fg)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self.status_text)

        painter.setPen(muted)
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.drawText(QRectF(14, 10, 70, 20), Qt.AlignmentFlag.AlignLeft, f"{self.index + 1}.")

        title_rect = QRectF(14, 32, self.WIDTH - 28, 24)
        call_rect = QRectF(14, 58, self.WIDTH - 28, 22)
        painter.setPen(text)
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft, self._elide(painter, self.step.name or "Step"))

        painter.setPen(muted)
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(call_rect, Qt.AlignmentFlag.AlignLeft, self._elide(painter, self.canvas.call_label(self.step.call_id)))

    def itemChange(self, change: QGraphicsObject.GraphicsItemChange, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            position = self.pos()
            self.step.position_x = position.x()
            self.step.position_y = position.y()
            self.canvas.refresh_connections()
        return super().itemChange(change, value)

    def set_status(self, status: int | None, network_error: bool = False) -> None:
        self.status = status
        self.network_error = network_error
        self.status_text = "ERR" if network_error else (str(status) if status is not None else "-")
        self.update()

    def _badge_colors(self) -> tuple[QColor, QColor]:
        dark = self.canvas.dark_mode
        badge_class = status_class(self.status, self.network_error)
        colors = {
            "neutral": ("#334155", "#e2e8f0") if dark else ("#eef2f6", "#475467"),
            "success": ("#064e3b", "#bbf7d0") if dark else ("#dcfae6", "#027a48"),
            "redirect": ("#1e3a8a", "#bfdbfe") if dark else ("#d1e9ff", "#175cd3"),
            "client_error": ("#78350f", "#fde68a") if dark else ("#fef0c7", "#b54708"),
            "server_error": ("#7f1d1d", "#fecaca") if dark else ("#fee4e2", "#b42318"),
            "network_error": ("#7f1d1d", "#fecaca") if dark else ("#fee4e2", "#b42318"),
        }
        background, foreground = colors.get(badge_class, colors["neutral"])
        return QColor(background), QColor(foreground)

    @staticmethod
    def _elide(painter: QPainter, text: str) -> str:
        return painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, WorkflowCanvasNode.WIDTH - 28)


class WorkflowCanvas(QWidget):
    def __init__(
        self,
        calls: list[RestCall],
        translator: Translator | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.calls = calls
        self.translator = translator or Translator()
        self.t = self.translator.t
        self.dark_mode = str(load_settings().get("theme") or "light") == "dark"
        self._steps: list[WorkflowStep] = []
        self.nodes: list[WorkflowCanvasNode] = []
        self.connections: list[QGraphicsPathItem] = []
        self._updating_editor = False

        self._build_ui()
        self.retranslate_ui()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        self.scene = QGraphicsScene(self)
        self.scene.selectionChanged.connect(self._refresh_editor)
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setMinimumHeight(280)
        self.view.setSceneRect(0, 0, 1100, 520)
        self._apply_scene_colors()

        self.details = QFrame()
        self.details.setObjectName("Metrics")
        details_layout = QVBoxLayout(self.details)
        details_layout.setContentsMargins(12, 12, 12, 12)
        details_layout.setSpacing(8)

        self.details_title = QLabel()
        self.details_title.setObjectName("SectionTitle")
        details_layout.addWidget(self.details_title)

        self.status_label = QLabel()
        self.status_label.setObjectName("StatusBadge")
        set_status_badge(self.status_label, "-", None)
        details_layout.addWidget(self.status_label)

        self.name_label = QLabel()
        self.name_input = QLineEdit()
        self.name_input.textEdited.connect(self._update_selected_step)
        details_layout.addWidget(self.name_label)
        details_layout.addWidget(self.name_input)

        self.call_label_widget = QLabel()
        self.call_combo = QComboBox()
        self.call_combo.currentIndexChanged.connect(self._update_selected_step)
        details_layout.addWidget(self.call_label_widget)
        details_layout.addWidget(self.call_combo)

        self.extractors_label = QLabel()
        self.extractors_edit = QPlainTextEdit()
        self.extractors_edit.setMaximumHeight(120)
        self.extractors_edit.textChanged.connect(self._update_selected_step)
        details_layout.addWidget(self.extractors_label)
        details_layout.addWidget(self.extractors_edit)
        details_layout.addStretch(1)

        splitter.addWidget(self.view)
        splitter.addWidget(self.details)
        splitter.setSizes([680, 260])

    def retranslate_ui(self) -> None:
        self.t = self.translator.t
        self.details_title.setText(self.t("workflow_canvas_node_details"))
        self.name_label.setText(self.t("name"))
        self.call_label_widget.setText(self.t("call"))
        self.extractors_label.setText(self.t("extractors"))
        self.extractors_edit.setPlaceholderText("token=token; id=features[0].attributes.OBJECTID")
        self._fill_call_combo()
        self._refresh_editor()

    def set_steps(self, steps: list[WorkflowStep]) -> None:
        self._steps = steps[:]
        self._ensure_positions()
        self._rebuild_scene()

    def steps(self) -> list[WorkflowStep]:
        self._commit_editor()
        return self._steps[:]

    def add_step(self, step: WorkflowStep | None = None) -> None:
        if not isinstance(step, WorkflowStep):
            step = WorkflowStep(
                name=f"{self.t('step')} {len(self._steps) + 1}",
                call_id=self.calls[0].id if self.calls else "",
            )
        self._steps.append(step)
        self._ensure_positions()
        self._rebuild_scene(select_index=len(self._steps) - 1)

    def remove_selected(self) -> None:
        index = self._selected_index()
        if index is None:
            index = len(self._steps) - 1 if self._steps else None
        if index is None:
            return
        del self._steps[index]
        self._layout_steps()
        self._rebuild_scene(select_index=min(index, len(self._steps) - 1))

    def move_selected(self, direction: int) -> None:
        index = self._selected_index()
        if index is None:
            index = len(self._steps) - 1 if self._steps else None
        if index is None:
            return
        target = index + direction
        if target < 0 or target >= len(self._steps):
            return
        self._steps[index], self._steps[target] = self._steps[target], self._steps[index]
        self._layout_steps()
        self._rebuild_scene(select_index=target)

    def update_statuses(self, result: dict) -> None:
        steps = result.get("steps") if isinstance(result, dict) else []
        step_results = steps if isinstance(steps, list) else []
        for index, node in enumerate(self.nodes):
            if index >= len(step_results):
                node.set_status(None)
                continue
            step_result = step_results[index]
            if not isinstance(step_result, dict):
                node.set_status(None)
                continue
            status = step_result.get("status")
            error = str(step_result.get("error") or "")
            node.set_status(status if isinstance(status, int) else None, bool(error))
        self._refresh_editor()

    def refresh_connections(self) -> None:
        for connection in self.connections:
            self.scene.removeItem(connection)
        self.connections.clear()

        pen = QPen(QColor("#60a5fa" if self.dark_mode else "#2e6ff2"), 2)
        for left, right in zip(self.nodes, self.nodes[1:]):
            start = left.pos() + QPointF(WorkflowCanvasNode.WIDTH, WorkflowCanvasNode.HEIGHT / 2)
            end = right.pos() + QPointF(0, WorkflowCanvasNode.HEIGHT / 2)
            distance = max(80, abs(end.x() - start.x()) / 2)
            path = QPainterPath(start)
            path.cubicTo(start + QPointF(distance, 0), end - QPointF(distance, 0), end)
            connection = QGraphicsPathItem(path)
            connection.setPen(pen)
            connection.setZValue(-1)
            self.scene.addItem(connection)
            self.connections.append(connection)

    def call_label(self, call_id: str) -> str:
        call = next((item for item in self.calls if item.id == call_id), None)
        if call is None:
            return "-"
        return f"{call.method} {call.name}"

    def _rebuild_scene(self, select_index: int | None = None) -> None:
        self.scene.clear()
        self.nodes.clear()
        self.connections.clear()
        self._apply_scene_colors()

        for index, step in enumerate(self._steps):
            node = WorkflowCanvasNode(self, step, index)
            node.setPos(float(step.position_x or 0), float(step.position_y or 0))
            self.scene.addItem(node)
            self.nodes.append(node)

        self.refresh_connections()
        if select_index is not None and 0 <= select_index < len(self.nodes):
            self.nodes[select_index].setSelected(True)
            self.view.centerOn(self.nodes[select_index])
        self._refresh_editor()

    def _selected_node(self) -> WorkflowCanvasNode | None:
        for item in self.scene.selectedItems():
            if isinstance(item, WorkflowCanvasNode):
                return item
        return None

    def _selected_index(self) -> int | None:
        node = self._selected_node()
        if node is None or node not in self.nodes:
            return None
        return self.nodes.index(node)

    def _refresh_editor(self) -> None:
        node = self._selected_node()
        enabled = node is not None
        self._updating_editor = True
        self.name_input.setEnabled(enabled)
        self.call_combo.setEnabled(enabled)
        self.extractors_edit.setEnabled(enabled)

        if node is None:
            self.name_input.clear()
            self.call_combo.setCurrentIndex(-1)
            self.extractors_edit.clear()
            set_status_badge(self.status_label, "-", None)
        else:
            self.name_input.setText(node.step.name)
            index = self.call_combo.findData(node.step.call_id)
            self.call_combo.setCurrentIndex(index)
            self.extractors_edit.setPlainText(format_extractors(node.step.extractors))
            set_status_badge(self.status_label, node.status_text, node.status, node.network_error)
        self._updating_editor = False

    def _update_selected_step(self) -> None:
        if self._updating_editor:
            return
        node = self._selected_node()
        if node is None:
            return

        node.step.name = self.name_input.text().strip() or f"{self.t('step')} {node.index + 1}"
        node.step.call_id = str(self.call_combo.currentData() or "")
        try:
            node.step.extractors = parse_extractors(self.extractors_edit.toPlainText())
        except ValueError:
            pass
        node.update()

    def _commit_editor(self) -> None:
        node = self._selected_node()
        if node is None:
            return
        node.step.name = self.name_input.text().strip() or f"{self.t('step')} {node.index + 1}"
        node.step.call_id = str(self.call_combo.currentData() or "")
        node.step.extractors = parse_extractors(self.extractors_edit.toPlainText())
        node.update()

    def _fill_call_combo(self) -> None:
        current = self.call_combo.currentData()
        self.call_combo.blockSignals(True)
        self.call_combo.clear()
        for call in self.calls:
            self.call_combo.addItem(f"{call.collection} / {call.method} {call.name}", call.id)
        if current is not None:
            index = self.call_combo.findData(current)
            if index >= 0:
                self.call_combo.setCurrentIndex(index)
        self.call_combo.blockSignals(False)

    def _ensure_positions(self) -> None:
        for index, step in enumerate(self._steps):
            if step.position_x is None:
                step.position_x = 40 + (index * 270)
            if step.position_y is None:
                step.position_y = 120

    def _layout_steps(self) -> None:
        for index, step in enumerate(self._steps):
            step.position_x = 40 + (index * 270)
            step.position_y = 120

    def _apply_scene_colors(self) -> None:
        self.dark_mode = str(load_settings().get("theme") or "light") == "dark"
        self.scene.setBackgroundBrush(QColor("#111827" if self.dark_mode else "#f8fafc"))
