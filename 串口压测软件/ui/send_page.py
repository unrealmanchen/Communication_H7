"""发送页：7 路串口，每路独立选择端口/波特率/发送速率与开关。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.config_store import BAUD_CHOICES, DEFAULT_BAUD, DEFAULT_RATE
from core.contracts import PortStats
from ui import theme
from ui.widgets import PortBadge, StatusDot, ToggleSwitch

NAME_WIDTH = 92
BAUD_WIDTH = 110
RATE_WIDTH = 120
STATUS_WIDTH = 140
TOGGLE_WIDTH = 46


class _PortRow(QFrame):
    edited = Signal(int)
    toggle_requested = Signal(int, bool)

    def __init__(self, index: int, port: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.index = index
        self.port = port
        self._updating = False
        self.setMinimumHeight(62)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(8)
        self.badge = PortBadge(index)
        self.name_label = QLabel(f"端口 {index + 1}")
        self.name_label.setStyleSheet(f"color: {theme.TEXT}; font-size: 12px; font-weight: 600;")
        name_row.addWidget(self.badge)
        name_row.addWidget(self.name_label)
        name_holder = QWidget()
        name_holder.setLayout(name_row)
        name_holder.setFixedWidth(NAME_WIDTH)
        layout.addWidget(name_holder)

        self.device_combo = QComboBox()
        self.device_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.device_combo.setMinimumContentsLength(10)
        self.device_combo.setMinimumWidth(160)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        layout.addWidget(self.device_combo, 1)

        self.baud_combo = QComboBox()
        self.baud_combo.setFixedWidth(BAUD_WIDTH)
        for baud in BAUD_CHOICES:
            self.baud_combo.addItem(str(baud), baud)
        self.baud_combo.currentIndexChanged.connect(self._on_baud_changed)
        layout.addWidget(self.baud_combo)

        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setFixedWidth(RATE_WIDTH)
        self.rate_spin.setRange(0.1, 1000.0)
        self.rate_spin.setDecimals(1)
        self.rate_spin.setSingleStep(1.0)
        self.rate_spin.setSuffix(" Hz")
        self.rate_spin.setKeyboardTracking(False)
        self.rate_spin.valueChanged.connect(self._on_rate_changed)
        layout.addWidget(self.rate_spin)

        self.status_dot = StatusDot()
        self.status_label = QLabel("未开启")
        self.status_label.setFixedWidth(STATUS_WIDTH - 20)
        self.status_label.setStyleSheet(f"color: {theme.MUTED}; font-size: 11px;")
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(4)
        status_row.addWidget(self.status_dot)
        status_row.addWidget(self.status_label, 1)
        status_holder = QWidget()
        status_holder.setLayout(status_row)
        status_holder.setFixedWidth(STATUS_WIDTH)
        layout.addWidget(status_holder)

        self.toggle = ToggleSwitch()
        self.toggle.setFixedWidth(TOGGLE_WIDTH)
        self.toggle.setToolTip(f"端口 {index + 1} 发送开关")
        self.toggle.toggled.connect(self._on_toggle)
        layout.addWidget(self.toggle, 0, Qt.AlignmentFlag.AlignVCenter)

        self._state = "idle"
        self._tx_hz = 0.0
        self._load_values()

    # ---- 配置 ------------------------------------------------------------
    def _load_values(self) -> None:
        self._updating = True
        try:
            device = str(self.port.get("device") or "")
            index = self.device_combo.findData(device)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)
            try:
                baud = int(self.port.get("baud") or DEFAULT_BAUD)
            except (TypeError, ValueError):
                baud = DEFAULT_BAUD
            baud_index = self.baud_combo.findData(baud)
            if baud_index < 0:
                self.baud_combo.addItem(str(baud), baud)
                baud_index = self.baud_combo.findData(baud)
            self.baud_combo.setCurrentIndex(max(0, baud_index))
            try:
                rate = float(self.port.get("rate_hz") or DEFAULT_RATE)
            except (TypeError, ValueError):
                rate = DEFAULT_RATE
            self.rate_spin.setValue(max(0.1, min(1000.0, rate)))
            self.toggle.setChecked(bool(self.port.get("enabled")))
            self.set_state("idle", "未开启")
        finally:
            self._updating = False

    def refresh_ports(self, ports) -> None:
        current = str(self.port.get("device") or "")
        self._updating = True
        try:
            self.device_combo.clear()
            self.device_combo.addItem("请选择串口", "")
            for info in ports:
                if getattr(info, "is_virtual", False):
                    continue
                device = str(getattr(info, "device", "") or "")
                if not device:
                    continue
                label = str(getattr(info, "label", device) or device)
                self.device_combo.addItem(label, device)
            index = self.device_combo.findData(current)
            if index < 0 and current:
                self.device_combo.addItem(f"{current}（未检测到）", current)
                index = self.device_combo.findData(current)
            self.device_combo.setCurrentIndex(max(0, index))
        finally:
            self._updating = False

    # ---- 状态 ------------------------------------------------------------
    def set_state(self, state: str, message: str = "") -> None:
        self._state = state
        self.status_dot.set_state(state)
        colors = {
            "idle": theme.MUTED,
            "opening": theme.AMBER,
            "connected": theme.BLUE,
            "running": theme.GREEN,
            "error": theme.RED,
        }
        labels = {
            "idle": "未开启",
            "opening": "打开中",
            "connected": "已连接",
            "running": "发送中",
            "error": "异常",
        }
        text = labels.get(state, state)
        if state == "running" and self._tx_hz > 0:
            text = f"发送中 {self._tx_hz:.1f} Hz"
        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"color: {colors.get(state, theme.MUTED)}; font-size: 11px;"
        )
        self.setToolTip(message or labels.get(state, ""))

    def update_tx_hz(self, tx_hz: float) -> None:
        self._tx_hz = max(0.0, float(tx_hz))
        if self._state == "running":
            self.set_state("running")

    def set_checked(self, checked: bool) -> None:
        self.toggle.setChecked(checked)

    # ---- 交互 ------------------------------------------------------------
    def _on_device_changed(self, _index: int) -> None:
        if self._updating:
            return
        self.port["device"] = str(self.device_combo.currentData() or "")
        self.edited.emit(self.index)

    def _on_baud_changed(self, _index: int) -> None:
        if self._updating:
            return
        try:
            self.port["baud"] = int(self.baud_combo.currentData())
        except (TypeError, ValueError):
            self.port["baud"] = DEFAULT_BAUD
        self.edited.emit(self.index)

    def _on_rate_changed(self, value: float) -> None:
        if self._updating:
            return
        self.port["rate_hz"] = round(float(value), 2)
        self.edited.emit(self.index)

    def _on_toggle(self, checked: bool) -> None:
        if self._updating:
            return
        self.port["enabled"] = bool(checked)
        self.toggle_requested.emit(self.index, bool(checked))


class SendPage(QWidget):
    config_changed = Signal()

    def __init__(self, manager, config: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.manager = manager
        self.config = config
        self._rows: list[_PortRow] = []

        self._build_ui()
        self._connect_manager()
        self._refresh_ports()

    # ---- 构建 ------------------------------------------------------------
    def _build_ui(self) -> None:
        ports = self.config.setdefault("send", {}).setdefault("ports", [])
        while len(ports) < 7:
            index = len(ports)
            ports.append(
                {
                    "name": f"端口 {index + 1}",
                    "device": "",
                    "baud": DEFAULT_BAUD,
                    "rate_hz": DEFAULT_RATE,
                    "enabled": False,
                }
            )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("串口发送")
        title.setObjectName("PageTitle")
        subtitle = QLabel("发送内容：0x402 底盘速度指令 · 22 字节协议帧（CRC8 + CRC16），七路独立发送")
        subtitle.setObjectName("PageSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch(1)

        refresh_button = QPushButton("刷新串口")
        refresh_button.setObjectName("Ghost")
        refresh_button.setFixedHeight(34)
        refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_button.clicked.connect(self._refresh_ports)
        header.addWidget(refresh_button)

        self.start_all_button = QPushButton("一键开启")
        self.start_all_button.setObjectName("Primary")
        self.start_all_button.setFixedHeight(34)
        self.start_all_button.setMinimumWidth(96)
        self.start_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_all_button.clicked.connect(lambda: self.set_all_enabled(True))
        header.addWidget(self.start_all_button)

        self.stop_all_button = QPushButton("一键关闭")
        self.stop_all_button.setObjectName("Danger")
        self.stop_all_button.setFixedHeight(34)
        self.stop_all_button.setMinimumWidth(96)
        self.stop_all_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_all_button.clicked.connect(lambda: self.set_all_enabled(False))
        header.addWidget(self.stop_all_button)
        root.addLayout(header)

        column_header = QFrame()
        column_header.setObjectName("Strip")
        column_layout = QHBoxLayout(column_header)
        column_layout.setContentsMargins(12, 5, 12, 5)
        column_layout.setSpacing(10)
        for text, width in (
            ("端口", NAME_WIDTH),
            ("串口", 0),
            ("波特率", BAUD_WIDTH),
            ("发送速率", RATE_WIDTH),
            ("状态", STATUS_WIDTH),
            ("开关", TOGGLE_WIDTH),
        ):
            label = QLabel(text)
            label.setStyleSheet(f"color: {theme.MUTED}; font-size: 10.5px;")
            if width:
                label.setFixedWidth(width)
            column_layout.addWidget(label, 1 if width == 0 else 0)
        root.addWidget(column_header)

        rows_host = QVBoxLayout()
        rows_host.setSpacing(8)
        for index in range(7):
            row = _PortRow(index, ports[index], self)
            row.edited.connect(self._on_row_edited)
            row.toggle_requested.connect(self._on_toggle_requested)
            self._rows.append(row)
            rows_host.addWidget(row, 1)
        rows_host.addStretch(0)
        root.addLayout(rows_host, 1)

    # ---- manager ---------------------------------------------------------
    def _connect_manager(self) -> None:
        for name, slot in (
            ("port_state_changed", self._on_port_state),
            ("stats_updated", self._on_stats),
            ("ports_refreshed", self._on_ports_refreshed),
        ):
            signal = getattr(self.manager, name, None)
            if signal is not None:
                signal.connect(slot)

    def _refresh_ports(self) -> None:
        try:
            ports = self.manager.available_ports()
        except Exception:
            ports = []
        for row in self._rows:
            row.refresh_ports(ports)

    def _on_ports_refreshed(self, ports) -> None:
        for row in self._rows:
            row.refresh_ports(ports)

    def _apply_all(self, emit: bool) -> None:
        try:
            self.manager.apply_config(self.config["send"]["ports"])
        except Exception:
            pass
        if emit:
            self.config_changed.emit()

    def _on_row_edited(self, _index: int) -> None:
        self._apply_all(emit=True)

    def _on_toggle_requested(self, index: int, enabled: bool) -> None:
        self._apply_all(emit=False)
        try:
            self.manager.set_enabled(index, enabled)
        except Exception:
            pass
        row = self._rows[index]
        if enabled:
            row.set_state("opening")
        else:
            try:
                connected = self.manager.is_running(index)
            except Exception:
                connected = False
            row.set_state("connected" if connected else "idle")
        self.config_changed.emit()

    def _on_port_state(self, index: int, state: str, message: str) -> None:
        if not 0 <= int(index) < len(self._rows):
            return
        row = self._rows[int(index)]
        row.set_state(str(state), str(message or ""))
        if state == "error":
            row.set_checked(False)
            self.config["send"]["ports"][int(index)]["enabled"] = False
            self.config_changed.emit()
        elif state == "running":
            enabled = bool(self.config["send"]["ports"][int(index)].get("enabled"))
            row.set_checked(enabled)
            row.set_state("running" if enabled else "connected")
        elif state == "idle":
            row.set_checked(False)

    def _on_stats(self, stats) -> None:
        if not isinstance(stats, dict):
            return
        for index, row in enumerate(self._rows):
            stat = stats.get(index)
            if not isinstance(stat, PortStats):
                continue
            row.update_tx_hz(stat.tx_hz)
            if stat.running:
                enabled = bool(self.config["send"]["ports"][index].get("enabled"))
                row.set_state("running" if enabled else "connected")

    # ---- 对外 ------------------------------------------------------------
    def set_all_enabled(self, enabled: bool) -> None:
        enabled = bool(enabled)
        for index, row in enumerate(self._rows):
            self.config["send"]["ports"][index]["enabled"] = enabled
            row.set_checked(enabled)
            if enabled:
                row.set_state("opening")
            else:
                try:
                    connected = self.manager.is_running(index)
                except Exception:
                    connected = False
                row.set_state("connected" if connected else "idle")
        self._apply_all(emit=False)
        try:
            if enabled:
                self.manager.enable_all()
            else:
                self.manager.disable_all()
        except Exception:
            pass
        self.config_changed.emit()

    def restore_running_ports(self) -> None:
        self._apply_all(emit=False)
        for index, row in enumerate(self._rows):
            enabled = bool(self.config["send"]["ports"][index].get("enabled"))
            row.set_checked(enabled)
            if enabled:
                try:
                    self.manager.set_enabled(index, True)
                except Exception:
                    pass
