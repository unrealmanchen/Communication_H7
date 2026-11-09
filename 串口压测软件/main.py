"""哨兵底盘 · 七路串口工具 — 程序入口。

用法：
    python main.py
    python main.py --page receive
    python main.py --capture out.png
    python main.py --config D:/path/config.json
"""

from __future__ import annotations

import argparse
import ctypes
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from core.config_store import ConfigStore
from ui import theme
from ui.branding import make_app_icon
from ui.main_window import MainWindow


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="哨兵底盘七路串口工具")
    parser.add_argument("--config", type=str, default=None, help="外部配置文件路径，默认程序目录下 config.json")
    parser.add_argument("--page", choices=("send", "receive"), default="send", help="启动时显示的页面")
    parser.add_argument("--capture", type=str, default=None, help="截图输出路径（自检用），截图后退出")
    parser.add_argument("--capture-delay", type=int, default=1500, help="截图前等待毫秒数")
    return parser.parse_args(argv)


def _enable_windows_timer_resolution() -> None:
    """把 Windows 定时器精度提到 1ms，降低串口超时/线程调度的抖动。"""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    _enable_windows_timer_resolution()

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv[:1])
    app.setApplicationName("SentryChassisSerialTool")
    app.setApplicationDisplayName("哨兵底盘 · 七路串口工具")
    theme.apply_theme(app)
    app.setWindowIcon(make_app_icon())

    store = ConfigStore(args.config)
    store.load()
    if not store.path.exists():
        try:
            store.save()
        except OSError:
            pass

    window = MainWindow(store)
    window.show()
    if store.data.get("window", {}).get("maximized"):
        window.showMaximized()
    if args.page == "receive":
        QTimer.singleShot(60, lambda: window.tabs.setCurrentIndex(1))

    if args.capture:
        capture_path = Path(args.capture).resolve()

        def capture_and_quit() -> None:
            if args.page == "receive":
                window.tabs.setCurrentIndex(1)
            QApplication.processEvents()
            capture_path.parent.mkdir(parents=True, exist_ok=True)
            pixmap = window.grab()
            if not pixmap.save(str(capture_path)):
                print(f"CAPTURE_FAILED {capture_path}", flush=True)
            else:
                print(f"CAPTURED {capture_path} {pixmap.width()}x{pixmap.height()}", flush=True)
            window.close()
            app.quit()

        QTimer.singleShot(max(300, args.capture_delay), capture_and_quit)

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
