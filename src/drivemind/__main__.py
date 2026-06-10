from __future__ import annotations

import ctypes
import os
import subprocess
import sys

from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEventLoop, QPropertyAnimation, QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from drivemind.core.config import ConfigManager
from drivemind.core.app_logger import configure_logging
from drivemind.ui.main_window import MainWindow
from drivemind.ui.theme import apply_theme
from drivemind.version import APP_NAME


def app_asset_path(name: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidate = Path(sys._MEIPASS) / "drivemind" / "assets" / name  # type: ignore[attr-defined]
        if candidate.exists():
            return candidate
        candidate = Path(sys._MEIPASS) / "assets" / name  # type: ignore[attr-defined]
        if candidate.exists():
            return candidate
    return Path(__file__).resolve().parent / "assets" / name



def _show_brand_splash(app: QApplication) -> None:
    """起動時に Brand.png を短くフェードイン / フェードアウト表示します。"""
    brand_path = app_asset_path("Brand.png")
    if not brand_path.exists():
        return
    pixmap = QPixmap(str(brand_path))
    if pixmap.isNull():
        return
    try:
        screen = app.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            max_width = max(360, int(available.width() * 0.46))
            max_height = max(220, int(available.height() * 0.38))
            pixmap = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        splash = QSplashScreen(pixmap, Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        splash.setAttribute(Qt.WA_TranslucentBackground, True)
        splash.setWindowOpacity(0.0)
        if screen:
            available = screen.availableGeometry()
            splash.move(available.center() - splash.rect().center())
        splash.show()
        app.processEvents()

        loop = QEventLoop()
        fade_in = QPropertyAnimation(splash, b"windowOpacity")
        fade_in.setDuration(520)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.InOutCubic)

        fade_out = QPropertyAnimation(splash, b"windowOpacity")
        fade_out.setDuration(520)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.InOutCubic)

        fade_in.finished.connect(lambda: QTimer.singleShot(760, fade_out.start))
        fade_out.finished.connect(loop.quit)
        fade_in.start()
        loop.exec()
        splash.close()
        app.processEvents()
    except Exception:
        # スプラッシュ表示に失敗しても本体起動は妨げません。
        return

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
    configure_logging(runtime_config)
    apply_theme(app, str(runtime_config.get("basic.theme", "dark")))
    icon_path = app_asset_path("logo_pure.ico")
    icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
    if icon.isNull():
        icon = QIcon(str(app_asset_path("logo.ico")))
    if not icon.isNull():
        app.setWindowIcon(icon)
    _show_brand_splash(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
