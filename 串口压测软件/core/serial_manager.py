"""七路串口引擎：常开接收、完整帧校验、发送开关与频率统计。"""

from __future__ import annotations

import copy
import threading
import time
from collections import deque
from dataclasses import replace
from typing import Any

from PySide6.QtCore import QCoreApplication, QObject, QTimer, Signal

try:  # pyserial 缺失时仍可使用虚拟端口/测试
    import serial
    from serial.tools import list_ports as _list_ports
except Exception:  # pragma: no cover
    serial = None  # type: ignore[assignment]
    _list_ports = None  # type: ignore[assignment]

from core.config_store import PORT_COUNT, default_config
from core.contracts import ParseError, PortInfo, PortStats, SuccessEvent
from core.protocol import Frame, build_command_frame, crc8, crc16, default_params, verify_frame
from core.virtual_device import VirtualChassisDevice

SOF = 0xA5
HEADER_LEN = 5
MAX_DATA_LEN = 2048
STATS_INTERVAL_MS = 200
RATE_WINDOW = 2.0
JOIN_TIMEOUT = 3.0
VIRTUAL_PREFIX = "VIRTUAL:"


class FrameParser:
    """把字节流解析为完整帧，并区分“总接收”和“解析成功”。

    * 帧头（A5 + 长度 + 0x00 + CRC8）正确才计入总接收帧；
    * 数据收全且 CRC16 正确才算解析成功；
    * 帧头 CRC8 错误、长度非法、CRC16 错误都返回错误记录，交给界面打印。
    """

    def __init__(self) -> None:
        self.buffer = bytearray()

    def reset(self) -> None:
        self.buffer.clear()

    def feed(
        self, data: bytes | bytearray
    ) -> tuple[list[bytes], list[Frame], list[tuple[str, bytes, str]]]:
        if data:
            self.buffer.extend(data)
        headers: list[bytes] = []
        frames: list[Frame] = []
        errors: list[tuple[str, bytes, str]] = []

        while True:
            if not self.buffer:
                break

            if self.buffer[0] != SOF:
                pos = self.buffer.find(SOF)
                if pos < 0:
                    self.buffer.clear()
                    break
                del self.buffer[:pos]
                continue

            if len(self.buffer) < HEADER_LEN:
                break

            if self.buffer[3] != 0x00 or crc8(self.buffer[:4]) != self.buffer[4]:
                header = bytes(self.buffer[:5])
                expected = crc8(header[:4])
                actual = header[4]
                data_len = header[1] | (header[2] << 8)
                detail = (
                    f"帧头={header.hex(' ')}；长度字段={data_len}；"
                    f"CRC8 期望 0x{expected:02X}，实际 0x{actual:02X}"
                )
                errors.append(
                    ("帧头 CRC8 校验失败", bytes(self.buffer[: min(len(self.buffer), 256)]), detail)
                )
                del self.buffer[0]
                continue

            header = bytes(self.buffer[:HEADER_LEN])
            data_len = header[1] | (header[2] << 8)
            if data_len > MAX_DATA_LEN:
                detail = (
                    f"帧头={header.hex(' ')}；长度字段={data_len}，"
                    f"超过最大值 {MAX_DATA_LEN}"
                )
                errors.append(
                    (
                        f"数据长度非法（{data_len}）",
                        bytes(self.buffer[: min(len(self.buffer), 256)]),
                        detail,
                    )
                )
                del self.buffer[:HEADER_LEN]
                continue

            total = HEADER_LEN + 2 + data_len + 2
            if len(self.buffer) < total:
                break

            raw = bytes(self.buffer[:total])
            headers.append(header)
            cmd_id = raw[5] | (raw[6] << 8)
            payload = raw[7 : 7 + data_len]
            valid = verify_frame(raw)
            frames.append(Frame(cmd_id=cmd_id, data=payload, raw=raw, valid=valid))
            if not valid:
                expected = crc16(raw[:-2])
                actual = raw[-2] | (raw[-1] << 8)
                detail = (
                    f"帧长={total}；cmd=0x{cmd_id:04X}；"
                    f"CRC16 期望 0x{expected:04X}，实际 0x{actual:04X}"
                )
                errors.append(("CRC16 校验失败", raw, detail))
            del self.buffer[:total]

        if len(self.buffer) > 1_000_000:
            del self.buffer[:-8192]
        return headers, frames, errors


class _PortFailure(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _open_error_message(device: str, exc: BaseException) -> str:
    text = str(exc) or exc.__class__.__name__
    lower = text.lower()
    if (
        isinstance(exc, PermissionError)
        or "permission" in lower
        or "access is denied" in lower
        or "拒绝访问" in text
    ):
        return f"串口 {device} 被占用或无访问权限（请关闭占用该串口的程序）"
    if (
        isinstance(exc, FileNotFoundError)
        or "could not open port" in lower
        or "file not found" in lower
        or "找不到" in text
    ):
        return f"串口 {device} 不存在或已被拔出"
    return f"串口 {device} 打开失败：{text}"


class _PortWorker:
    """一路端口：串口常开接收；开关打开时按 rate_hz 周期发送。"""

    def __init__(self, manager: "SerialManager", index: int) -> None:
        self.manager = manager
        self.index = index
        self._stop = threading.Event()
        self._force = threading.Event()
        self._serial = None
        self._thread = threading.Thread(
            target=self._run,
            name=f"serial-port-{index + 1}",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self, timeout: float = JOIN_TIMEOUT) -> bool:
        self._stop.set()
        self._thread.join(timeout)
        if self._thread.is_alive():
            self._close_serial()
            self._thread.join(0.5)
        return not self._thread.is_alive()

    @property
    def alive(self) -> bool:
        return self._thread.is_alive()

    def force_send(self) -> None:
        self._force.set()

    def _close_serial(self) -> None:
        ser, self._serial = self._serial, None
        if ser is not None:
            try:
                ser.close()
            except Exception:
                pass

    def _run(self) -> None:
        try:
            cfg = self.manager._copy_config(self.index)
            device = str(cfg.get("device") or "")
            if device.upper().startswith(VIRTUAL_PREFIX):
                self._run_virtual(cfg)
            else:
                self._run_serial(cfg)
        except _PortFailure as exc:
            if not self._stop.is_set():
                self.manager._set_state(self.index, "error", exc.message)
        except Exception as exc:  # 单路线程异常不影响进程
            if not self._stop.is_set():
                self.manager._set_state(self.index, "error", f"端口线程异常：{exc}")
        finally:
            self._close_serial()

    # ---- 真实串口 --------------------------------------------------------
    def _run_serial(self, cfg: dict[str, Any]) -> None:
        device = str(cfg.get("device") or "")
        baud = int(cfg.get("baud") or 115200)
        if serial is None:
            raise _PortFailure("未安装 pyserial，无法打开真实串口")
        self.manager._set_state(self.index, "opening", f"正在打开 {device} @ {baud}")
        try:
            # timeout=0：非阻塞读，避免 USB 转串口驱动在反复重配 timeout 时丢数据
            ser = serial.Serial(port=device, baudrate=baud, timeout=0, write_timeout=0.5)
        except Exception as exc:
            raise _PortFailure(_open_error_message(device, exc)) from exc

        if self._stop.is_set():
            try:
                ser.close()
            except Exception:
                pass
            return
        self._serial = ser
        try:
            try:
                ser.reset_input_buffer()
            except Exception:
                pass
            self.manager._set_state(self.index, "running", f"{device} @ {baud}")
            self._loop_serial(ser, device)
        finally:
            self._close_serial()

    def _loop_serial(self, ser: Any, device: str) -> None:
        parser = FrameParser()
        next_tx = time.perf_counter()
        last_period: float | None = None

        while not self._stop.is_set():
            cfg = self.manager._copy_config(self.index)
            enabled = bool(cfg.get("enabled"))
            rate = max(0.1, float(cfg.get("rate_hz") or 100.0))
            period = 1.0 / rate
            now = time.perf_counter()

            if enabled:
                if last_period is None or abs(period - last_period) > 1e-9:
                    next_tx = now
                    last_period = period
                if self._force.is_set():
                    self._force.clear()
                    self._write_frame(ser, cfg)
                    next_tx = now + period
                elif now >= next_tx:
                    self._write_frame(ser, cfg)
                    next_tx += period
                    if next_tx < now:
                        next_tx = now + period
            else:
                last_period = None

            try:
                chunk = ser.read(1)
                waiting = ser.in_waiting
                if waiting:
                    chunk += ser.read(waiting)
            except Exception as exc:
                raise _PortFailure(
                    f"串口 {device} 连接中断（设备可能已被拔出）：{exc}"
                ) from exc
            if chunk:
                self.manager._handle_rx(self.index, chunk, parser)

            if enabled:
                delay = next_tx - time.perf_counter()
                time.sleep(min(max(delay, 0.0005), 0.002))
            else:
                time.sleep(0.002)

    def _write_frame(self, ser: Any, cfg: dict[str, Any]) -> None:
        payload = build_command_frame(0x402, cfg.get("params") or {})
        try:
            written = ser.write(payload)
        except Exception as exc:
            raise _PortFailure(
                f"串口 {cfg.get('device')} 发送失败（设备可能已被拔出）：{exc}"
            ) from exc
        self.manager._note_tx(self.index, int(written) if written else len(payload))

    # ---- 虚拟端口（测试用） ---------------------------------------------
    def _run_virtual(self, cfg: dict[str, Any]) -> None:
        device = str(cfg.get("device") or VIRTUAL_PREFIX + str(self.index + 1))
        self.manager._set_state(self.index, "opening", f"正在打开虚拟端口 {device}")
        sim = VirtualChassisDevice(self.index, float(self.manager.reply_rate_hz))
        self.manager._set_state(self.index, "running", f"{device} · 模拟设备")
        parser = FrameParser()
        next_tx = time.perf_counter()
        last_period: float | None = None

        while not self._stop.is_set():
            now = time.perf_counter()
            try:
                sim.set_reply_rate(float(self.manager.reply_rate_hz), now)
            except Exception:
                pass
            for raw in sim.due_payloads(now):
                self.manager._handle_rx(self.index, raw, parser)

            cfg = self.manager._copy_config(self.index)
            enabled = bool(cfg.get("enabled"))
            period = 1.0 / max(0.1, float(cfg.get("rate_hz") or 100.0))
            if enabled:
                if last_period is None or abs(period - last_period) > 1e-9:
                    next_tx = now
                    last_period = period
                if self._force.is_set():
                    self._force.clear()
                    self.manager._note_tx(self.index, 22)
                    next_tx = now + period
                elif now >= next_tx:
                    self.manager._note_tx(self.index, 22)
                    next_tx += period
                    if next_tx < now:
                        next_tx = now + period
            else:
                last_period = None

            wake_at = sim.next_due_at
            if enabled:
                wake_at = min(wake_at, next_tx)
            delay = wake_at - time.perf_counter()
            time.sleep(min(max(delay, 0.0005), 0.02))


class SerialManager(QObject):
    """七路串口管理器。"""

    stats_updated = Signal(object)
    port_state_changed = Signal(int, str, str)
    ports_refreshed = Signal(object)
    receive_success = Signal(object)  # SuccessEvent
    receive_error = Signal(object)    # ParseError

    def __init__(self, reply_rate_hz: float = 20.0, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.reply_rate_hz = float(reply_rate_hz)

        self._lock = threading.RLock()
        self._control_lock = threading.RLock()
        self._closed = False

        self._configs: list[dict[str, Any]] = []
        for port in copy.deepcopy(default_config()["send"]["ports"]):
            port["command"] = 0x402
            port["params"] = default_params(0x402)
            self._configs.append(port)
        self._stats: dict[int, PortStats] = {
            index: PortStats(index=index) for index in range(PORT_COUNT)
        }
        for index, cfg in enumerate(self._configs):
            self._stats[index].device = str(cfg.get("device") or "")
            self._stats[index].baud = int(cfg.get("baud") or 115200)

        self._rx_times: dict[int, deque[float]] = {
            index: deque(maxlen=4096) for index in range(PORT_COUNT)
        }
        self._rx_total_times: dict[int, deque[float]] = {
            index: deque(maxlen=4096) for index in range(PORT_COUNT)
        }
        self._tx_times: dict[int, deque[float]] = {
            index: deque(maxlen=4096) for index in range(PORT_COUNT)
        }
        self._workers: dict[int, _PortWorker] = {}

        self._timer = QTimer(self)
        self._timer.setInterval(STATS_INTERVAL_MS)
        self._timer.timeout.connect(self._broadcast_stats)
        self._ensure_timer()

    # ---- 串口枚举 --------------------------------------------------------
    def available_ports(self) -> list[PortInfo]:
        result: list[PortInfo] = []
        if _list_ports is not None:
            try:
                for info in _list_ports.comports():
                    description = (info.description or "").strip()
                    label = f"{info.device} · {description}" if description else info.device
                    result.append(PortInfo(device=info.device, label=label, is_virtual=False))
            except Exception:
                pass
        for index in range(PORT_COUNT):
            device = f"{VIRTUAL_PREFIX}{index + 1}"
            result.append(
                PortInfo(device=device, label=f"虚拟端口 {index + 1} · 模拟设备", is_virtual=True)
            )
        return result

    def refresh_ports(self) -> list[PortInfo]:
        ports = self.available_ports()
        self.ports_refreshed.emit(ports)
        return ports

    # ---- 配置 / 开关 -----------------------------------------------------
    def apply_config(self, ports: list[dict]) -> None:
        """应用 7 路配置：配置了 COM 就常开接收；开关只控制发送。"""
        if self._closed:
            return
        ports = list(ports or [])
        with self._control_lock:
            with self._lock:
                old_cfgs = copy.deepcopy(self._configs)
            new_cfgs = [
                self._merge_config(index, ports[index] if index < len(ports) else None)
                for index in range(PORT_COUNT)
            ]
            with self._lock:
                self._configs = new_cfgs
                for index in range(PORT_COUNT):
                    self._stats[index].device = str(new_cfgs[index].get("device") or "")
                    self._stats[index].baud = int(new_cfgs[index].get("baud") or 115200)

            for index in range(PORT_COUNT):
                old_cfg, new_cfg = old_cfgs[index], new_cfgs[index]
                endpoint_changed = (
                    str(old_cfg.get("device") or "") != str(new_cfg.get("device") or "")
                    or int(old_cfg.get("baud") or 0) != int(new_cfg.get("baud") or 0)
                )
                running = self.is_running(index)
                device = str(new_cfg.get("device") or "")

                if not device:
                    if running:
                        self._stop_worker(index)
                    elif self._stats[index].state != "idle":
                        self._set_state(index, "idle", "")
                    continue

                if running:
                    if endpoint_changed:
                        self._stop_worker(index)
                        self._start(index)
                else:
                    state = self._stats[index].state
                    if endpoint_changed or state != "error":
                        self._start(index)
        self._ensure_timer()

    def set_enabled(self, index: int, enabled: bool) -> None:
        """只切换是否周期发送；串口保持打开以持续接收。"""
        if self._closed or not 0 <= int(index) < PORT_COUNT:
            return
        index = int(index)
        with self._control_lock:
            with self._lock:
                self._configs[index]["enabled"] = bool(enabled)
                device = str(self._configs[index].get("device") or "")
            if enabled and device and not self.is_running(index):
                self._start(index)
        self._ensure_timer()

    def enable_all(self) -> None:
        for index in range(PORT_COUNT):
            self.set_enabled(index, True)

    def disable_all(self) -> None:
        for index in range(PORT_COUNT):
            self.set_enabled(index, False)

    def is_running(self, index: int) -> bool:
        if not 0 <= int(index) < PORT_COUNT:
            return False
        with self._lock:
            worker = self._workers.get(int(index))
        return bool(worker is not None and worker.alive)

    # ---- 发送 / 统计 -----------------------------------------------------
    def send_once(self, index: int) -> None:
        if self._closed or not 0 <= int(index) < PORT_COUNT:
            return
        with self._lock:
            worker = self._workers.get(int(index))
        if worker is not None and worker.alive:
            worker.force_send()

    def stats(self) -> dict[int, PortStats]:
        return self._snapshot()

    def reset_errors(self) -> None:
        """只清零错误计数，不清零接收频率/成功帧数。"""
        with self._lock:
            for index in range(PORT_COUNT):
                stats = self._stats[index]
                stats.parse_errors = 0
                stats.header_errors = 0
                stats.crc_errors = 0
                stats.last_error = ""
        self._broadcast_stats()

    def shutdown(self) -> None:
        with self._control_lock:
            if self._closed:
                return
            self._closed = True
            try:
                self._timer.stop()
            except Exception:
                pass
            with self._lock:
                workers = list(self._workers.items())
                self._workers.clear()
            for _index, worker in workers:
                worker.stop()
            with self._lock:
                for index in range(PORT_COUNT):
                    self._rx_times[index].clear()
                    self._rx_total_times[index].clear()
                    self._tx_times[index].clear()
                    self._stats[index].rx_hz = 0.0
                    self._stats[index].rx_total_hz = 0.0
                    self._stats[index].tx_hz = 0.0
            for index in range(PORT_COUNT):
                self._set_state(index, "idle", "")

    # ---- 内部：配置 ------------------------------------------------------
    def _copy_config(self, index: int) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._configs[int(index)])

    def _merge_config(self, index: int, raw: Any) -> dict[str, Any]:
        with self._lock:
            cfg = copy.deepcopy(self._configs[index])
        if not isinstance(raw, dict):
            return cfg
        if "name" in raw:
            cfg["name"] = str(raw.get("name") or cfg.get("name") or f"端口 {index + 1}")[:32]
        if "device" in raw:
            cfg["device"] = str(raw.get("device") or "")
        if "baud" in raw:
            try:
                baud = int(raw.get("baud"))
            except (TypeError, ValueError):
                baud = int(cfg.get("baud") or 115200)
            cfg["baud"] = baud if baud > 0 else 115200
        if "rate_hz" in raw:
            try:
                rate = float(raw.get("rate_hz"))
            except (TypeError, ValueError):
                rate = float(cfg.get("rate_hz") or 100.0)
            cfg["rate_hz"] = max(0.1, min(1000.0, rate))
        if "enabled" in raw:
            cfg["enabled"] = bool(raw.get("enabled"))
        return cfg

    # ---- 内部：生命周期 --------------------------------------------------
    def _start(self, index: int) -> None:
        if self._closed:
            return
        with self._control_lock:
            if self._closed:
                return
            with self._lock:
                worker = self._workers.get(index)
                if worker is not None and worker.alive:
                    return
            cfg = self._copy_config(index)
            device = str(cfg.get("device") or "")
            if not device:
                self._set_state(index, "error", "未选择串口设备")
                return
            if not device.upper().startswith(VIRTUAL_PREFIX) and serial is None:
                self._set_state(index, "error", "未安装 pyserial，无法打开真实串口")
                return

            worker = _PortWorker(self, index)
            with self._lock:
                self._workers[index] = worker
                self._stats[index].device = device
                self._stats[index].baud = int(cfg.get("baud") or 115200)
                self._stats[index].last_error = ""
                self._rx_times[index].clear()
                self._rx_total_times[index].clear()
                self._tx_times[index].clear()
            try:
                worker.start()
            except Exception as exc:
                with self._lock:
                    self._workers.pop(index, None)
                self._set_state(index, "error", f"无法启动端口线程：{exc}")

    def _stop_worker(self, index: int) -> None:
        with self._control_lock:
            with self._lock:
                worker = self._workers.pop(index, None)
            if worker is not None:
                worker.stop()
            with self._lock:
                self._rx_times[index].clear()
                self._rx_total_times[index].clear()
                self._tx_times[index].clear()
            self._set_state(index, "idle", "")

    # ---- 内部：状态 / 统计 ----------------------------------------------
    def _set_state(self, index: int, state: str, message: str = "") -> None:
        with self._lock:
            stats = self._stats[index]
            if stats.state == state and stats.message == message:
                return
            stats.state = state
            stats.message = message
            if state == "error":
                stats.last_error = message
            cfg = self._configs[index]
            stats.device = str(cfg.get("device") or "")
            stats.baud = int(cfg.get("baud") or 115200)
        self.port_state_changed.emit(index, state, message)

    def _note_tx(self, index: int, nbytes: int) -> None:
        with self._lock:
            stats = self._stats[index]
            stats.tx_frames += 1
            stats.tx_bytes += max(0, int(nbytes))
            self._tx_times[index].append(time.perf_counter())

    def _handle_rx(self, index: int, data: bytes, parser: FrameParser) -> None:
        headers, frames, errors = parser.feed(data)
        if not (headers or frames or errors):
            with self._lock:
                self._stats[index].rx_bytes += len(data)
            return

        now = time.perf_counter()
        wall = time.time()
        success_events: list[SuccessEvent] = []
        error_events: list[ParseError] = []

        with self._lock:
            stats = self._stats[index]
            stats.rx_bytes += len(data)

            for _header in headers:
                stats.rx_total_frames += 1
                self._rx_total_times[index].append(now)

            for frame in frames:
                frame.port_index = index
                if frame.valid:
                    stats.rx_frames += 1
                    stats.last_rx_ts = wall
                    self._rx_times[index].append(now)
                    success_events.append(SuccessEvent(index, wall, frame.raw[:HEADER_LEN]))

            for reason, raw, detail in errors:
                stats.parse_errors += 1
                if "CRC16" in reason:
                    stats.crc_errors += 1
                else:
                    stats.header_errors += 1
                stats.last_error = reason
                error_events.append(ParseError(index, wall, reason, raw, detail))

        for event in success_events:
            self.receive_success.emit(event)
        for event in error_events:
            self.receive_error.emit(event)

    def _rate(self, times: deque[float]) -> float:
        count = len(times)
        if count < 2:
            return float(count) if count else 0.0
        span = times[-1] - times[0]
        return (count - 1) / span if span > 0 else 0.0

    def _prune_rates(self, now: float) -> None:
        cutoff = now - RATE_WINDOW
        for index in range(PORT_COUNT):
            for times in (
                self._rx_times[index],
                self._rx_total_times[index],
                self._tx_times[index],
            ):
                while times and times[0] < cutoff:
                    times.popleft()

    def _snapshot(self) -> dict[int, PortStats]:
        now = time.perf_counter()
        with self._lock:
            self._prune_rates(now)
            result: dict[int, PortStats] = {}
            for index in range(PORT_COUNT):
                snap = replace(self._stats[index])
                snap.rx_hz = self._rate(self._rx_times[index])
                snap.rx_total_hz = self._rate(self._rx_total_times[index])
                snap.tx_hz = self._rate(self._tx_times[index])
                result[index] = snap
            return result

    def _broadcast_stats(self) -> None:
        if self._closed:
            return
        self.stats_updated.emit(self._snapshot())

    def _ensure_timer(self) -> None:
        if self._closed:
            return
        try:
            if QCoreApplication.instance() is not None and not self._timer.isActive():
                self._timer.start()
        except Exception:
            pass


__all__ = ["FrameParser", "SerialManager"]
