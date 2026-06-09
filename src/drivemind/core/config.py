from __future__ import annotations

import json
import shutil
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from .fingerprint import generate_machine_fingerprint


def app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd().resolve()


DEFAULT_SETTINGS: dict[str, Any] = {
    "basic": {
        # 初期値は3分です。設定画面で変更できます。
        "refresh_interval_seconds": 180,
        "autosave_minutes": 5,
        "config_file_path": "",
        "capacity_decimals": 2,
        "percent_decimals": 2,
        # システムパーティションを含む物理ディスクは内部ドライブとして扱います。
        "treat_system_disk_as_internal": True,
        # ESP / MSR / OEM パーティションは初期値では表示しません。
        "show_esp_partitions": False,
        "show_msr_partitions": False,
        "show_oem_partitions": False,
        # 必要な場合だけ管理者権限で起動します。
        "run_as_admin": False,
    },
    "desktop_naotu": {
        "exe_path": "",
    },
    "mindmap": {
        "exclude_names": [
            "System Volume Information",
            "$RECYCLE.BIN",
            "$MFT",
            "$Extend",
            "$Secure",
            "$LogFile",
        ],
        "include_hidden": True,
        "mark_hidden": True,
        "include_system": False,
        "include_files": False,
        "include_extensions": True,
        "max_depth": 48,
        "max_files_per_folder": 16,
    },
    "catalogs": {
        # グループ名 -> 背景色。色なしの場合は空文字です。
        "groups": {},
        "purposes": [],
        "memos": [],
    },
    "other": {
        "update_check_frequency": "daily",
        "last_update_check": "",
        "suppress_update_date": "",
        "skip_version": "",
    },
    "ui": {
        "column_order_state": "",
        "summary_single_mode": False,
        # 初期表示はドライブ名 A-Z 順です。
        "sort_column": 2,
        "sort_desc": False,
    },
    "drive_notes": {},
    "runtime": {
        "last_export_path": "",
    },
}


def deep_merge(base: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _unique_sorted(values: list[Any] | tuple[Any, ...] | set[Any]) -> list[str]:
    cleaned = {str(v).strip() for v in values if str(v).strip()}
    return sorted(cleaned, key=str.casefold)


class ConfigManager:
    def __init__(self) -> None:
        self.fingerprint = generate_machine_fingerprint()
        self.default_path = app_base_dir() / "Config" / f"{self.fingerprint}.txt"
        self.path = self.default_path
        self.settings: dict[str, Any] = deepcopy(DEFAULT_SETTINGS)
        self.load()
        self._migrate_catalogs_from_notes()

    def load(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._load_from_path(self.path, merge=True)
        custom_path = self.get("basic.config_file_path", "")
        if custom_path:
            candidate = Path(str(custom_path)).expanduser()
            if candidate != self.path and candidate.exists():
                self.path = candidate
                self._load_from_path(candidate, merge=True)

    def _load_from_path(self, path: Path, merge: bool = True) -> bool:
        if not path.exists():
            return False
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(data, dict):
                self.settings = deep_merge(self.settings if merge else deepcopy(DEFAULT_SETTINGS), data)
                return True
        except Exception:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            broken = path.with_suffix(path.suffix + f".broken-{timestamp}")
            try:
                shutil.copy2(path, broken)
            except Exception:
                pass
        return False

    def load_from_file_merge(self, path: str | Path) -> bool:
        ok = self._load_from_path(Path(path).expanduser(), merge=True)
        if ok:
            self._migrate_catalogs_from_notes()
        return ok

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.set("basic.config_file_path", str(self.path))
        text = json.dumps(self.settings, ensure_ascii=False, indent=2)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(self.path)

    def set_config_file_path(self, path: str | Path) -> None:
        candidate = Path(path).expanduser()
        if candidate.suffix.lower() != ".txt":
            candidate = candidate.with_suffix(".txt")
        self.path = candidate
        self.set("basic.config_file_path", str(candidate))

    def get(self, dotted_key: str, default: Any = None) -> Any:
        cur: Any = self.settings
        for part in dotted_key.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def set(self, dotted_key: str, value: Any) -> None:
        parts = dotted_key.split(".")
        cur = self.settings
        for part in parts[:-1]:
            if part not in cur or not isinstance(cur[part], dict):
                cur[part] = {}
            cur = cur[part]
        cur[parts[-1]] = value

    def drive_note(self, key: str) -> dict[str, Any]:
        notes = self.settings.setdefault("drive_notes", {})
        return notes.setdefault(key, {})

    def set_drive_note_value(self, key: str, field: str, value: Any) -> None:
        note = self.drive_note(key)
        note[field] = value
        if field == "group" and str(value).strip():
            self.add_group(str(value).strip())
        elif field == "purpose" and str(value).strip():
            self.add_purpose(str(value).strip())
        elif field == "memo" and str(value).strip():
            self.add_memo(str(value).strip())

    def _catalogs(self) -> dict[str, Any]:
        return self.settings.setdefault("catalogs", {"groups": {}, "purposes": [], "memos": []})

    def _migrate_catalogs_from_notes(self) -> None:
        for note in self.settings.get("drive_notes", {}).values():
            group = str(note.get("group", "")).strip()
            purpose = str(note.get("purpose", "")).strip()
            memo = str(note.get("memo", "")).strip()
            if group:
                self.add_group(group)
            if purpose:
                self.add_purpose(purpose)
            if memo:
                self.add_memo(memo)

    def known_groups(self) -> list[str]:
        groups = set(self._catalogs().get("groups", {}).keys())
        for note in self.settings.get("drive_notes", {}).values():
            group = str(note.get("group", "")).strip()
            if group:
                groups.add(group)
        return sorted(groups, key=str.casefold)

    def add_group(self, name: str, color: str = "") -> None:
        name = name.strip()
        if not name:
            return
        groups = self._catalogs().setdefault("groups", {})
        old = str(groups.get(name, ""))
        groups[name] = color.strip() or old

    def rename_group(self, old_name: str, new_name: str) -> None:
        old_name = old_name.strip()
        new_name = new_name.strip()
        if not old_name or not new_name or old_name == new_name:
            return
        groups = self._catalogs().setdefault("groups", {})
        color = str(groups.pop(old_name, ""))
        groups[new_name] = color or str(groups.get(new_name, ""))
        for note in self.settings.get("drive_notes", {}).values():
            if str(note.get("group", "")).strip() == old_name:
                note["group"] = new_name

    def remove_group(self, name: str) -> int:
        name = name.strip()
        self._catalogs().setdefault("groups", {}).pop(name, None)
        changed = 0
        for note in self.settings.get("drive_notes", {}).values():
            if str(note.get("group", "")).strip() == name:
                note["group"] = ""
                changed += 1
        return changed

    def set_group_color(self, name: str, color: str) -> None:
        name = name.strip()
        if name:
            self.add_group(name)
            self._catalogs().setdefault("groups", {})[name] = color.strip()

    def group_color(self, name: str) -> str:
        if not name:
            return ""
        return str(self._catalogs().setdefault("groups", {}).get(name.strip(), ""))

    def known_purposes(self) -> list[str]:
        values = set(self._catalogs().get("purposes", []))
        for note in self.settings.get("drive_notes", {}).values():
            value = str(note.get("purpose", "")).strip()
            if value:
                values.add(value)
        return sorted(values, key=str.casefold)

    def add_purpose(self, value: str) -> None:
        values = set(self._catalogs().setdefault("purposes", []))
        if value.strip():
            values.add(value.strip())
        self._catalogs()["purposes"] = _unique_sorted(values)

    def remove_purpose(self, value: str) -> int:
        value = value.strip()
        self._catalogs()["purposes"] = [v for v in self.known_purposes() if v != value]
        changed = 0
        for note in self.settings.get("drive_notes", {}).values():
            if str(note.get("purpose", "")).strip() == value:
                note["purpose"] = ""
                changed += 1
        return changed

    def known_memos(self) -> list[str]:
        values = set(self._catalogs().get("memos", []))
        for note in self.settings.get("drive_notes", {}).values():
            value = str(note.get("memo", "")).strip()
            if value:
                values.add(value)
        return sorted(values, key=str.casefold)

    def add_memo(self, value: str) -> None:
        values = set(self._catalogs().setdefault("memos", []))
        if value.strip():
            values.add(value.strip())
        self._catalogs()["memos"] = _unique_sorted(values)

    def remove_memo(self, value: str) -> int:
        value = value.strip()
        self._catalogs()["memos"] = [v for v in self.known_memos() if v != value]
        changed = 0
        for note in self.settings.get("drive_notes", {}).values():
            if str(note.get("memo", "")).strip() == value:
                note["memo"] = ""
                changed += 1
        return changed
