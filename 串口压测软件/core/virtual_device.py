"""虚拟底盘设备：无需真实硬件即可演示七路串口收发。

``VIRTUAL:1`` … ``VIRTUAL:7`` 不占用任何真实 COM 口。由
:class:`core.serial_manager.SerialManager` 的独立工作线程按 ``reply_rate_hz``
周期调用 :meth:`VirtualChassisDevice.due_payloads` 取得协议帧字节流，再喂给
与真实串口完全相同的流式解析器（``core.protocol.next_frame``）。

因此虚拟端口不是"假信号"，而是真的走一遍 编码 → 字节流 → 解析 → Frame 流程，
UI 收到的数据与真实底盘回传格式完全一致。
"""

from __future__ import annotations

import math
import struct
import time

from core.protocol import DATA_LEN, build_frame

# 0x303 在线状态位：底盘 4 电机 / 云台 C 板与两个 6020 / 摩擦轮与 IMU / 拨弹盘…
# 全在线时按字节为 0x01 0x0F 0x0F 0x0F（共 13 个设备在线）。
DEFAULT_ONLINE_BYTES: tuple[int, int, int, int] = (0x01, 0x0F, 0x0F, 0x0F)

#: 与真实底盘一致的回传命令轮转顺序。
REPLY_CYCLE: tuple[int, ...] = (0x303, 0x301, 0x302)


def wrap_angle(angle: float) -> float:
    """把角度归一化到 (-180, 180]。"""
    wrapped = (angle + 180.0) % 360.0 - 180.0
    if wrapped <= -180.0:
        wrapped += 360.0
    return wrapped


def online_payload(online: bool = True) -> bytes:
    """构造 0x303 设备在线状态的 13 字节 data。"""
    payload = bytearray(DATA_LEN)
    if online:
        payload[0:4] = bytes(DEFAULT_ONLINE_BYTES)
    return bytes(payload)


class VirtualChassisDevice:
    """单路虚拟底盘的数据源。

    数值随"运行时间 + 端口号"变化，保证 7 路界面同时演示时曲线互不相同。
    本类不创建线程、不依赖 Qt，可在测试中直接驱动。
    """

    def __init__(self, port_index: int, reply_rate_hz: float = 20.0) -> None:
        self.port_index = int(port_index)
        self.reply_rate_hz = float(reply_rate_hz)
        self._t0 = time.perf_counter()
        self._next_due = self._t0
        self._cycle_pos = self.port_index % len(REPLY_CYCLE)
        self.online = True

    # -- 速率 ----------------------------------------------------------------

    @property
    def reply_interval(self) -> float:
        return 1.0 / max(0.1, float(self.reply_rate_hz))

    @property
    def next_due_at(self) -> float:
        """下一帧应产生的 :func:`time.perf_counter` 时刻（供线程精确排程）。

        注意：Windows 上 ``time.monotonic()`` 分辨率只有约 15.6ms，
        高回传速率会被拖慢，因此内部统一使用高精度 ``perf_counter``。
        """
        return self._next_due

    def set_reply_rate(self, reply_rate_hz: float, now: float | None = None) -> bool:
        """热更新回传频率；变化时立即重新对齐下一帧时刻。"""
        new_rate = max(0.1, float(reply_rate_hz))
        if abs(new_rate - self.reply_rate_hz) < 1e-9:
            return False
        self.reply_rate_hz = new_rate
        self._next_due = time.perf_counter() if now is None else now
        return True

    def due_payloads(self, now: float | None = None, max_frames: int = 8) -> list[bytes]:
        """返回截止 ``now`` 应产生的全部回传帧字节串。

        * 每过一个回传周期产生一帧，按 0x303 → 0x301 → 0x302 轮转；
        * ``now`` 缺省取 :func:`time.perf_counter`；
        * 线程被长时间挂起后会一次性补齐，但最多 ``max_frames`` 帧，
          避免恢复时突发刷屏。
        """
        if now is None:
            now = time.perf_counter()
        interval = self.reply_interval
        if now - self._next_due > interval * max_frames:
            # 落后太多（例如系统休眠/线程被抢占），直接对齐到当前时刻
            self._next_due = now

        payloads: list[bytes] = []
        while now >= self._next_due and len(payloads) < max_frames:
            cmd_id = REPLY_CYCLE[self._cycle_pos % len(REPLY_CYCLE)]
            self._cycle_pos += 1
            payloads.append(build_frame(cmd_id, self.build_payload(cmd_id, now)))
            self._next_due += interval
        return payloads

    # -- 数据 ----------------------------------------------------------------

    def elapsed(self, now: float | None = None) -> float:
        if now is None:
            now = time.perf_counter()
        return max(0.0, now - self._t0)

    def build_payload(self, cmd_id: int, now: float | None = None) -> bytes:
        """生成指定命令的 13 字节 data。"""
        elapsed = self.elapsed(now)
        index = self.port_index

        payload = bytearray(DATA_LEN)
        if cmd_id == 0x303:
            payload[0:4] = bytes(DEFAULT_ONLINE_BYTES) if self.online else b"\x00\x00\x00\x00"
        elif cmd_id == 0x301:
            chassis_yaw = wrap_angle(
                index * 45.0 + elapsed * (18.0 + index * 4.0) + 20.0 * math.sin(elapsed * 1.1 + index)
            )
            big_yaw = 90.0 + index * 3.0 + 50.0 * math.sin(elapsed * 0.8 + index * 0.55)
            struct.pack_into("<f", payload, 0, chassis_yaw)
            struct.pack_into("<f", payload, 4, big_yaw)
            payload[12] = 1 if math.sin(elapsed * 0.5 + index) > 0.9 else 0
        elif cmd_id == 0x302:
            small_yaw = wrap_angle(-25.0 + index * 6.0 + 35.0 * math.sin(elapsed * 1.3 + index * 0.4))
            small_pitch = -8.0 + 14.0 * math.sin(elapsed * 1.7 + index * 0.3)
            struct.pack_into("<f", payload, 0, small_yaw)
            struct.pack_into("<f", payload, 4, small_pitch)
        return bytes(payload)

    def build_reply_frame(self, cmd_id: int, now: float | None = None) -> bytes:
        """生成一条完整回传帧（带正确 CRC8/CRC16）。"""
        return build_frame(cmd_id, self.build_payload(cmd_id, now))


__all__ = [
    "DEFAULT_ONLINE_BYTES",
    "REPLY_CYCLE",
    "VirtualChassisDevice",
    "online_payload",
    "wrap_angle",
]
