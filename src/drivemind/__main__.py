from __future__ import annotations

import ctypes
import os
import subprocess
import sys

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from drivemind.core.config import ConfigManager
from drivemind.ui.main_window import MainWindow
from drivemind.ui.theme import apply_theme
from drivemind.version import APP_NAME


def app_asset_path(name: str) -> Path:
    return Path(__file__).resolve().parent / "assets" / name


def _is_windows_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
    except Exception:
        return False


def _maybe_relaunch_as_admin() -> bool:
    if os.name != "nt":
        return False
    config = ConfigManager()
    if not bool(config.get("basic.run_as_admin", False)):
        return False
    if _is_windows_admin():
        return False
    if os.environ.get("DRIVEMIND_ELEVATION_ATTEMPTED") == "1":
        return False
    try:
        env = os.environ.copy()
        env["DRIVEMIND_ELEVATION_ATTEMPTED"] = "1"
        if getattr(sys, "frozen", False):
            exe = sys.executable
            params = " ".join(f'"{arg}"' for arg in sys.argv[1:])
        else:
            exe = sys.executable
            params = "-m drivemind " + " ".join(f'"{arg}"' for arg in sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)  # type: ignore[attr-defined]
        return True
    except Exception:
        # 昇格できない場合は通常権限のまま起動します。
        return False


def main() -> int:
    if _maybe_relaunch_as_admin():
        return 0
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("S2OUnicus")
    runtime_config = ConfigManager()
    apply_theme(app, str(runtime_config.get("basic.theme", "dark")))
    icon_path = app_asset_path("logo_pure.ico")
    icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
    if icon.isNull():
        icon = QIcon(str(app_asset_path("logo.ico")))
    if not icon.isNull():
        app.setWindowIcon(icon)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
