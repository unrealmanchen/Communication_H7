"""外部配置持久化测试。"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from core.config_store import ConfigStore, default_config, normalize_config


class ConfigStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "config.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_default_has_seven_ports_without_extra_fields(self) -> None:
        config = default_config()
        ports = config["send"]["ports"]
        self.assertEqual(len(ports), 7)
        self.assertTrue(all(port["device"] == "" for port in ports))
        self.assertTrue(all(port["baud"] == 115200 for port in ports))
        self.assertTrue(all(port["rate_hz"] == 100.0 for port in ports))
        self.assertNotIn("command", ports[0])
        self.assertNotIn("params", ports[0])

    def test_save_and_load_roundtrip(self) -> None:
        store = ConfigStore(self.path)
        store.data = default_config()
        port = store.data["send"]["ports"][0]
        port.update(device="COM9", baud=921600, rate_hz=250.0, enabled=True)
        store.data["receive"].update(mode="single", single_port=4)
        store.save()
        self.assertTrue(self.path.exists())

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(raw["send"]["ports"][0]["device"], "COM9")

        reloaded = ConfigStore(self.path)
        reloaded.load()
        port = reloaded.data["send"]["ports"][0]
        self.assertEqual(port["device"], "COM9")
        self.assertEqual(port["baud"], 921600)
        self.assertEqual(port["rate_hz"], 250.0)
        self.assertTrue(port["enabled"])
        self.assertEqual(reloaded.data["receive"]["mode"], "single")
        self.assertEqual(reloaded.data["receive"]["single_port"], 4)

    def test_missing_file_uses_defaults(self) -> None:
        store = ConfigStore(self.path)
        store.load()
        self.assertEqual(len(store.data["send"]["ports"]), 7)
        self.assertEqual(store.load_error, "")

    def test_broken_json_falls_back(self) -> None:
        self.path.write_text("{ this is not json", encoding="utf-8")
        store = ConfigStore(self.path)
        store.load()
        self.assertTrue(store.load_error)
        self.assertEqual(len(store.data["send"]["ports"]), 7)

    def test_invalid_values_are_clamped(self) -> None:
        config = normalize_config(
            {
                "send": {
                    "ports": [
                        {
                            "device": "COM1",
                            "baud": -1,
                            "rate_hz": 99999,
                            "enabled": "yes",
                            "command": 1026,
                            "params": {"x": 1},
                        }
                    ]
                },
                "receive": {"mode": "nonsense", "single_port": 99},
                "window": {"width": 10, "height": 10},
            }
        )
        self.assertEqual(len(config["send"]["ports"]), 7)
        port = config["send"]["ports"][0]
        self.assertEqual(port["baud"], 115200)
        self.assertEqual(port["rate_hz"], 1000.0)
        self.assertTrue(port["enabled"])
        self.assertEqual(port["device"], "COM1")
        self.assertNotIn("command", port)
        self.assertEqual(config["receive"]["mode"], "all")
        self.assertEqual(config["receive"]["single_port"], 6)
        self.assertGreaterEqual(config["window"]["width"], 900)
        self.assertGreaterEqual(config["window"]["height"], 600)


if __name__ == "__main__":
    unittest.main(verbosity=2)
