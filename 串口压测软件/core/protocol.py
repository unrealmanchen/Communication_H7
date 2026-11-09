"""哨兵底盘串口通信协议编解码。

协议来源：docx《哨兵底盘通信》（2025.1.10 v1.0）

帧结构（22 字节，data 长度固定 13 时）::

    +--------+--------+--------+--------+--------+---------+------------------+--------+
    | 0xA5   | len_lo | len_hi |   0    | crc8   | cmd_id  |   data (13 B)    | crc16  |
    +--------+--------+--------+--------+--------+---------+------------------+--------+
       SOF     data 长度(uint16 LE)  校验头   (uint16 LE)   payload      (uint16 LE)

* ``crc8``  : CRC8(init=0xFF) 覆盖前 4 字节
* ``crc16`` : CRC16(init=0xFFFF) 覆盖 header + cmd_id + data
* 多字节数值一律小端序，float 为 IEEE-754 单精度。
"""

from __future__ import annotations

import struct
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

SOF = 0xA5
DATA_LEN = 13
HEADER_LEN = 5
FRAME_LEN = HEADER_LEN + 2 + DATA_LEN + 2  # 22

CRC8_INIT = 0xFF
CRC16_INIT = 0xFFFF


def _make_crc8_table() -> tuple[int, ...]:
    """生成 CRC8 表：G(x)=x^8+x^5+x^4+1，反射多项式 0x8C。"""
    table: list[int] = []
    for index in range(256):
        crc = index
        for _ in range(8):
            crc = ((crc >> 1) ^ 0x8C) if (crc & 1) else (crc >> 1)
        table.append(crc & 0xFF)
    return tuple(table)


def _make_crc16_table() -> tuple[int, ...]:
    """生成 CRC16 表：反射多项式 0x8408（即 CCITT 反射）。"""
    table: list[int] = []
    for index in range(256):
        crc = index
        for _ in range(8):
            crc = ((crc >> 1) ^ 0x8408) if (crc & 1) else (crc >> 1)
        table.append(crc & 0xFFFF)
    return tuple(table)


CRC8_TAB = _make_crc8_table()
CRC16_TAB = _make_crc16_table()


def crc8(data: bytes | bytearray, init: int = CRC8_INIT) -> int:
    crc = init
    for byte in data:
        crc = CRC8_TAB[(crc ^ byte) & 0xFF]
    return crc


def crc16(data: bytes | bytearray, init: int = CRC16_INIT) -> int:
    crc = init
    for byte in data:
        crc = ((crc >> 8) ^ CRC16_TAB[(crc ^ byte) & 0xFF]) & 0xFFFF
    return crc


def build_frame(cmd_id: int, data: bytes | bytearray, data_len: int | None = None) -> bytes:
    """按协议构造一帧。默认 data 长度 13 字节。"""
    payload = bytes(data)
    if data_len is None:
        data_len = len(payload)
    if len(payload) != data_len:
        raise ValueError(f"data 长度应为 {data_len}，实际 {len(payload)}")
    if not 0 <= cmd_id <= 0xFFFF:
        raise ValueError(f"非法 cmd_id: {cmd_id}")
    header = bytearray([SOF, data_len & 0xFF, (data_len >> 8) & 0xFF, 0x00])
    header.append(crc8(header))
    frame = bytearray(header)
    frame += struct.pack("<H", cmd_id)
    frame += payload
    frame += struct.pack("<H", crc16(frame))
    return bytes(frame)


@dataclass
class Frame:
    """一帧接收数据。"""

    cmd_id: int
    data: bytes
    raw: bytes
    valid: bool = True
    timestamp: float = field(default_factory=time.time)
    port_index: int = -1

    @property
    def data_len(self) -> int:
        return len(self.data)

    @property
    def cmd_hex(self) -> str:
        return f"0x{self.cmd_id:03X}"


def next_frame(buffer: bytearray) -> tuple[Frame | None, int]:
    """从缓冲区头部尝试取出一帧。

    返回 ``(frame, consumed)``：

    * ``consumed == 0``：数据不完整，继续等待；
    * ``frame is None, consumed > 0``：丢弃了若干无效/噪声字节；
    * ``frame.valid is False``：帧结构完整但 CRC16 校验失败。
    """
    if not buffer:
        return None, 0

    # 丢弃 SOF 之前的噪声
    if buffer[0] != SOF:
        pos = buffer.find(SOF)
        if pos < 0:
            return None, len(buffer)
        return None, pos

    if len(buffer) < HEADER_LEN:
        return None, 0

    data_len = buffer[1] | (buffer[2] << 8)
    if buffer[3] != 0x00 or data_len > 4096 or crc8(bytes(buffer[:4])) != buffer[4]:
        return None, 1

    total = HEADER_LEN + 2 + data_len + 2
    if len(buffer) < total:
        return None, 0

    raw = bytes(buffer[:total])
    cmd_id = struct.unpack_from("<H", raw, 5)[0]
    payload = raw[7 : 7 + data_len]
    expected = crc16(raw[:-2])
    valid = raw[-2] == (expected & 0xFF) and raw[-1] == ((expected >> 8) & 0xFF)
    return Frame(cmd_id=cmd_id, data=payload, raw=raw, valid=valid), total


def verify_frame(raw: bytes) -> bool:
    """校验一条完整帧（22 字节或变长帧）。"""
    if len(raw) < 9 or raw[0] != SOF or raw[3] != 0:
        return False
    data_len = raw[1] | (raw[2] << 8)
    if len(raw) != HEADER_LEN + 2 + data_len + 2:
        return False
    if crc8(raw[:4]) != raw[4]:
        return False
    expected = crc16(raw[:-2])
    return raw[-2] == (expected & 0xFF) and raw[-1] == ((expected >> 8) & 0xFF)


def hex_bytes(data: bytes | bytearray, sep: str = " ") -> str:
    return sep.join(f"{byte:02x}" for byte in data)


# --------------------------------------------------------------------------
# 命令元数据
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    kind: str  # float / uint32 / uint8 / enum
    default: float | int
    offset: int
    unit: str = ""
    decimals: int = 3
    minimum: float = -1_000_000.0
    maximum: float = 1_000_000.0
    step: float = 0.1
    choices: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class CommandSpec:
    cmd_id: int
    name: str
    description: str
    direction: str
    fields: tuple[FieldSpec, ...] = ()

    @property
    def label(self) -> str:
        return f"0x{self.cmd_id:03X}  {self.name}"


COMMANDS: dict[int, CommandSpec] = {
    0x401: CommandSpec(
        0x401,
        "雷达 IMU 数据下发",
        "原雷达 IMU 数据下发，云台姿态改由独立 IMU 获得，暂时弃用。",
        "上位机 → 通信板",
    ),
    0x402: CommandSpec(
        0x402,
        "底盘速度指令",
        "以头朝向前为 X 轴正方向、右为 Y 轴正方向，角速度为逆时针为正。",
        "上位机 → 通信板",
        fields=(
            FieldSpec("linear_x", "X 线速度", "float", 1.5, 0, "m/s", 3, -10.0, 10.0, 0.1),
            FieldSpec("linear_y", "Y 线速度", "float", 0.0, 4, "m/s", 3, -10.0, 10.0, 0.1),
            FieldSpec("angular_z", "Z 角速度", "float", 0.5, 8, "rad/s", 3, -20.0, 20.0, 0.1),
        ),
    ),
    0x403: CommandSpec(
        0x403,
        "云台角度指令",
        "角度制，转到目标角度，顺时针为正。",
        "上位机 → 通信板",
        fields=(
            FieldSpec("big_yaw", "大云台 Yaw", "float", 90.0, 0, "°", 2, -720.0, 720.0, 1.0),
            FieldSpec("small_yaw", "小云台 Yaw", "float", 30.0, 4, "°", 2, -720.0, 720.0, 1.0),
            FieldSpec("small_pitch", "小云台 Pitch", "float", -10.0, 8, "°", 2, -90.0, 90.0, 1.0),
        ),
    ),
    0x404: CommandSpec(
        0x404,
        "发射机构控制（已替代）",
        "仅用于遥控器调试，控制摩擦轮与小转盘，存在炸盘风险，已由 0x405 替代。",
        "上位机 → 通信板",
        fields=(
            FieldSpec("fire_count", "发射个数", "uint32", 0, 0, "发", 0, 0, 1000, 1),
            FieldSpec(
                "stop",
                "立即停止",
                "enum",
                0,
                12,
                choices=((0, "否"), (1, "是（清空待发弹）")),
            ),
        ),
    ),
    0x405: CommandSpec(
        0x405,
        "模式切换指令",
        "切换底盘跟随模式。",
        "上位机 → 通信板",
        fields=(
            FieldSpec(
                "mode",
                "跟随模式",
                "enum",
                1,
                12,
                choices=((1, "跟随底盘（默认）"), (2, "跟随云台"), (3, "小陀螺")),
            ),
        ),
    ),
    0x406: CommandSpec(
        0x406,
        "上位机停机/开机回传",
        "收到 0x306 后必须回传接收到的内容。",
        "上位机 → 通信板",
        fields=(
            FieldSpec(
                "power",
                "开机状态",
                "enum",
                1,
                0,
                choices=((0, "关机"), (1, "开机")),
            ),
        ),
    ),
}

# 接收方向命令（用于日志显示名称）
RX_COMMAND_NAMES = {
    0x301: "Yaw 轴角度信息",
    0x302: "小云台角度信息",
    0x303: "设备在线状态",
    0x304: "裁判系统数据",
    0x305: "发射机构指令确认",
    0x306: "上位机停机/开机指令",
    0x201: "底盘 Yaw 值",
    0x202: "底盘状态信息",
    0x203: "底盘停机/开机回传",
    0x101: "小云台 IMU 数据",
    0x102: "大云台 IMU 数据",
    0x103: "底盘速度指令",
    0x104: "转动角度指令",
    0x105: "模式切换指令",
    0x106: "底盘停机/开机指令",
    0x501: "小云台 IMU 数据",
    0x601: "小云台角度指令",
    0x602: "发射指令",
}

ONLINE_BITS: tuple[tuple[int, int, str], ...] = (
    (0, 0, "底盘 M3508 ×4"),
    (1, 0, "MF9025 电机"),
    (1, 1, "底盘 C 板"),
    (1, 2, "云台 Yaw 6020"),
    (1, 3, "云台 Pitch 6020"),
    (2, 0, "摩擦轮 M3508 左"),
    (2, 1, "摩擦轮 M3508 右"),
    (2, 2, "大云台 IMU"),
    (2, 3, "小云台 IMU"),
    (3, 0, "拨弹盘 2006"),
    (3, 1, "云台 C 板"),
    (3, 2, "裁判系统"),
    (3, 3, "图传"),
)


def command_name(cmd_id: int) -> str:
    spec = COMMANDS.get(cmd_id)
    if spec:
        return spec.name
    return RX_COMMAND_NAMES.get(cmd_id, f"未知指令 0x{cmd_id:03X}")


def default_params(cmd_id: int) -> dict[str, Any]:
    spec = COMMANDS.get(cmd_id)
    if spec is None:
        return {}
    return {item.key: item.default for item in spec.fields}


def pack_payload(cmd_id: int, values: dict[str, Any] | None = None) -> bytes:
    """把界面参数打包为 13 字节 data。未知/缺省字段填 0。"""
    values = values or {}
    payload = bytearray(DATA_LEN)
    spec = COMMANDS.get(cmd_id)
    if spec is None:
        return bytes(payload)
    for item in spec.fields:
        value = values.get(item.key, item.default)
        try:
            if item.kind == "float":
                struct.pack_into("<f", payload, item.offset, float(value))
            elif item.kind == "uint32":
                struct.pack_into("<I", payload, item.offset, int(value) & 0xFFFFFFFF)
            else:
                payload[item.offset] = int(value) & 0xFF
        except (struct.error, ValueError, TypeError):
            # 非法值按默认值重新打包，保证发送线程不崩
            if item.kind == "float":
                struct.pack_into("<f", payload, item.offset, float(item.default))
            elif item.kind == "uint32":
                struct.pack_into("<I", payload, item.offset, int(item.default) & 0xFFFFFFFF)
            else:
                payload[item.offset] = int(item.default) & 0xFF
    return bytes(payload)


def build_command_frame(cmd_id: int, values: dict[str, Any] | None = None) -> bytes:
    return build_frame(cmd_id, pack_payload(cmd_id, values))


def _read_float(data: bytes, offset: int) -> float | None:
    if len(data) < offset + 4:
        return None
    return struct.unpack_from("<f", data, offset)[0]


def format_float(value: float, unit: str = "", decimals: int = 2) -> str:
    text = f"{value:.{decimals}f}"
    if text in ("-0.00", "-0.0"):
        text = text[1:]
    return f"{text}{unit}" if unit else text


def decode_payload(cmd_id: int, data: bytes) -> list[tuple[str, str]]:
    """把 data 解码为 ``[(字段名, 显示值), ...]``，用于日志展示。"""
    result: list[tuple[str, str]] = []

    if cmd_id == 0x301:
        chassis = _read_float(data, 0)
        big_yaw = _read_float(data, 4)
        limit = data[12] if len(data) > 12 else 0
        if chassis is not None:
            result.append(("底盘 Yaw", format_float(chassis, "°")))
        if big_yaw is not None:
            result.append(("大云台 Yaw", format_float(big_yaw, "°")))
        result.append(("小云台限位", "是" if limit else "否"))
    elif cmd_id == 0x302:
        small_yaw = _read_float(data, 0)
        small_pitch = _read_float(data, 4)
        if small_yaw is not None:
            result.append(("小云台 Yaw", format_float(small_yaw, "°")))
        if small_pitch is not None:
            result.append(("小云台 Pitch", format_float(small_pitch, "°")))
    elif cmd_id == 0x303:
        online_names: list[str] = []
        offline_count = 0
        for byte_index, bit_index, name in ONLINE_BITS:
            if byte_index >= len(data):
                offline_count += 1
                continue
            if data[byte_index] & (1 << bit_index):
                online_names.append(name)
            else:
                offline_count += 1
        result.append(("在线设备", f"{len(online_names)}/{len(ONLINE_BITS)}"))
        result.append(("在线列表", "、".join(online_names) if online_names else "无"))
        if offline_count:
            result.append(("离线数量", str(offline_count)))
    elif cmd_id == 0x305:
        value = data[0] if data else 0
        result.append(("请求成功", "是" if value & 0x01 else "否"))
        result.append(("请求发射状态", "开" if value & 0x02 else "关"))
        result.append(("当前发射状态", "开" if value & 0x04 else "关"))
    elif cmd_id == 0x306:
        result.append(("开机状态", "开机" if (data[0] if data else 0) else "关机"))
    elif cmd_id == 0x304:
        result.append(("裁判系统数据", f"{len(data)} 字节"))
        result.append(("原始数据", hex_bytes(data)))
    elif cmd_id in COMMANDS:
        spec = COMMANDS[cmd_id]
        for item in spec.fields:
            if item.kind == "float":
                value = _read_float(data, item.offset)
                if value is not None:
                    result.append((item.label, format_float(value, item.unit, item.decimals)))
            elif item.kind == "uint32":
                if len(data) >= item.offset + 4:
                    value = struct.unpack_from("<I", data, item.offset)[0]
                    result.append((item.label, str(value)))
            elif item.kind == "enum":
                if len(data) > item.offset:
                    raw = data[item.offset]
                    label = dict(item.choices).get(raw, str(raw))
                    result.append((item.label, label))
            else:
                if len(data) > item.offset:
                    result.append((item.label, str(data[item.offset])))
        if not result:
            result.append(("数据", hex_bytes(data)))
    else:
        result.append(("数据", hex_bytes(data)))

    return result


def format_frame(frame: Frame) -> str:
    """单行摘要，例如 ``底盘 Yaw 12.30° · 大云台 Yaw 45.00° · 小云台限位 否``。"""
    if not frame.valid:
        return "CRC16 校验失败"
    fields = decode_payload(frame.cmd_id, frame.data)
    return " · ".join(f"{name} {value}" for name, value in fields)


def iter_commands() -> Iterable[CommandSpec]:
    return (COMMANDS[key] for key in sorted(COMMANDS))
