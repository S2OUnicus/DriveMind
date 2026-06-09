from __future__ import annotations

import ctypes
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


class MindmapExporter:
    def __init__(self, config: ConfigManager) -> None:
        self.config = config
        self.errors: list[str] = []

    def export(self, devices: list[DeviceInfo], selected_keys: set[str], output_path: str | Path) -> Path:
        self.errors.clear()
        output = Path(output_path)
        root = make_node("DriveMind")
        for device in devices:
            selected_volumes = [v for v in device.volumes if v.key in selected_keys]
            if not selected_volumes:
                continue
            device_text = f"{device.display_kind}: {device.name}"
            device_node = make_node(device_text)
            for volume in selected_volumes:
                drive_label = volume.label or "無題"
                drive_name = volume.drive.replace(":", "") if volume.drive else volume.mountpoint
                volume_node = make_node(f"{drive_name}: {drive_label}")
                volume_root = Path(volume.mountpoint)
                volume_node["children"] = self._walk(volume_root, depth=0)
                device_node["children"].append(volume_node)
            root["children"].append(device_node)

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
        max_depth = int(self.config.get("mindmap.max_depth", 6) or 6)
        if depth >= max_depth:
            return []

        exclude_names = set(str(x).lower() for x in self.config.get("mindmap.exclude_names", []))
        include_hidden = bool(self.config.get("mindmap.include_hidden", True))
        mark_hidden = bool(self.config.get("mindmap.mark_hidden", True))
        include_system = bool(self.config.get("mindmap.include_system", False))
        include_files = bool(self.config.get("mindmap.include_files", False))
        include_extensions = bool(self.config.get("mindmap.include_extensions", True))

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

        for entry in entries:
            if entry.name.lower() in exclude_names:
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
                    node = make_node(display_name(entry, include_extensions, mark_hidden, flags))
                    node["children"] = self._walk(entry, depth + 1)
                    nodes.append(node)
                elif include_files and entry.is_file():
                    nodes.append(make_node(display_name(entry, include_extensions, mark_hidden, flags)))
            except OSError as exc:
                self.errors.append(f"読み取り不可: {entry} ({exc})")
                continue
        return nodes
