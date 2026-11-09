"""协议编解码单元测试（与 docx 示例逐字节对齐）。"""

from __future__ import annotations

import struct
import unittest

from core.protocol import (
    COMMANDS,
    FRAME_LEN,
    Frame,
    build_command_frame,
    build_frame,
    crc8,
    crc16,
    decode_payload,
    format_frame,
    hex_bytes,
    next_frame,
    pack_payload,
    verify_frame,
)

DOC_EXAMPLE = bytes.fromhex(
    "a5 0d 00 00 d3 02 04 00 00 c0 3f 00 00 20 40 00 00 00 3f 00 98 1f"
)


class ProtocolDocExampleTest(unittest.TestCase):
    def test_doc_example_exact_bytes(self) -> None:
        frame = build_command_frame(0x402, {"linear_x": 1.5, "linear_y": 2.5, "angular_z": 0.5})
        self.assertEqual(hex_bytes(frame), hex_bytes(DOC_EXAMPLE))
        self.assertEqual(len(frame), FRAME_LEN)
        self.assertTrue(verify_frame(frame))

    def test_crc8_header(self) -> None:
        self.assertEqual(crc8(bytes([0xA5, 0x0D, 0x00, 0x00])), 0xD3)

    def test_crc16_value_and_little_endian(self) -> None:
        self.assertEqual(crc16(DOC_EXAMPLE[:-2]), 0x1F98)
        self.assertEqual(DOC_EXAMPLE[-2:], bytes([0x98, 0x1F]))

    def test_parse_doc_example(self) -> None:
        buffer = bytearray(DOC_EXAMPLE)
        frame, consumed = next_frame(buffer)
        self.assertIsNotNone(frame)
        self.assertEqual(consumed, 22)
        assert frame is not None
        self.assertTrue(frame.valid)
        self.assertEqual(frame.cmd_id, 0x402)
        self.assertEqual(len(frame.data), 13)
        x, y, z = struct.unpack("<fff", frame.data[:12])
        self.assertAlmostEqual(x, 1.5, places=6)
        self.assertAlmostEqual(y, 2.5, places=6)
        self.assertAlmostEqual(z, 0.5, places=6)

    def test_format_frame(self) -> None:
        frame, _ = next_frame(bytearray(DOC_EXAMPLE))
        assert frame is not None
        summary = format_frame(frame)
        self.assertIn("X 线速度", summary)
        self.assertIn("1.500", summary)


class FrameParsingTest(unittest.TestCase):
    def test_partial_frame_waits(self) -> None:
        buffer = bytearray(DOC_EXAMPLE[:10])
        frame, consumed = next_frame(buffer)
        self.assertIsNone(frame)
        self.assertEqual(consumed, 0)

    def test_noise_is_skipped(self) -> None:
        buffer = bytearray(b"\x00\x11\x22" + DOC_EXAMPLE)
        frame, consumed = next_frame(buffer)
        self.assertIsNone(frame)
        self.assertEqual(consumed, 3)
        del buffer[:consumed]
        frame, consumed = next_frame(buffer)
        self.assertIsNotNone(frame)
        self.assertEqual(consumed, 22)

    def test_bad_crc16_flagged(self) -> None:
        corrupted = bytearray(DOC_EXAMPLE)
        corrupted[-1] ^= 0xFF
        frame, consumed = next_frame(corrupted)
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertFalse(frame.valid)
        self.assertEqual(consumed, 22)
        self.assertIn("CRC16", format_frame(frame))

    def test_bad_header_crc_resyncs(self) -> None:
        corrupted = bytearray(DOC_EXAMPLE)
        corrupted[4] = 0x00
        frame, consumed = next_frame(corrupted)
        self.assertIsNone(frame)
        self.assertEqual(consumed, 1)

    def test_variable_length_frame(self) -> None:
        payload = bytes(range(20))
        raw = build_frame(0x304, payload)
        frame, consumed = next_frame(bytearray(raw))
        self.assertIsNotNone(frame)
        assert frame is not None
        self.assertEqual(frame.cmd_id, 0x304)
        self.assertEqual(frame.data, payload)
        self.assertEqual(consumed, len(raw))

    def test_unknown_command_still_parses(self) -> None:
        raw = build_frame(0x7FF, bytes(13))
        frame, _ = next_frame(bytearray(raw))
        assert frame is not None
        self.assertEqual(frame.cmd_id, 0x7FF)
        self.assertTrue(frame.valid)


class CommandsTest(unittest.TestCase):
    def test_all_commands_pack_13_bytes_and_roundtrip(self) -> None:
        for cmd_id, spec in COMMANDS.items():
            with self.subTest(cmd=hex(cmd_id)):
                values = {item.key: item.default for item in spec.fields}
                payload = pack_payload(cmd_id, values)
                self.assertEqual(len(payload), 13)
                raw = build_frame(cmd_id, payload)
                self.assertTrue(verify_frame(raw))
                frame = Frame(cmd_id=cmd_id, data=payload, raw=raw)
                self.assertTrue(format_frame(frame))
                self.assertTrue(decode_payload(cmd_id, payload))

    def test_status_commands_decode(self) -> None:
        online = decode_payload(0x303, bytes([0x0F, 0x0F, 0x0F, 0x0E]))
        labels = dict(online)
        self.assertEqual(labels["在线设备"], "12/13")

        ack = decode_payload(0x305, bytes([0x07] + [0] * 12))
        labels = dict(ack)
        self.assertEqual(labels["请求成功"], "是")
        self.assertEqual(labels["请求发射状态"], "开")
        self.assertEqual(labels["当前发射状态"], "开")

        power = decode_payload(0x306, bytes([1] + [0] * 12))
        self.assertEqual(dict(power)["开机状态"], "开机")


if __name__ == "__main__":
    unittest.main(verbosity=2)
