from __future__ import annotations

import ctypes
import fnmatch
import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .config import ConfigManager
from .models import DeviceInfo, VolumeInfo

FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4
FILE_ATTRIBUTE_REPARSE_POINT = 0x400


@dataclass(slots=True)
class PathFlags:
    hidden: bool = False
    system: bool = False
    symlink: bool = False


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now_ms() -> int:
    return int(time.time() * 1000)


def make_node(text: str, children: list[dict] | None = None) -> dict:
    return {
        "data": {
            "id": _new_id(),
            "created": _now_ms(),
            "text": text,
        },
        "children": children or [],
    }


def path_flags(path: Path) -> PathFlags:
    if os.name == "nt":
        try:
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))  # type: ignore[attr-defined]
            if attrs == -1:
                return PathFlags()
            return PathFlags(
                hidden=bool(attrs & FILE_ATTRIBUTE_HIDDEN),
                system=bool(attrs & FILE_ATTRIBUTE_SYSTEM),
                symlink=bool(attrs & FILE_ATTRIBUTE_REPARSE_POINT),
            )
        except Exception:
            return PathFlags()
    name = path.name
    return PathFlags(hidden=name.startswith("."), system=False, symlink=path.is_symlink())


def display_name(path: Path, include_extensions: bool, mark_hidden: bool, flags: PathFlags) -> str:
    name = path.name or str(path)
    if path.is_file() and not include_extensions and path.suffix:
        name = path.stem
    if mark_hidden and flags.hidden:
        name += " [Hide]"
    return name



ADOBE_PROJECT_SUFFIXES = {
    ".prproj": "PR-Proj",
    ".aep": "AE-Proj",
    ".aepx": "AE-Proj",
}
PROGRAM_COMPANION_DIRS = {
    "bin", "lib", "libs", "include", "share", "resources", "plugins", "plugin", "dist", "build", "runtime", "scripts"
}


def _matches_exclude(name: str, patterns: set[str]) -> bool:
    lowered = name.lower()
    for pattern in patterns:
        if not pattern:
            continue
        p = pattern.lower()
        if fnmatch.fnmatch(lowered, p):
            return True
    return False


def _adobe_project_label(folder: Path) -> str | None:
    try:
        for entry in folder.iterdir():
            if entry.is_file():
                prefix = ADOBE_PROJECT_SUFFIXES.get(entry.suffix.lower())
                if prefix:
                    return f"{prefix}：{entry.stem}"
    except OSError:
        return None
    return None


def _looks_like_program_folder(folder: Path) -> bool:
    """控えめな判定でプログラムフォルダをまとめます。単体 exe だけでは判定しません。"""
    try:
        entries = list(folder.iterdir())
    except OSError:
        return False
    companion_dirs = {e.name.lower() for e in entries if e.is_dir()} & PROGRAM_COMPANION_DIRS
    if not companion_dirs:
        return False
    for entry in entries:
        try:
            if entry.is_file() and entry.suffix.lower() == ".exe":
                return True
            if entry.is_dir() and entry.name.lower() in {"bin", "runtime"}:
                for sub in entry.iterdir():
                    if sub.is_file() and sub.suffix.lower() == ".exe":
                        return True
        except OSError:
            continue
    return False

class MindmapExporter:
    def __init__(self, config: ConfigManager) -> None:
        self.config = config
        self.errors: list[str] = []
        self.max_depth = int(self.config.get("mindmap.max_depth", 48) or 48)
        self.max_files_per_folder = int(self.config.get("mindmap.max_files_per_folder", 16) or 16)

    def export(
        self,
        devices: list[DeviceInfo],
        selected_keys: set[str],
        output_path: str | Path,
        max_depth: int | None = None,
        max_files_per_folder: int | None = None,
    ) -> Path:
        self.errors.clear()
        self._set_limits(max_depth, max_files_per_folder)
        output = Path(output_path)
        root = make_node("DriveMind")
        output_device_name = bool(self.config.get("mindmap.output_device_name", False))
        for device in devices:
            selected_volumes = [v for v in device.volumes if v.key in selected_keys]
            if not selected_volumes:
                continue
            device_node = make_node(f"{device.display_kind}: {device.name}") if output_device_name else None
            for volume in selected_volumes:
                drive_label = volume.label or "無題"
                drive_name = volume.drive.replace(":", "") if volume.drive else volume.mountpoint
                volume_node = make_node(f"{drive_name}: {drive_label}")
                volume_root = Path(volume.mountpoint)
                volume_node["children"] = self._walk(volume_root, depth=0)
                if output_device_name and device_node is not None:
                    device_node["children"].append(volume_node)
                else:
                    root["children"].append(volume_node)
            if output_device_name and device_node is not None:
                root["children"].append(device_node)

        return self._write_km(root, output)

    def export_folder(
        self,
        folder_path: str | Path,
        output_path: str | Path,
        max_depth: int | None = None,
        max_files_per_folder: int | None = None,
    ) -> Path:
        """任意フォルダをルートにして DesktopNaotu 用 .km を出力します。"""
        self.errors.clear()
        self._set_limits(max_depth, max_files_per_folder)
        folder = Path(folder_path)
        if not folder.exists():
            raise FileNotFoundError(f"フォルダが見つかりません: {folder}")
        if not folder.is_dir():
            raise NotADirectoryError(f"フォルダではありません: {folder}")
        root = make_node("DriveMind")
        root_node = make_node(folder.name or str(folder))
        root_node["children"] = self._walk(folder, depth=0)
        root["children"].append(root_node)
        return self._write_km(root, Path(output_path))

    def _set_limits(self, max_depth: int | None, max_files_per_folder: int | None) -> None:
        self.max_depth = max(1, int(max_depth if max_depth is not None else self.config.get("mindmap.max_depth", 48)))
        self.max_files_per_folder = max(0, int(max_files_per_folder if max_files_per_folder is not None else self.config.get("mindmap.max_files_per_folder", 16)))

    def _write_km(self, root: dict, output: Path) -> Path:
        km = {
            "root": root,
            "template": "default",
            "theme": "fresh-blue",
            "version": "1.4.43",
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(km, ensure_ascii=False, indent=2), encoding="utf-8")
        self.config.set("runtime.last_export_path", str(output))
        self.config.save()
        return output

    def _walk(self, folder: Path, depth: int) -> list[dict]:
        if depth >= self.max_depth:
            return []

        exclude_names = set(str(x).lower() for x in self.config.get("mindmap.exclude_names", []))
        include_hidden = bool(self.config.get("mindmap.include_hidden", True))
        mark_hidden = bool(self.config.get("mindmap.mark_hidden", True))
        include_system = bool(self.config.get("mindmap.include_system", False))
        include_files = bool(self.config.get("mindmap.include_files", False))
        include_extensions = bool(self.config.get("mindmap.include_extensions", True))
        include_program_folders = bool(self.config.get("mindmap.include_program_folders", False))
        adobe_project_folder_only = bool(self.config.get("mindmap.adobe_project_folder_only", True))

        nodes: list[dict] = []
        try:
            entries = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            self.errors.append(f"権限不足: {folder}")
            return [make_node("[権限不足]")]
        except FileNotFoundError:
            self.errors.append(f"見つかりません: {folder}")
            return [make_node("[見つかりません]")]
        except OSError as exc:
            self.errors.append(f"読み取り不可: {folder} ({exc})")
            return [make_node("[読み取り不可]")]

        file_count = 0
        skipped_files = 0
        for entry in entries:
            if _matches_exclude(entry.name, exclude_names):
                continue
            flags = path_flags(entry)
            if flags.symlink:
                continue
            if flags.hidden and not include_hidden:
                continue
            if flags.system and not include_system:
                continue
            try:
                if entry.is_dir():
                    adobe_label = _adobe_project_label(entry) if adobe_project_folder_only else None
                    if adobe_label:
                        nodes.append(make_node(adobe_label))
                        continue
                    if not include_program_folders and _looks_like_program_folder(entry):
                        nodes.append(make_node(f"プログラム：{entry.name}"))
                        continue
                    node = make_node(display_name(entry, include_extensions, mark_hidden, flags))
                    node["children"] = self._walk(entry, depth + 1)
                    nodes.append(node)
                elif include_files and entry.is_file():
                    if self.max_files_per_folder and file_count >= self.max_files_per_folder:
                        skipped_files += 1
                        continue
                    file_count += 1
                    nodes.append(make_node(display_name(entry, include_extensions, mark_hidden, flags)))
            except OSError as exc:
                self.errors.append(f"読み取り不可: {entry} ({exc})")
                continue
        if skipped_files:
            nodes.append(make_node(f"[同一フォルダ内のファイル数制限により省略: {skipped_files} 件]"))
        return nodes
