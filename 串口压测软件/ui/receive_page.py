"""接收页：常开接收，记录解析成功/解析错误，并显示七路成功与总接收频率。"""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.contracts import ParseError, PortStats, SuccessEvent
from ui import theme


class ReceivePage(QWidget):
    config_changed = Signal()

    MODE_ALL = "all"        # 模式二：全部端口
    MODE_SINGLE = "single"  # 模式一：单端口

    def __init__(self, manager, config: dict, parent: QWidget | None = None):
        super().__init__(parent)
        self.manager = manager
        self.config = config
        self._pending: list[tuple[str, str]] = []
        self._history: list[tuple[str, str]] = []
        self._updating = False
        self._ok_labels: list[QLabel] = []
        self._total_labels: list[QLabel] = []
        self._error_labels: list[QLabel] = []

        self._flush_timer = QTimer(self)
        self._flush_timer.setInterval(100)
        self._flush_timer.timeout.connect(self._flush)
        self._flush_timer.start()

        self._timer_start = time.perf_counter()
        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(100)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()

        self._build_ui()
        self._connect_manager()
        self.apply_config()

    # ---- 构建 ------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("接收记录")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "已指定 COM 的端口常开接收；分别统计解析成功频率、总接收频率，解析错误也会打印"
        )
        subtitle.setObjectName("PageSubtitle")
        titles.addWidget(title)
        titles.addWidget(subtitle)
        header.addLayout(titles)
        header.addStretch(1)
        self.total_label = QLabel("成功 0.0 Hz / 总 0.0 Hz")
        self.total_label.setStyleSheet(
            f"color: {theme.ACCENT}; font-size: 15px; font-weight: 700;"
        )
        header.addWidget(self.total_label, 0, Qt.AlignmentFlag.AlignVCenter)
        self.error_rate_label = QLabel("错误率 0.000%")
        self.error_rate_label.setStyleSheet(
            f"color: {theme.MUTED}; font-size: 13px; font-weight: 600; padding-left: 12px;"
        )
        header.addWidget(self.error_rate_label, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(header)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)
        mode_label = QLabel("查看模式")
        mode_label.setStyleSheet(f"color: {theme.MUTED}; font-size: 11px;")
        mode_row.addWidget(mode_label)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.single_button = QPushButton("模式一 · 单端口")
        self.all_button = QPushButton("模式二 · 全部端口")
        for index, button in enumerate((self.single_button, self.all_button)):
            button.setObjectName("Segment")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.mode_group.addButton(button, index)
            mode_row.addWidget(button)
        self.mode_group.idClicked.connect(self._on_mode_clicked)

        self.port_combo = QComboBox()
        self.port_combo.setFixedWidth(120)
        for index in range(7):
            self.port_combo.addItem(f"端口 {index + 1}", index)
        self.port_combo.currentIndexChanged.connect(self._on_port_changed)
        mode_row.addWidget(self.port_combo)
        mode_row.addStretch(1)

        self.timer_label = QLabel("计时 00:00:00.000")
        self.timer_label.setStyleSheet(
            f"color: {theme.TEXT_SOFT}; font-family: '{theme.pick_mono_font()}', Consolas, monospace;"
            " font-size: 11px;"
        )
        mode_row.addWidget(self.timer_label)

        self.timer_reset_button = QPushButton("计时归零")
        self.timer_reset_button.setObjectName("Ghost")
        self.timer_reset_button.setFixedHeight(30)
        self.timer_reset_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.timer_reset_button.setToolTip("测试计时从 0 重新开始")
        self.timer_reset_button.clicked.connect(self._on_timer_reset)
        mode_row.addWidget(self.timer_reset_button)

        filter_label = QLabel("日志筛选")
        filter_label.setStyleSheet(f"color: {theme.MUTED}; font-size: 11px;")
        mode_row.addWidget(filter_label)

        self.success_filter = QCheckBox("成功")
        self.success_filter.setToolTip("显示解析成功记录")
        self.success_filter.setChecked(True)
        self.success_filter.toggled.connect(self._on_filter_changed)
        mode_row.addWidget(self.success_filter)

        self.error_filter = QCheckBox("错误")
        self.error_filter.setToolTip("显示解析错误记录")
        self.error_filter.setChecked(True)
        self.error_filter.toggled.connect(self._on_filter_changed)
        mode_row.addWidget(self.error_filter)

        self.clear_errors_button = QPushButton("错误清零")
        self.clear_errors_button.setObjectName("Ghost")
        self.clear_errors_button.setFixedHeight(30)
        self.clear_errors_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_errors_button.setToolTip("清零各路解析错误计数，并清空当前接收记录")
        self.clear_errors_button.clicked.connect(self._on_clear_errors)
        mode_row.addWidget(self.clear_errors_button)
        root.addLayout(mode_row)

        frequency_frame = QFrame()
        frequency_frame.setObjectName("Strip")
        frequency_layout = QHBoxLayout(frequency_frame)
        frequency_layout.setContentsMargins(14, 7, 14, 7)
        frequency_layout.setSpacing(8)
        for index in range(7):
            cell = QVBoxLayout()
            cell.setSpacing(0)
            name = QLabel(f"端口 {index + 1}")
            name.setStyleSheet(
                f"color: {theme.PORT_COLORS[index]}; font-size: 10px; font-weight: 600;"
            )
            ok = QLabel("成功 0.0 Hz")
            ok.setStyleSheet(f"color: {theme.MUTED}; font-size: 13px; font-weight: 700;")
            total = QLabel("总 0.0 Hz")
            total.setStyleSheet(f"color: {theme.MUTED}; font-size: 10.5px;")
            error = QLabel("错误 0 · 0.000%")
            error.setStyleSheet(f"color: {theme.MUTED}; font-size: 9.5px;")
            cell.addWidget(name)
            cell.addWidget(ok)
            cell.addWidget(total)
            cell.addWidget(error)
            frequency_layout.addLayout(cell, 1)
            self._ok_labels.append(ok)
            self._total_labels.append(total)
            self._error_labels.append(error)
            if index < 6:
                separator = QFrame()
                separator.setFixedWidth(1)
                separator.setStyleSheet(f"background: {theme.CARD_BORDER};")
                frequency_layout.addWidget(separator)
        root.addWidget(frequency_frame)

        self.log = QPlainTextEdit()
        self.log.setObjectName("LogView")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setPlaceholderText("等待接收…")
        root.addWidget(self.log, 1)

    # ---- manager ---------------------------------------------------------
    def _connect_manager(self) -> None:
        for name, slot in (
            ("receive_success", self._on_success),
            ("receive_error", self._on_error),
            ("stats_updated", self._on_stats),
        ):
            signal = getattr(self.manager, name, None)
            if signal is not None:
                signal.connect(slot)

    def _allowed(self, port_index: int) -> bool:
        receive = self.config.get("receive", {})
        if receive.get("mode") != self.MODE_SINGLE:
            return True
        return int(port_index) == int(receive.get("single_port", 0))

    def _device_text(self, port_index: int) -> str:
        ports = self.config.get("send", {}).get("ports", [])
        if 0 <= int(port_index) < len(ports):
            device = str(ports[int(port_index)].get("device") or "")
            return f"（{device}）" if device else ""
        return ""

    @staticmethod
    def _time_text(timestamp: float) -> str:
        stamp = time.localtime(timestamp)
        millis = int((timestamp % 1) * 1000)
        return f"[{time.strftime('%H:%M:%S', stamp)}.{millis:03d}]"

    def _kind_enabled(self, kind: str) -> bool:
        receive = self.config.get("receive", {})
        if kind == "success":
            return bool(receive.get("success_log", True))
        return bool(receive.get("error_log", True))

    def _record(self, kind: str, line: str) -> None:
        self._history.append((kind, line))
        if len(self._history) > 3000:
            del self._history[:-3000]
        if self._kind_enabled(kind):
            self._pending.append((kind, line))
            if len(self._pending) > 1000:
                del self._pending[:-1000]

    def _on_success(self, event: SuccessEvent) -> None:
        if not self._allowed(event.port_index):
            return
        line = (
            f"{self._time_text(event.timestamp)} "
            f"端口 {int(event.port_index) + 1}{self._device_text(event.port_index)} 解析成功"
        )
        self._record("success", line)

    def _on_error(self, event: ParseError) -> None:
        if not self._allowed(event.port_index):
            return
        line = (
            f"{self._time_text(event.timestamp)} "
            f"端口 {int(event.port_index) + 1}{self._device_text(event.port_index)} "
            f"解析错误：{event.reason}"
        )
        if event.detail:
            line += f"\n    原因：{event.detail}"
        if event.raw:
            line += f"\n    接收内容（{len(event.raw)} 字节）：{event.raw_hex}"
        self._record("error", line)

    def _flush(self) -> None:
        if not self._pending:
            return
        lines = [text for _kind, text in self._pending[:300]]
        del self._pending[:300]
        self.log.appendPlainText("\n".join(lines))
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _rebuild_log(self) -> None:
        self._flush()
        lines = [text for kind, text in self._history if self._kind_enabled(kind)]
        self.log.setPlainText("\n".join(lines))
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _clear_log(self) -> None:
        self._pending.clear()
        self._history.clear()
        self.log.clear()

    def _on_stats(self, stats) -> None:
        if not isinstance(stats, dict):
            return
        total_ok = 0.0
        total_all = 0.0
        total_errors = 0
        total_attempts = 0
        for index in range(7):
            stat = stats.get(index)
            ok_hz = float(getattr(stat, "rx_hz", 0.0) or 0.0)
            total_hz = float(getattr(stat, "rx_total_hz", 0.0) or 0.0)
            errors = int(getattr(stat, "parse_errors", 0) or 0)
            attempts = int(getattr(stat, "error_attempts", 0) or 0)
            rate = float(getattr(stat, "error_rate", 0.0) or 0.0)
            total_ok += ok_hz
            total_all += total_hz
            total_errors += errors
            total_attempts += attempts

            self._ok_labels[index].setText(f"成功 {ok_hz:.1f} Hz")
            self._ok_labels[index].setStyleSheet(
                f"color: {theme.ACCENT if ok_hz > 0 else theme.MUTED};"
                " font-size: 13px; font-weight: 700;"
            )
            self._total_labels[index].setText(f"总 {total_hz:.1f} Hz")
            self._total_labels[index].setStyleSheet(
                f"color: {theme.TEXT_SOFT if total_hz > 0 else theme.MUTED}; font-size: 10.5px;"
            )
            self._error_labels[index].setText(f"错误 {errors} · {rate:.3f}%")
            self._error_labels[index].setStyleSheet(
                f"color: {theme.RED if errors else theme.MUTED}; font-size: 9.5px;"
            )
            self._error_labels[index].setToolTip(
                f"解析错误 {errors} 次 / 接收尝试 {attempts} 次"
            )
        self.total_label.setText(f"成功 {total_ok:.1f} Hz / 总 {total_all:.1f} Hz")
        overall = (total_errors / total_attempts * 100.0) if total_attempts else 0.0
        self.error_rate_label.setText(f"错误率 {overall:.3f}%")
        self.error_rate_label.setStyleSheet(
            f"color: {theme.RED if total_errors else theme.MUTED};"
            " font-size: 13px; font-weight: 600; padding-left: 12px;"
        )
        self.error_rate_label.setToolTip(
            f"总解析错误 {total_errors} 次 / 总接收尝试 {total_attempts} 次"
        )

    def _update_clock(self) -> None:
        elapsed = max(0.0, time.perf_counter() - self._timer_start)
        hours = int(elapsed // 3600)
        minutes = int((elapsed % 3600) // 60)
        seconds = int(elapsed % 60)
        millis = int((elapsed % 1) * 1000)
        self.timer_label.setText(
            f"计时 {hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
        )

    def _on_timer_reset(self) -> None:
        self._timer_start = time.perf_counter()
        self._update_clock()

    def _on_clear_errors(self) -> None:
        reset = getattr(self.manager, "reset_errors", None)
        if callable(reset):
            reset()
        self._clear_log()
        self.log.setPlaceholderText("错误计数已清零，等待接收…")

    # ---- 模式 ------------------------------------------------------------
    def apply_config(self) -> None:
        receive = self.config.setdefault("receive", {})
        mode = receive.get("mode", self.MODE_ALL)
        port = max(0, min(6, int(receive.get("single_port", 0) or 0)))
        self._updating = True
        try:
            if mode == self.MODE_SINGLE:
                self.single_button.setChecked(True)
            else:
                self.all_button.setChecked(True)
            self.port_combo.setCurrentIndex(port)
            self.port_combo.setEnabled(mode == self.MODE_SINGLE)
            self.success_filter.setChecked(bool(receive.get("success_log", True)))
            self.error_filter.setChecked(bool(receive.get("error_log", True)))
        finally:
            self._updating = False

    def _on_filter_changed(self, _checked: bool) -> None:
        if self._updating:
            return
        self.config["receive"]["success_log"] = bool(self.success_filter.isChecked())
        self.config["receive"]["error_log"] = bool(self.error_filter.isChecked())
        self._rebuild_log()
        self.config_changed.emit()

    def _on_mode_clicked(self, index: int) -> None:
        mode = self.MODE_SINGLE if index == 0 else self.MODE_ALL
        self.config["receive"]["mode"] = mode
        self.port_combo.setEnabled(mode == self.MODE_SINGLE)
        self._clear_log()
        self.config_changed.emit()

    def _on_port_changed(self, index: int) -> None:
        if self._updating or index < 0:
            return
        self.config["receive"]["single_port"] = int(index)
        self._clear_log()
        self.config_changed.emit()
