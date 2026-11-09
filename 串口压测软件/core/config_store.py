"""外部 JSON 配置：7 路串口参数、接收页模式、窗口位置。"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

PORT_COUNT = 7
CONFIG_FILENAME = "config.json"
DEFAULT_BAUD = 115200
DEFAULT_RATE = 100.0
BAUD_CHOICES = (9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600, 1000000, 2000000)


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def default_config_path() -> Path:
    return app_root() / CONFIG_FILENAME


def _default_port(index: int) -> dict[str, Any]:
    return {
        "name": f"端口 {index + 1}",
        "device": "",
        "baud": DEFAULT_BAUD,
        "rate_hz": DEFAULT_RATE,
        "enabled": False,
    }


def default_config() -> dict[str, Any]:
    return {
        "version": 5,
        "window": {"width": 1180, "height": 780, "x": None, "y": None, "maximized": False},
        "send": {"ports": [_default_port(index) for index in range(PORT_COUNT)]},
        "receive": {
            "mode": "all",
            "single_port": 0,
            "success_log": True,
            "error_log": True,
        },
    }


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _normalize_port(raw: Any, index: int) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    port = _default_port(index)

    try:
        baud = int(raw.get("baud", DEFAULT_BAUD))
    except (TypeError, ValueError):
        baud = DEFAULT_BAUD
    port["baud"] = baud if baud > 0 else DEFAULT_BAUD

    try:
        rate = float(raw.get("rate_hz", DEFAULT_RATE))
    except (TypeError, ValueError):
        rate = DEFAULT_RATE
    port["rate_hz"] = round(_clamp(rate, 0.1, 1000.0), 2)

    port["device"] = str(raw.get("device") or "")
    port["enabled"] = bool(raw.get("enabled", False))
    return port


def normalize_config(raw: Any) -> dict[str, Any]:
    raw = raw if isinstance(raw, dict) else {}
    cfg = default_config()

    window = raw.get("window") if isinstance(raw.get("window"), dict) else {}
    for key in ("width", "height", "x", "y", "maximized"):
        if key in window:
            cfg["window"][key] = window[key]
    try:
        cfg["window"]["width"] = int(_clamp(int(cfg["window"]["width"]), 900, 10000))
        cfg["window"]["height"] = int(_clamp(int(cfg["window"]["height"]), 600, 10000))
    except (TypeError, ValueError):
        cfg["window"] = default_config()["window"]
    for key in ("x", "y"):
        if cfg["window"].get(key) is not None:
            try:
                cfg["window"][key] = int(cfg["window"][key])
            except (TypeError, ValueError):
                cfg["window"][key] = None
    cfg["window"]["maximized"] = bool(cfg["window"].get("maximized", False))

    receive = raw.get("receive") if isinstance(raw.get("receive"), dict) else {}
    cfg["receive"]["mode"] = receive.get("mode") if receive.get("mode") in ("all", "single") else "all"
    try:
        cfg["receive"]["single_port"] = int(_clamp(int(receive.get("single_port", 0)), 0, PORT_COUNT - 1))
    except (TypeError, ValueError):
        cfg["receive"]["single_port"] = 0
    cfg["receive"]["success_log"] = bool(receive.get("success_log", True))
    cfg["receive"]["error_log"] = bool(receive.get("error_log", True))

    raw_ports = raw.get("send", {}).get("ports") if isinstance(raw.get("send"), dict) else None
    cfg["send"]["ports"] = [
        _normalize_port(raw_ports[index] if isinstance(raw_ports, list) and index < len(raw_ports) else None, index)
        for index in range(PORT_COUNT)
    ]
    return cfg


class ConfigStore:
    """读写程序目录下的 ``config.json``（UTF-8，缩进 2 空格，原子替换）。"""

    def __init__(self, path: str | os.PathLike[str] | None = None):
        self.path = Path(path) if path else default_config_path()
        self.data: dict[str, Any] = default_config()
        self.load_error = ""

    def load(self) -> dict[str, Any]:
        self.load_error = ""
        if not self.path.exists():
            self.data = default_config()
            return self.data
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8-sig"))
            self.data = normalize_config(raw)
        except Exception as exc:
            self.load_error = f"配置文件读取失败，已使用默认配置：{exc}"
            self.data = default_config()
        return self.data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.data, ensure_ascii=False, indent=2) + "\n"
        fd, temp_name = tempfile.mkstemp(prefix=".config-", suffix=".json", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, self.path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def reset(self) -> dict[str, Any]:
        self.data = copy.deepcopy(default_config())
        return self.data
