"""程序图标与品牌元素（全部由 QPainter 生成，无需外部资源）。"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QLinearGradient, QPainter, QPen, QPixmap

from ui import theme


def make_logo_pixmap(size: int = 64) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    margin = max(1.0, size * 0.025)
    rect = QRectF(margin, margin, size - margin * 2, size - margin * 2)
    radius = size * 0.24
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor("#13263F"))
    gradient.setColorAt(1.0, QColor("#081220"))
    painter.setBrush(gradient)
    painter.setPen(QPen(QColor(theme.ACCENT), max(1.0, size * 0.028)))
    painter.drawRoundedRect(rect, radius, radius)

    # 三颗代表 SOF / LEN / CRC 的小圆点
    dot_radius = max(1.2, size * 0.026)
    dot_y = size * 0.285
    for index, color in enumerate((theme.ACCENT, theme.BLUE, theme.MUTED)):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawEllipse(
            QRectF(size * (0.30 + index * 0.14), dot_y, dot_radius * 2, dot_radius * 2)
        )

    font = QFont(theme.pick_mono_font(), int(size * 0.30))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(theme.TEXT))
    painter.drawText(
        QRectF(0, size * 0.36, size, size * 0.48),
        Qt.AlignmentFlag.AlignCenter,
        "A5",
    )
    painter.end()
    return pixmap


def make_app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(make_logo_pixmap(size))
    return icon
