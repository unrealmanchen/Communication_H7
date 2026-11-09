"""界面通用小控件：自绘开关、状态灯、端口编号徽标。"""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton, QLabel, QWidget

from ui import theme


class ToggleSwitch(QAbstractButton):
    """自绘拨动开关；``setChecked`` 不触发 toggled，用户点击才触发。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(46, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._offset = 0.0
        self._animation = QPropertyAnimation(self, b"offset", self)
        self._animation.setDuration(160)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)

    def _get_offset(self) -> float:
        return self._offset

    def _set_offset(self, value: float) -> None:
        self._offset = float(value)
        self.update()

    offset = Property(float, _get_offset, _set_offset)

    def _animate(self, checked: bool) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._offset)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def setChecked(self, checked: bool) -> None:  # noqa: N802 (Qt API)
        blocked = self.blockSignals(True)
        super().setChecked(checked)
        self.blockSignals(blocked)
        self._animation.stop()
        self._offset = 1.0 if checked else 0.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        track = QRectF(1.0, 3.0, width - 2.0, height - 6.0)
        radius = track.height() / 2.0

        if not self.isEnabled():
            track_color = QColor("#1A273B")
            knob_color = QColor("#41526B")
        elif self.isChecked():
            track_color = QColor(theme.ACCENT)
            knob_color = QColor("#F4FFFC")
        else:
            track_color = QColor("#26374F")
            knob_color = QColor("#C4D2E6")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(track, radius, radius)

        knob_radius = 9.0
        knob_x = 4.0 + self._offset * (width - 8.0 - knob_radius * 2.0)
        painter.setBrush(knob_color)
        painter.drawEllipse(
            QRectF(knob_x, (height - knob_radius * 2) / 2.0, knob_radius * 2, knob_radius * 2)
        )


class StatusDot(QWidget):
    COLORS = {
        "idle": "#3D4F69",
        "opening": theme.AMBER,
        "connected": theme.BLUE,
        "running": theme.GREEN,
        "error": theme.RED,
    }

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._state = "idle"
        self.setFixedSize(12, 12)

    def set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.COLORS.get(self._state, "#3D4F69")))
        painter.drawEllipse(QRectF(3, 3, 6, 6))


class PortBadge(QLabel):
    def __init__(self, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(28, 28)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color = theme.PORT_COLORS[index % len(theme.PORT_COLORS)]
        self.setText(f"{index + 1:02d}")
        self.setStyleSheet(
            f"background: {theme.rgba(color, 0.14)};"
            f"color: {color};"
            f"border: 1px solid {theme.rgba(color, 0.34)};"
            "border-radius: 8px;"
            "font-family: 'Consolas', monospace;"
            "font-size: 11px;"
            "font-weight: 700;"
        )
