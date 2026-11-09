"""主窗口：顶部标题 + 发送/接收两个标签页 + 外部配置自动保存。"""

from __future__ import annotations

import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.config_store import ConfigStore
from core.serial_manager import SerialManager
from ui import theme
from ui.branding import make_logo_pixmap
from ui.receive_page import ReceivePage
from ui.send_page import SendPage


class MainWindow(QMainWindow):
    def __init__(self, store: ConfigStore, parent: QWidget | None = None):
        super().__init__(parent)
        self.store = store
        self.config = store.data
        self.manager = SerialManager(parent=self)

        self.setWindowTitle("哨兵底盘 · 七路串口工具")
        self.setMinimumSize(980, 680)
        self.setWindowIcon(make_logo_pixmap(64))

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(500)
        self._save_timer.timeout.connect(self._save_now)

        self._build_ui()
        self._restore_geometry()

        QTimer.singleShot(200, self._restore_runtime)

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 16, 22, 10)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(make_logo_pixmap(40))
        logo.setFixedSize(40, 40)
        header.addWidget(logo)

        titles = QVBoxLayout()
        titles.setSpacing(1)
        title = QLabel("哨兵底盘 · 七路串口工具")
        title.setStyleSheet(f"color: {theme.TEXT}; font-size: 19px; font-weight: 700;")
        subtitle = QLabel("串口发送与接收记录 · 协议帧 22 字节")
        subtitle.setStyleSheet(f"color: {theme.MUTED}; font-size: 10.5px;")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch(1)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("MainTabs")
        self.send_page = SendPage(self.manager, self.config)
        self.receive_page = ReceivePage(self.manager, self.config)
        self.tabs.addTab(self.send_page, "发送")
        self.tabs.addTab(self.receive_page, "接收记录")
        layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(2, 0, 2, 0)
        self.config_label = QLabel(f"配置文件：{self.store.path}")
        self.config_label.setStyleSheet(f"color: {theme.MUTED}; font-size: 10px;")
        self.config_label.setToolTip(str(self.store.path))
        footer.addWidget(self.config_label)
        footer.addStretch(1)
        self.save_label = QLabel("配置已载入")
        self.save_label.setStyleSheet(f"color: {theme.MUTED}; font-size: 10px;")
        footer.addWidget(self.save_label)
        layout.addLayout(footer)

        self.setCentralWidget(root)
        self.send_page.config_changed.connect(self._mark_dirty)
        self.receive_page.config_changed.connect(self._mark_dirty)
        self.tabs.currentChanged.connect(lambda _index: self._save_now())

    # ---- 保存 ------------------------------------------------------------
    def _mark_dirty(self) -> None:
        self.save_label.setText("保存中…")
        self.save_label.setStyleSheet(f"color: {theme.AMBER}; font-size: 10px;")
        self._save_timer.start()

    def _save_now(self) -> None:
        self._save_timer.stop()
        try:
            self.store.save()
        except Exception as exc:
            self.save_label.setText(f"保存失败：{exc}")
            self.save_label.setStyleSheet(f"color: {theme.RED}; font-size: 10px;")
            return
        self.save_label.setText(f"已保存 {time.strftime('%H:%M:%S')}")
        self.save_label.setStyleSheet(f"color: {theme.MUTED}; font-size: 10px;")

    def _restore_runtime(self) -> None:
        if self.store.load_error:
            self.save_label.setText("配置损坏，已使用默认值")
            self.save_label.setStyleSheet(f"color: {theme.AMBER}; font-size: 10px;")
            self.save_label.setToolTip(self.store.load_error)
        self.send_page.restore_running_ports()

    # ---- 窗口 ------------------------------------------------------------
    def _restore_geometry(self) -> None:
        window = self.config.get("window", {})
        width = int(window.get("width", 1180))
        height = int(window.get("height", 780))
        self.resize(width, height)
        x, y = window.get("x"), window.get("y")
        if x is not None and y is not None:
            self.move(int(x), int(y))

    def _persist_geometry(self) -> None:
        window = self.config.setdefault("window", {})
        window["maximized"] = self.isMaximized()
        if not self.isMaximized():
            window["width"] = self.width()
            window["height"] = self.height()
            window["x"] = self.x()
            window["y"] = self.y()

    def closeEvent(self, event) -> None:  # noqa: N802
        self._persist_geometry()
        self._save_now()
        self.manager.shutdown()
        super().closeEvent(event)
