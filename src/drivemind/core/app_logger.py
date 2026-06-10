from __future__ import annotations

import logging
import os
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import ConfigManager, app_base_dir

_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def log_dir() -> Path:
    path = app_base_dir() / "log"
    path.mkdir(parents=True, exist_ok=True)
    return path


def configure_logging(config: ConfigManager | None = None) -> Path:
    """DriveMind のファイルログを初期化します。"""
    config = config or ConfigManager()
    level_name = str(config.get("log.level", "warning")).lower()
    level = _LEVELS.get(level_name, logging.WARNING)
    max_mb = max(1, int(config.get("log.max_size_mb", 64) or 64))
    keep_days = max(0, int(config.get("log.keep_days", 7) or 7))
    folder = log_dir()
    _cleanup_old_logs(folder, keep_days)
    path = folder / "DriveMind.log"

    root = logging.getLogger()
    root.setLevel(level)
    for handler in list(root.handlers):
        if getattr(handler, "_drivemind_handler", False):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
    handler = RotatingFileHandler(path, maxBytes=max_mb * 1024 * 1024, backupCount=5, encoding="utf-8")
    handler._drivemind_handler = True  # type: ignore[attr-defined]
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    root.addHandler(handler)
    logging.getLogger(__name__).info("logging configured: level=%s max_mb=%s keep_days=%s", level_name, max_mb, keep_days)
    return path


def _cleanup_old_logs(folder: Path, keep_days: int) -> None:
    if keep_days <= 0:
        return
    cutoff = time.time() - keep_days * 86400
    for path in folder.glob("*.log*"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except Exception:
            pass


def delete_all_logs() -> int:
    """ログファイルを削除します。Windows で開いているログを消せるように、専用ハンドラを先に閉じます。"""
    root = logging.getLogger()
    for handler in list(root.handlers):
        if getattr(handler, "_drivemind_handler", False):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass
    count = 0
    for path in log_dir().glob("*.log*"):
        try:
            path.unlink(missing_ok=True)
            count += 1
        except Exception:
            pass
    return count


def open_log_folder() -> None:
    folder = log_dir()
    if os.name == "nt":
        os.startfile(str(folder))  # type: ignore[attr-defined]
    elif os.uname().sysname == "Darwin":  # type: ignore[attr-defined]
        import subprocess
        subprocess.Popen(["open", str(folder)])
    else:
        import subprocess
        subprocess.Popen(["xdg-open", str(folder)])


def log_total_size() -> int:
    """現在のログフォルダ内にあるログファイルの合計サイズを返します。"""
    total = 0
    for path in log_dir().glob("*.log*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except Exception:
            pass
    return total
