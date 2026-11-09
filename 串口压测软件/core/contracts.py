"""核心模块共享的数据契约。

界面层只依赖本文件与 :class:`core.serial_manager.SerialManager` 的公开接口，
串口后端可以在不修改界面的情况下替换实现。
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PortInfo:
    device: str
    label: str
    is_virtual: bool = False

    @property
    def display(self) -> str:
        return self.label


@dataclass
class PortStats:
    index: int = 0
    device: str = ""
    baud: int = 115200
    state: str = "idle"  # idle / opening / running / error
    message: str = ""
    rx_frames: int = 0          # 解析成功的完整帧数
    rx_total_frames: int = 0    # 收到有效帧头的总帧数（含 CRC16 失败）
    tx_frames: int = 0
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_hz: float = 0.0          # 解析成功频率
    rx_total_hz: float = 0.0    # 总接收频率
    tx_hz: float = 0.0
    crc_errors: int = 0
    header_errors: int = 0
    parse_errors: int = 0
    last_rx_ts: float = 0.0
    last_error: str = ""

    @property
    def running(self) -> bool:
        return self.state == "running"

    @property
    def has_data(self) -> bool:
        return self.last_rx_ts > 0

    @property
    def error_attempts(self) -> int:
        """错误率分母：总接收帧 + 帧头非法候选。"""
        return self.rx_total_frames + self.header_errors

    @property
    def error_rate(self) -> float:
        attempts = self.error_attempts
        return (self.parse_errors / attempts * 100.0) if attempts else 0.0


@dataclass(frozen=True)
class SuccessEvent:
    """一次解析成功：帧头、长度、CRC16 全部通过。"""

    port_index: int
    timestamp: float
    header: bytes = b""

    @property
    def header_hex(self) -> str:
        return " ".join(f"{byte:02x}" for byte in self.header)


@dataclass(frozen=True)
class ParseError:
    """一次解析错误，用于接收记录页打印。"""

    port_index: int
    timestamp: float
    reason: str
    raw: bytes = b""
    detail: str = ""

    @property
    def raw_hex(self) -> str:
        return " ".join(f"{byte:02x}" for byte in self.raw)


STATE_LABELS = {
    "idle": "未开启",
    "opening": "打开中",
    "connected": "已连接",
    "running": "发送中",
    "error": "异常",
}


__all__ = ["PortInfo", "PortStats", "SuccessEvent", "ParseError", "STATE_LABELS"]
