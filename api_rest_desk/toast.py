from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation, QTimer, Qt
from PyQt6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget


class ToastNotification(QLabel):
    """Small notification label that slides in from the top-right corner,
    stays visible briefly, and fades out automatically.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setProperty("toastKind", "info")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)
        self.setWindowFlags(Qt.WindowType.Widget)
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity_effect)
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._fade_out)
        self.animation: QParallelAnimationGroup | None = None
        self.hide()

    def show_message(self, text: str, kind: str = "info", duration_ms: int = 3200) -> None:
        """Display a toast message with the given *kind*
        (``"success"``, ``"warning"``, ``"error"``, or ``"info"``).

        The toast slides in, stays for *duration_ms* milliseconds,
        and then fades out.
        """
        self.hide_timer.stop()
        self._stop_animation()
        self.setText(text)
        self.setProperty("toastKind", kind)
        self.style().unpolish(self)
        self.style().polish(self)
        self.adjustSize()
        self.setFixedWidth(min(max(self.sizeHint().width(), 240), 420))
        self.adjustSize()
        final_pos = self._corner_position()
        self.move(final_pos + QPoint(0, -12))
        self.opacity_effect.setOpacity(0.0)
        self.show()
        self.raise_()
        self._animate(final_pos, 1.0, 180)
        self.hide_timer.start(duration_ms)

    def _corner_position(self) -> QPoint:
        parent = self.parentWidget()
        if parent is None:
            return self.pos()

        margin = 18
        x = max(margin, parent.width() - self.width() - margin)
        y = margin
        return QPoint(x, y)

    def _fade_out(self) -> None:
        self._stop_animation()
        self._animate(self.pos() + QPoint(0, -8), 0.0, 160, hide_when_done=True)

    def _animate(
        self,
        end_pos: QPoint,
        end_opacity: float,
        duration_ms: int,
        hide_when_done: bool = False,
    ) -> None:
        group = QParallelAnimationGroup(self)

        position_animation = QPropertyAnimation(self, b"pos", group)
        position_animation.setDuration(duration_ms)
        position_animation.setStartValue(self.pos())
        position_animation.setEndValue(end_pos)
        position_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity", group)
        opacity_animation.setDuration(duration_ms)
        opacity_animation.setStartValue(self.opacity_effect.opacity())
        opacity_animation.setEndValue(end_opacity)
        opacity_animation.setEasingCurve(QEasingCurve.Type.OutCubic)

        group.addAnimation(position_animation)
        group.addAnimation(opacity_animation)
        if hide_when_done:
            group.finished.connect(self.hide)

        self.animation = group
        group.start()

    def _stop_animation(self) -> None:
        if self.animation is not None:
            self.animation.stop()
            self.animation.deleteLater()
            self.animation = None
