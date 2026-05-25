from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPainterPath, QPen, QPolygonF, QWheelEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from api_rest_desk.i18n import Translator
from api_rest_desk.models import RestCall, WorkflowStep
from api_rest_desk.settings import load_settings
from api_rest_desk.theme import PALETTE, set_status_badge, status_class
from api_rest_desk.workflow import format_extractors, parse_extractors


ZOOM_FACTOR = 1.15
ZOOM_MIN = 0.3
ZOOM_MAX = 3.0
ARROW_SIZE = 10.0


class WorkflowCanvasNode(QGraphicsObject):
    """Draggable node representing a single workflow step on the canvas."""

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
        self.setAcceptHoverEvents(True)
        self.setToolTip(self._build_tooltip())

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.WIDTH, self.HEIGHT)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        del option, widget
        dark = self.canvas.dark_mode
        background = QColor(PALETTE["dark_void"] if dark else PALETTE["white"])
        border = QColor(PALETTE["cornflower_blue"] if self.isSelected() else (PALETTE["charcoal_blue"] if dark else PALETTE["silver_gray"]))
        text = QColor(PALETTE["snow_white"] if dark else PALETTE["rich_black"])
        muted = QColor(PALETTE["silver_gray"] if dark else PALETTE["dim_gray"])

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

    def contextMenuEvent(self, event) -> None:
        """Show a right-click context menu on the node."""
        menu = QMenu()
        t = self.canvas.translator.t
        delete_action = menu.addAction(t("delete"))
        move_up_action = menu.addAction(t("move_up"))
        move_down_action = menu.addAction(t("move_down"))

        chosen = menu.exec(event.screenPos())
        if chosen == delete_action:
            idx = self.canvas.nodes.index(self) if self in self.canvas.nodes else None
            if idx is not None:
                del self.canvas._steps[idx]
                self.canvas._layout_steps()
                self.canvas._rebuild_scene(select_index=min(idx, len(self.canvas._steps) - 1))
        elif chosen == move_up_action:
            self.canvas.move_selected(-1)
        elif chosen == move_down_action:
            self.canvas.move_selected(1)

    def itemChange(self, change: QGraphicsObject.GraphicsItemChange, value):
        if change == QGraphicsObject.GraphicsItemChange.ItemPositionHasChanged:
            position = self.pos()
            self.step.position_x = position.x()
            self.step.position_y = position.y()
            self.canvas.refresh_connections()
            self.canvas.update_drop_candidate(self)
            self.canvas._fit_scene_rect()
        return super().itemChange(change, value)

    def mousePressEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.canvas.commit_drop_candidate(self)

    def set_status(self, status: int | None, network_error: bool = False) -> None:
        """Update the node's status badge and tooltip."""
        self.status = status
        self.network_error = network_error
        self.status_text = "ERR" if network_error else (str(status) if status is not None else "-")
        self.setToolTip(self._build_tooltip())
        self.update()

    def _build_tooltip(self) -> str:
        """Build a rich tooltip with step name, call label, and status."""
        call = self.canvas.call_label(self.step.call_id)
        lines = [
            f"<b>{self.step.name or 'Step'}</b>",
            call,
        ]
        if self.status is not None:
            lines.append(f"Status: {self.status_text}")
        if self.step.extractors:
            lines.append(f"Extractors: {format_extractors(self.step.extractors)}")
        return "<br>".join(lines)

    def _badge_colors(self) -> tuple[QColor, QColor]:
        dark = self.canvas.dark_mode
        badge_class = status_class(self.status, self.network_error)
        colors = {
            "neutral": (PALETTE["dark_gunmetal"], PALETTE["pale_slate"]) if dark else (PALETTE["light_blue_gray"], PALETTE["gunmetal"]),
            "success": (PALETTE["deep_emerald"], PALETTE["light_mint"]) if dark else (PALETTE["pale_mint_green"], PALETTE["forest_green"]),
            "redirect": (PALETTE["deep_sapphire"], PALETTE["baby_blue"]) if dark else (PALETTE["pale_cerulean"], PALETTE["denim_blue"]),
            "client_error": (PALETTE["chocolate_brown"], PALETTE["buff_yellow"]) if dark else (PALETTE["champagne"], PALETTE["burnt_orange"]),
            "server_error": (PALETTE["maroon"], PALETTE["light_coral"]) if dark else (PALETTE["pale_pink"], PALETTE["crimson_red"]),
            "network_error": (PALETTE["maroon"], PALETTE["light_coral"]) if dark else (PALETTE["pale_pink"], PALETTE["crimson_red"]),
        }
        background, foreground = colors.get(badge_class, colors["neutral"])
        return QColor(background), QColor(foreground)

    @staticmethod
    def _elide(painter: QPainter, text: str) -> str:
        return painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, WorkflowCanvasNode.WIDTH - 28)


class _ZoomableView(QGraphicsView):
    """QGraphicsView subclass with mouse-wheel zoom and keyboard shortcuts."""

    def __init__(self, scene: QGraphicsScene, canvas: WorkflowCanvas) -> None:
        super().__init__(scene)
        self._canvas = canvas
        self._zoom = 1.0
        self._panning = False
        self._pan_start = QPointF()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom in/out with the mouse wheel."""
        # ...existing code...
        if event.angleDelta().y() > 0:
            factor = ZOOM_FACTOR
        else:
            factor = 1 / ZOOM_FACTOR

        new_zoom = self._zoom * factor
        if new_zoom < ZOOM_MIN or new_zoom > ZOOM_MAX:
            return

        self._zoom = new_zoom
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.scale(factor, factor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start panning when the middle mouse button is pressed."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Pan the canvas while the middle button is held down."""
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Stop panning when the middle button is released."""
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle Delete key to remove the selected node."""
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._canvas.remove_selected()
        else:
            super().keyPressEvent(event)


class WorkflowCanvas(QWidget):
    """Visual canvas editor for building workflows by dragging nodes
    and connecting them with bezier curves.
    """

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
        self.connections: list[dict] = []
        self.drop_candidate: tuple[int, int] | None = None
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
        self.view = _ZoomableView(self.scene, self)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.view.setMinimumHeight(280)
        self.view.setSceneRect(0, 0, 1100, 520)
        self._apply_scene_colors()

        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        self.home_button = QPushButton("⌂ Home")
        self.home_button.setFixedHeight(28)
        self.home_button.setMaximumWidth(90)
        self.home_button.setToolTip("Fit all nodes in view")
        self.home_button.clicked.connect(self.fit_all)
        toolbar.addWidget(self.home_button)
        toolbar.addStretch(1)
        canvas_layout.addLayout(toolbar)
        canvas_layout.addWidget(self.view, 1)

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

        splitter.addWidget(canvas_container)
        splitter.addWidget(self.details)
        splitter.setSizes([680, 260])

    def retranslate_ui(self) -> None:
        self.t = self.translator.t
        self.home_button.setText(f"⌂ {self.t('canvas_home')}")
        self.home_button.setToolTip(self.t("canvas_home_tooltip"))
        self.details_title.setText(self.t("workflow_canvas_node_details"))
        self.name_label.setText(self.t("name"))
        self.call_label_widget.setText(self.t("call"))
        self.extractors_label.setText(self.t("extractors"))
        self.extractors_edit.setPlaceholderText("token=token; id=features[0].attributes.OBJECTID")
        self._fill_call_combo()
        self._refresh_editor()

    def set_steps(self, steps: list[WorkflowStep]) -> None:
        """Load a list of workflow steps onto the canvas."""
        self._steps = steps[:]
        self._ensure_positions()
        self._rebuild_scene()

    def steps(self) -> list[WorkflowStep]:
        """Return the current steps, committing any pending editor changes."""
        self._commit_editor()
        return self._steps[:]

    def add_step(self, step: WorkflowStep | None = None) -> None:
        """Add a new step node to the canvas."""
        if not isinstance(step, WorkflowStep):
            step = WorkflowStep(
                name=f"{self.t('step')} {len(self._steps) + 1}",
                call_id=self.calls[0].id if self.calls else "",
            )
        self._steps.append(step)
        self._ensure_positions()
        self._rebuild_scene(select_index=len(self._steps) - 1)

    def remove_selected(self) -> None:
        """Remove the currently selected node from the canvas."""
        index = self._selected_index()
        if index is None:
            index = len(self._steps) - 1 if self._steps else None
        if index is None:
            return
        del self._steps[index]
        self._layout_steps()
        self._rebuild_scene(select_index=min(index, len(self._steps) - 1))

    def move_selected(self, direction: int) -> None:
        """Swap the selected node with its neighbor in the given direction."""
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
        """Update node status badges from a workflow run result."""
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
        """Redraw all bezier connections between nodes, with arrowheads."""
        for connection in self.connections:
            self.scene.removeItem(connection["item"])
            arrow = connection.get("arrow")
            if arrow is not None:
                self.scene.removeItem(arrow)
        self.connections.clear()

        default_color = QColor(PALETTE["cornflower_blue"] if self.dark_mode else PALETTE["vivid_blue"])
        highlight_color = QColor(PALETTE["amber"])
        default_pen = QPen(default_color, 2)
        highlight_pen = QPen(highlight_color, 4)

        for index, (left, right) in enumerate(zip(self.nodes, self.nodes[1:])):
            is_highlighted = self.drop_candidate == (index, index + 1)
            color = highlight_color if is_highlighted else default_color
            pen = highlight_pen if is_highlighted else default_pen

            start = left.pos() + QPointF(WorkflowCanvasNode.WIDTH, WorkflowCanvasNode.HEIGHT / 2)
            end = right.pos() + QPointF(0, WorkflowCanvasNode.HEIGHT / 2)
            distance = max(80, abs(end.x() - start.x()) / 2)
            path = QPainterPath(start)
            path.cubicTo(start + QPointF(distance, 0), end - QPointF(distance, 0), end)
            connection_item = QGraphicsPathItem(path)
            connection_item.setPen(pen)
            connection_item.setZValue(-1)
            self.scene.addItem(connection_item)

            # Arrowhead at the end of the connection
            arrow_item = self._create_arrowhead(start, end, color)
            self.scene.addItem(arrow_item)

            self.connections.append(
                {
                    "item": connection_item,
                    "arrow": arrow_item,
                    "left_index": index,
                    "right_index": index + 1,
                    "start": start,
                    "end": end,
                }
            )

    @staticmethod
    def _create_arrowhead(start: QPointF, end: QPointF, color: QColor) -> QGraphicsPolygonItem:
        """Create a small triangular arrowhead pointing into *end*."""
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.hypot(dx, dy)
        if length == 0:
            length = 1
        ux, uy = dx / length, dy / length
        px, py = -uy, ux  # perpendicular

        tip = end
        base_left = QPointF(
            tip.x() - ARROW_SIZE * ux + (ARROW_SIZE / 2.5) * px,
            tip.y() - ARROW_SIZE * uy + (ARROW_SIZE / 2.5) * py,
        )
        base_right = QPointF(
            tip.x() - ARROW_SIZE * ux - (ARROW_SIZE / 2.5) * px,
            tip.y() - ARROW_SIZE * uy - (ARROW_SIZE / 2.5) * py,
        )
        polygon = QPolygonF([tip, base_left, base_right])
        item = QGraphicsPolygonItem(polygon)
        item.setBrush(color)
        item.setPen(QPen(color, 1))
        item.setZValue(-1)
        return item

    def _fit_scene_rect(self) -> None:
        """Expand the scene rect to fit all nodes with generous padding."""
        if not self.nodes:
            self.view.setSceneRect(0, 0, 1100, 520)
            return
        items_rect = self.scene.itemsBoundingRect()
        padded = items_rect.adjusted(-100, -100, 200, 200)
        minimum = QRectF(0, 0, 1100, 520)
        self.view.setSceneRect(padded.united(minimum))

    def fit_all(self) -> None:
        """Reset zoom and pan so that all nodes are visible and centered."""
        self.view.resetTransform()
        self.view._zoom = 1.0
        if not self.nodes:
            return
        self._fit_scene_rect()
        rect = self.scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
        self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        # Update the internal zoom tracker to match the applied transform
        current_scale = self.view.transform().m11()
        self.view._zoom = max(ZOOM_MIN, min(ZOOM_MAX, current_scale))

    def update_drop_candidate(self, node: WorkflowCanvasNode) -> None:
        """Update the visual drop candidate indicator between two nodes."""
        if node not in self.nodes or len(self.nodes) < 3:
            self._set_drop_candidate(None)
            return

        node_index = self.nodes.index(node)
        node_center = node.pos() + QPointF(WorkflowCanvasNode.WIDTH / 2, WorkflowCanvasNode.HEIGHT / 2)
        best_pair: tuple[int, int] | None = None
        best_distance = 90.0

        for connection in self.connections:
            left_index = int(connection["left_index"])
            right_index = int(connection["right_index"])
            if node_index in {left_index, right_index}:
                continue

            distance = self._distance_to_segment(node_center, connection["start"], connection["end"])
            if distance < best_distance:
                best_pair = (left_index, right_index)
                best_distance = distance

        self._set_drop_candidate(best_pair)

    def commit_drop_candidate(self, node: WorkflowCanvasNode) -> None:
        """Commit the drop action, moving a node to a new position between two other nodes."""
        if self.drop_candidate is None or node not in self.nodes:
            self._set_drop_candidate(None)
            return

        old_index = self.nodes.index(node)
        left_index, _right_index = self.drop_candidate
        step = self._steps.pop(old_index)
        target_index = left_index + 1
        if old_index < target_index:
            target_index -= 1
        self._steps.insert(target_index, step)
        step.position_x = node.pos().x()
        step.position_y = node.pos().y()
        self.drop_candidate = None
        self._rebuild_scene(select_index=target_index)

    def _set_drop_candidate(self, candidate: tuple[int, int] | None) -> None:
        if candidate == self.drop_candidate:
            return
        self.drop_candidate = candidate
        self.refresh_connections()

    @staticmethod
    def _distance_to_segment(point: QPointF, start: QPointF, end: QPointF) -> float:
        """Calculate the minimum distance from a point to a line segment."""
        segment_x = end.x() - start.x()
        segment_y = end.y() - start.y()
        length_squared = (segment_x * segment_x) + (segment_y * segment_y)
        if length_squared == 0:
            return math.hypot(point.x() - start.x(), point.y() - start.y())

        projection = (
            ((point.x() - start.x()) * segment_x) + ((point.y() - start.y()) * segment_y)
        ) / length_squared
        projection = max(0.0, min(1.0, projection))
        closest = QPointF(start.x() + projection * segment_x, start.y() + projection * segment_y)
        return math.hypot(point.x() - closest.x(), point.y() - closest.y())

    def call_label(self, call_id: str) -> str:
        call = next((item for item in self.calls if item.id == call_id), None)
        if call is None:
            return "-"
        return f"{call.method} {call.name}"

    def _rebuild_scene(self, select_index: int | None = None) -> None:
        self.scene.clear()
        self.nodes.clear()
        self.connections.clear()
        self.drop_candidate = None
        self._apply_scene_colors()

        for index, step in enumerate(self._steps):
            node = WorkflowCanvasNode(self, step, index)
            node.setPos(float(step.position_x or 0), float(step.position_y or 0))
            self.scene.addItem(node)
            self.nodes.append(node)

        self.refresh_connections()
        self._fit_scene_rect()
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
        node.setToolTip(node._build_tooltip())
        node.update()

    def _commit_editor(self) -> None:
        node = self._selected_node()
        if node is None:
            return
        node.step.name = self.name_input.text().strip() or f"{self.t('step')} {node.index + 1}"
        node.step.call_id = str(self.call_combo.currentData() or "")
        node.step.extractors = parse_extractors(self.extractors_edit.toPlainText())
        node.setToolTip(node._build_tooltip())
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
        self.scene.setBackgroundBrush(QColor(PALETTE["near_black"] if self.dark_mode else PALETTE["snow_white"]))
