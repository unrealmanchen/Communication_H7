"""七路串口引擎测试：常开接收、帧头成功计数、独立开关与线程清理。"""

from __future__ import annotations

import os
import sys
import threading
import time
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication  # noqa: E402

from core.config_store import default_config  # noqa: E402
from core.protocol import build_frame  # noqa: E402
from core.serial_manager import FrameParser  # noqa: E402
import core.serial_manager as serial_manager_module  # noqa: E402


def ensure_app() -> QCoreApplication:
    return QCoreApplication.instance() or QCoreApplication([])


def wait_for(condition, timeout: float = 2.0, interval: float = 0.01) -> bool:
    app = ensure_app()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        try:
            if condition():
                return True
        except Exception:
            pass
        time.sleep(interval)
    app.processEvents()
    return bool(condition())


def make_ports(rate_hz: float = 50.0, enabled: bool = False) -> list[dict]:
    ports = default_config()["send"]["ports"]
    for index, port in enumerate(ports):
        port["device"] = f"VIRTUAL:{index + 1}"
        port["rate_hz"] = rate_hz
        port["enabled"] = enabled
    return ports


def assert_no_worker_threads() -> None:
    alive = [
        thread.name
        for thread in threading.enumerate()
        if thread.name.startswith("serial-port-") and thread.is_alive()
    ]
    assert not alive, f"关闭后仍有后台线程: {alive}"


class FrameParserTest(unittest.TestCase):
    def test_one_frame(self) -> None:
        frame = build_frame(0x301, bytes(13))
        headers, frames, errors = FrameParser().feed(frame)
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], frame[:5])
        self.assertEqual(len(frames), 1)
        self.assertTrue(frames[0].valid)
        self.assertEqual(errors, [])

    def test_two_frames_with_noise(self) -> None:
        data = b"\x00\x11" + build_frame(0x301, bytes(13)) + build_frame(0x303, bytes(13))
        headers, frames, errors = FrameParser().feed(data)
        self.assertEqual(len(headers), 2)
        self.assertEqual(len(frames), 2)
        self.assertEqual(errors, [])

    def test_bad_header_crc_reported(self) -> None:
        frame = bytearray(build_frame(0x301, bytes(13)))
        frame[4] ^= 0xFF
        headers, frames, errors = FrameParser().feed(frame)
        self.assertEqual(headers, [])
        self.assertEqual(frames, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("帧头", errors[0][0])
        self.assertIn("CRC8 期望", errors[0][2])
        self.assertEqual(errors[0][1], bytes(frame))

    def test_bad_crc16_reported(self) -> None:
        frame = bytearray(build_frame(0x301, bytes(13)))
        frame[-1] ^= 0xFF
        headers, frames, errors = FrameParser().feed(frame)
        self.assertEqual(len(headers), 1)
        self.assertEqual(len(frames), 1)
        self.assertFalse(frames[0].valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("CRC16", errors[0][0])
        self.assertIn("CRC16 期望", errors[0][2])
        self.assertEqual(errors[0][1], bytes(frame))

    def test_payload_a5_not_false_positive(self) -> None:
        payload = bytes.fromhex("a5 0d 00 00 d3") + bytes(8)
        frame = build_frame(0x301, payload)
        headers, frames, errors = FrameParser().feed(frame)
        self.assertEqual(len(headers), 1)
        self.assertEqual(len(frames), 1)
        self.assertEqual(errors, [])

    def test_split_bytes(self) -> None:
        frame = build_frame(0x302, bytes(13))
        parser = FrameParser()
        headers = []
        frames = []
        errors = []
        for byte in frame:
            h, f, e = parser.feed(bytes([byte]))
            headers.extend(h)
            frames.extend(f)
            errors.extend(e)
        self.assertEqual(len(headers), 1)
        self.assertEqual(len(frames), 1)
        self.assertTrue(frames[0].valid)
        self.assertEqual(errors, [])


class SerialManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        ensure_app()
        self.manager = serial_manager_module.SerialManager(reply_rate_hz=20.0)
        self.events: list = []
        self.manager.receive_success.connect(self.events.append)

    def tearDown(self) -> None:
        self.manager.shutdown()
        assert_no_worker_threads()

    def test_ports_receive_even_when_send_switch_off(self) -> None:
        ports = make_ports(rate_hz=100.0, enabled=False)
        self.manager.apply_config(ports)
        self.assertTrue(
            wait_for(
                lambda: all(
                    self.manager.stats()[index].state == "running"
                    and self.manager.stats()[index].rx_frames > 0
                    for index in range(7)
                ),
                timeout=3.0,
            ),
            [(i, s.state, s.rx_frames) for i, s in self.manager.stats().items()],
        )
        stats = self.manager.stats()
        self.assertTrue(all(stat.tx_frames == 0 for stat in stats.values()))
        self.assertTrue(all(stat.rx_hz > 0 for stat in stats.values()))
        self.assertTrue(wait_for(lambda: {event.port_index for event in self.events} == set(range(7)), 2.0))

    def test_enable_starts_sending_without_reopening_port(self) -> None:
        ports = make_ports(rate_hz=100.0, enabled=False)
        self.manager.apply_config(ports)
        self.assertTrue(wait_for(lambda: self.manager.stats()[0].rx_frames > 0, 2.0))

        self.manager.set_enabled(0, True)
        self.assertTrue(wait_for(lambda: self.manager.stats()[0].tx_hz > 20, 3.0))
        self.assertTrue(self.manager.stats()[0].tx_frames > 0)

        self.manager.set_enabled(0, False)
        self.assertTrue(self.manager.is_running(0))
        self.assertTrue(wait_for(lambda: self.manager.stats()[0].tx_hz == 0, 3.0))
        before = self.manager.stats()[0].rx_frames
        self.assertTrue(wait_for(lambda: self.manager.stats()[0].rx_frames > before, 2.0))

    def test_hot_update_rate_and_device_restart(self) -> None:
        ports = make_ports(rate_hz=20.0, enabled=True)
        self.manager.apply_config(ports)
        self.assertTrue(wait_for(lambda: self.manager.stats()[0].state == "running", 2.0))
        self.assertTrue(wait_for(lambda: 5 < self.manager.stats()[0].tx_hz < 40, 3.0))

        ports[0]["rate_hz"] = 200.0
        self.manager.apply_config(ports)
        self.assertTrue(wait_for(lambda: self.manager.stats()[0].tx_hz > 120, 3.0))
        self.assertTrue(self.manager.is_running(0))

        ports[0]["device"] = "VIRTUAL:5"
        self.manager.apply_config(ports)
        self.assertTrue(wait_for(lambda: self.manager.stats()[0].state == "running", 3.0))
        self.assertTrue(wait_for(lambda: self.manager.stats()[0].rx_frames > 0, 2.0))

    def test_error_isolation(self) -> None:
        ports = make_ports(rate_hz=50.0, enabled=False)
        ports[0]["device"] = "COM99"
        ports[1]["enabled"] = True
        self.manager.apply_config(ports)
        self.assertTrue(wait_for(lambda: self.manager.stats()[0].state == "error", 3.0))
        self.assertIn("COM99", self.manager.stats()[0].message)
        self.assertTrue(
            wait_for(
                lambda: self.manager.stats()[1].state == "running"
                and self.manager.stats()[1].rx_frames > 0
                and self.manager.stats()[1].tx_frames > 0,
                timeout=2.0,
            )
        )


class FakeSerialPort:
    instances: list["FakeSerialPort"] = []

    def __init__(self, port=None, baudrate=115200, timeout=0.02, write_timeout=0.5, **kwargs):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.closed = False
        self.read_calls = 0
        self._rx = bytearray()
        FakeSerialPort.instances.append(self)

    @property
    def in_waiting(self) -> int:
        return len(self._rx)

    def reset_input_buffer(self) -> None:
        self._rx.clear()

    def read(self, size: int = 1) -> bytes:
        self.read_calls += 1
        end = time.perf_counter() + max(0.0, float(self.timeout or 0.0))
        while True:
            if self._rx:
                chunk = bytes(self._rx[:size])
                del self._rx[:size]
                return chunk
            if time.perf_counter() >= end:
                return b""
            time.sleep(0.0005)

    def write(self, data) -> int:
        self._rx.extend(bytes(data))
        return len(data)

    def close(self) -> None:
        self.closed = True


class _fake_serial_module:
    def __enter__(self):
        self.real = serial_manager_module.serial
        FakeSerialPort.instances.clear()
        serial_manager_module.serial = types.SimpleNamespace(Serial=FakeSerialPort)
        return FakeSerialPort

    def __exit__(self, *exc_info):
        serial_manager_module.serial = self.real
        return False


class ErrorRateTest(unittest.TestCase):
    def test_success_total_and_error_rate(self) -> None:
        ensure_app()
        manager = serial_manager_module.SerialManager(reply_rate_hz=20.0)
        parser = serial_manager_module.FrameParser()
        try:
            valid = build_frame(0x301, bytes(13))
            bad_crc = bytearray(build_frame(0x301, bytes(13)))
            bad_crc[-1] ^= 0xFF
            bad_header = bytearray(build_frame(0x301, bytes(13)))
            bad_header[4] ^= 0xFF

            manager._handle_rx(0, valid, parser)
            manager._handle_rx(0, bytes(bad_crc), parser)
            manager._handle_rx(0, bytes(bad_header), parser)
            stats = manager.stats()[0]
            self.assertEqual(stats.rx_frames, 1)
            self.assertEqual(stats.rx_total_frames, 2)
            self.assertEqual(stats.parse_errors, 2)
            self.assertEqual(stats.header_errors, 1)
            self.assertEqual(stats.error_attempts, 3)
            self.assertAlmostEqual(stats.error_rate, 2 / 3 * 100, places=3)

            manager.reset_errors()
            stats = manager.stats()[0]
            self.assertEqual(stats.parse_errors, 0)
            self.assertEqual(stats.header_errors, 0)
            self.assertEqual(stats.error_rate, 0.0)
            self.assertEqual(stats.rx_total_frames, 2)
        finally:
            manager.shutdown()


class RealSerialPathTest(unittest.TestCase):
    def test_fake_serial_loopback(self) -> None:
        ensure_app()
        with _fake_serial_module():
            manager = serial_manager_module.SerialManager(reply_rate_hz=20.0)
            events: list = []
            manager.receive_success.connect(events.append)
            try:
                ports = make_ports(rate_hz=50.0, enabled=True)
                ports[0]["device"] = "COM_FAKE"
                manager.apply_config(ports)
                self.assertTrue(wait_for(lambda: manager.stats()[0].state == "running", 2.0))
                self.assertTrue(wait_for(lambda: manager.stats()[0].tx_frames > 0, 2.0))
                self.assertTrue(wait_for(lambda: manager.stats()[0].rx_frames > 0, 2.0))
                self.assertTrue(events)
                self.assertEqual(events[0].port_index, 0)
            finally:
                manager.shutdown()
            assert_no_worker_threads()
            self.assertTrue(FakeSerialPort.instances[0].closed)


class ShutdownTest(unittest.TestCase):
    def test_shutdown_stops_threads(self) -> None:
        ensure_app()
        manager = serial_manager_module.SerialManager(reply_rate_hz=20.0)
        manager.apply_config(make_ports(rate_hz=50.0, enabled=True))
        self.assertTrue(wait_for(lambda: all(manager.is_running(i) for i in range(7)), 3.0))
        manager.shutdown()
        assert_no_worker_threads()
        self.assertTrue(all(not manager.is_running(i) for i in range(7)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
