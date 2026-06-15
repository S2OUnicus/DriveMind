from __future__ import annotations

import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import psutil

from .config import ConfigManager
from .models import DeviceInfo, DiskSnapshot, VolumeInfo


DRIVE_RE = re.compile(r'DeviceID="([A-Z]:)"', re.IGNORECASE)
PARTITION_RE = re.compile(r'DeviceID="([^"]+)"', re.IGNORECASE)


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _windows_subprocess_kwargs() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = 0
    return {
        "startupinfo": startupinfo,
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
    }


def _powershell_json(script: str, timeout: int = 10) -> dict[str, Any]:
    """PowerShell を JSON 取得用に実行します。

    非管理者環境では Get-Disk / Get-PhysicalDisk などが遅延・失敗する場合があります。
    ここで例外を外へ出すと、GUI 起動時にディスクリスト全体が空になるため、
    失敗時は空 dict を返し、psutil ベースの取得へフォールバックさせます。
    """
    if os.name != "nt":
        return {}
    command = [
        "powershell",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            **_windows_subprocess_kwargs(),
        )
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return {}
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    try:
        data = json.loads(result.stdout)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _volume_label_and_fs(root: str) -> tuple[str, str, list[str]]:
    """Windowsのボリュームラベルとファイルシステムを取得します。"""
    attrs: list[str] = []
    if os.name != "nt":
        return "", "", attrs
    try:
        volume_name = ctypes.create_unicode_buffer(261)
        fs_name = ctypes.create_unicode_buffer(261)
        serial = ctypes.c_ulong()
        max_component_len = ctypes.c_ulong()
        flags = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetVolumeInformationW(  # type: ignore[attr-defined]
            ctypes.c_wchar_p(root),
            volume_name,
            ctypes.sizeof(volume_name),
            ctypes.byref(serial),
            ctypes.byref(max_component_len),
            ctypes.byref(flags),
            fs_name,
            ctypes.sizeof(fs_name),
        )
        if ok:
            if flags.value & 0x00080000:
                attrs.append("RO")
            return volume_name.value, fs_name.value, attrs
    except Exception:
        pass
    return "", "", attrs


def _windows_disk_inventory() -> tuple[
    dict[int, dict[str, Any]],
    dict[str, int],
    dict[int, int],
    dict[int, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    set[int],
]:
    """Windowsの物理ディスクと論理ドライブの対応を取得します。

    まず Get-Disk / Get-Partition / Get-Volume の対応情報を使います。
    それが取れない環境では Win32_LogicalDiskToPartition を補助として使います。
    """
    script = r'''
$ErrorActionPreference = 'SilentlyContinue'
$disks = Get-Disk | Select-Object Number,FriendlyName,SerialNumber,BusType,MediaType,Size,UniqueId,IsBoot,IsSystem,IsReadOnly,IsOffline,PartitionStyle
$win32 = Get-CimInstance Win32_DiskDrive | Select-Object Index,Model,SerialNumber,InterfaceType,MediaType,Size,PNPDeviceID
$parts = Get-Partition | Select-Object DiskNumber,PartitionNumber,DriveLetter,Type,GptType,MbrType,IsBoot,IsSystem,IsReadOnly,IsHidden,IsOffline,Size
$volumes = @()
foreach ($p in (Get-Partition)) {
  if ($p.DriveLetter) {
    $v = $null
    try { $v = $p | Get-Volume } catch {}
    $volumes += [PSCustomObject]@{
      Drive = ([string]$p.DriveLetter + ':')
      DiskNumber = $p.DiskNumber
      PartitionNumber = $p.PartitionNumber
      FileSystem = if ($v) { $v.FileSystem } else { '' }
      Label = if ($v) { $v.FileSystemLabel } else { '' }
      Type = $p.Type
      GptType = $p.GptType
      MbrType = $p.MbrType
      IsBoot = $p.IsBoot
      IsSystem = $p.IsSystem
      IsReadOnly = $p.IsReadOnly
      IsHidden = $p.IsHidden
      IsOffline = $p.IsOffline
      Size = $p.Size
    }
  }
}
$links = Get-CimInstance Win32_LogicalDiskToPartition | Select-Object Antecedent,Dependent
$physical = Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,SerialNumber,MediaType,BusType,Size
$logical = Get-CimInstance Win32_LogicalDisk | Select-Object DeviceID,DriveType,ProviderName,VolumeName,FileSystem
$bitlocker = @()
try {
  if (Get-Command Get-BitLockerVolume -ErrorAction SilentlyContinue) {
    $bitlocker = Get-BitLockerVolume | ForEach-Object {
      [PSCustomObject]@{
        MountPoint = $_.MountPoint
        VolumeStatus = if ($null -ne $_.VolumeStatus) { $_.VolumeStatus.ToString() } else { '' }
        ProtectionStatus = if ($null -ne $_.ProtectionStatus) { $_.ProtectionStatus.ToString() } else { '' }
        LockStatus = if ($null -ne $_.LockStatus) { $_.LockStatus.ToString() } else { '' }
        EncryptionPercentage = $_.EncryptionPercentage
      }
    }
  }
} catch {}
[PSCustomObject]@{Disks=$disks;Win32=$win32;Partitions=$parts;Volumes=$volumes;Links=$links;Physical=$physical;Logical=$logical;BitLocker=$bitlocker} | ConvertTo-Json -Depth 8 -Compress
'''
    data = _powershell_json(script)
    disks_by_index: dict[int, dict[str, Any]] = {}
    drive_to_disk: dict[str, int] = {}
    partition_counts: dict[int, int] = {}
    physical_by_index: dict[int, dict[str, Any]] = {}
    volume_meta: dict[str, dict[str, Any]] = {}
    logical_meta: dict[str, dict[str, Any]] = {}
    bitlocker_meta: dict[str, dict[str, Any]] = {}
    system_disks: set[int] = set()

    # Get-Disk を優先します。Number は Get-Partition の DiskNumber と対応します。
    for disk in _ensure_list(data.get("Disks")):
        try:
            idx = int(disk.get("Number"))
        except Exception:
            continue
        disks_by_index[idx] = dict(disk)
        if bool(disk.get("IsBoot")) or bool(disk.get("IsSystem")):
            system_disks.add(idx)

    # Win32_DiskDrive の情報を補助情報として統合します。
    for disk in _ensure_list(data.get("Win32")):
        try:
            idx = int(disk.get("Index"))
        except Exception:
            continue
        existing = disks_by_index.setdefault(idx, {})
        for key, value in dict(disk).items():
            existing.setdefault(key, value)

    for part in _ensure_list(data.get("Partitions")):
        try:
            disk_idx = int(part.get("DiskNumber"))
        except Exception:
            continue
        partition_counts[disk_idx] = partition_counts.get(disk_idx, 0) + 1
        if bool(part.get("IsBoot")) or bool(part.get("IsSystem")):
            system_disks.add(disk_idx)

    for volume in _ensure_list(data.get("Volumes")):
        drive = str(volume.get("Drive", "")).upper().strip()
        if not drive:
            continue
        try:
            disk_idx = int(volume.get("DiskNumber"))
        except Exception:
            continue
        drive_to_disk[drive] = disk_idx
        volume_meta[drive] = dict(volume)
        if bool(volume.get("IsBoot")) or bool(volume.get("IsSystem")):
            system_disks.add(disk_idx)

    # Get-Partition が失敗した場合の補助対応。
    for link in _ensure_list(data.get("Links")):
        dep = str(link.get("Dependent", ""))
        ant = str(link.get("Antecedent", ""))
        drive_match = DRIVE_RE.search(dep)
        part_match = PARTITION_RE.search(ant)
        if not drive_match or not part_match:
            continue
        drive = drive_match.group(1).upper()
        partition_device_id = part_match.group(1)
        disk_match = re.search(r"Disk #([0-9]+)", partition_device_id, re.IGNORECASE)
        if disk_match:
            drive_to_disk.setdefault(drive, int(disk_match.group(1)))

    for physical in _ensure_list(data.get("Physical")):
        try:
            idx = int(str(physical.get("DeviceId", "")))
        except Exception:
            continue
        physical_by_index[idx] = dict(physical)

    for logical in _ensure_list(data.get("Logical")):
        drive = str(logical.get("DeviceID", "")).upper().strip()
        if drive:
            logical_meta[drive] = dict(logical)


    for bl in _ensure_list(data.get("BitLocker")):
        mount = str(bl.get("MountPoint", "")).upper().strip()
        if mount.endswith("\\"):
            mount = mount[:-1]
        if mount and len(mount) >= 2 and mount[1] == ":":
            bitlocker_meta[mount[:2]] = dict(bl)

    # OSのSystemDriveが分かる場合は、そのドライブを含むディスクをシステムディスクとして扱います。
    system_drive = os.environ.get("SystemDrive", "").upper().strip()
    if system_drive in drive_to_disk:
        system_disks.add(drive_to_disk[system_drive])

    return disks_by_index, drive_to_disk, partition_counts, physical_by_index, volume_meta, logical_meta, bitlocker_meta, system_disks


def _normalize_media_type(*values: str) -> str:
    text = " ".join(v for v in values if v).lower()
    if "ssd" in text or "solid" in text:
        return "SSD"
    if "hdd" in text or "hard" in text or "磁気" in text:
        return "HDD"
    if "scm" in text:
        return "SCM"
    return "不明"


def _is_external(interface: str, bus_type: str, pnp: str) -> bool:
    text = f" {interface} {bus_type} {pnp} ".lower()
    compact = text.replace("-", " ").replace("_", " ")
    if any(token in compact for token in [" usb", " 1394", "firewire", "thunderbolt"]):
        return True
    return bus_type.strip().lower() in {"usb", "sd", "mmc", "1394"}


def _interface_label(interface: str, bus_type: str) -> str:
    bus = (bus_type or "").strip()
    iface = (interface or "").strip()
    if bus.lower() in {"nvme", "raid"}:
        return "M.2 / NVMe" if bus.lower() == "nvme" else bus
    if bus:
        return bus
    if iface:
        return iface
    return "不明"


def _bool_meta(meta: dict[str, Any], key: str) -> bool:
    return str(meta.get(key, "")).lower() == "true" or meta.get(key) is True


def _partition_kind(meta: dict[str, Any]) -> str:
    text = f"{meta.get('Type', '')} {meta.get('GptType', '')} {meta.get('MbrType', '')}".lower()
    if "system" in text or "c12a7328-f81f-11d2-ba4b-00a0c93ec93b" in text:
        return "ESP"
    if "reserved" in text or "e3c9e316-0b5c-4db8-817d-f92df00215ae" in text:
        return "MSR"
    if "oem" in text or "de94bba4-06d1-4d40-a16a-bfd50179d6ac" in text:
        return "OEM"
    if "basic" in text:
        return "Basic"
    return str(meta.get("Type") or meta.get("GptType") or meta.get("MbrType") or "").strip()


def _is_ram_disk_label(label: str) -> bool:
    text = label.lower().replace(" ", "")
    return any(token in text for token in ["ramcache", "ramdisk", "ramdrive"])


def _is_web_disk_label(label: str, provider: str = "") -> bool:
    text = f"{label} {provider}".lower()
    tokens = ["google drive", "googledrive", "onedrive", "dropbox", "webdav", "webdrv", "web disk", "webdisk", "icloud drive"]
    return any(token in text for token in tokens)


def _should_show_partition(config: ConfigManager, partition_kind: str, attributes: list[str], label: str, logical: dict[str, Any]) -> bool:
    kind = (partition_kind or "").upper()
    if kind == "ESP" and not bool(config.get("basic.show_esp_partitions", False)):
        return False
    if kind == "MSR" and not bool(config.get("basic.show_msr_partitions", False)):
        return False
    if kind == "OEM" and not bool(config.get("basic.show_oem_partitions", False)):
        return False
    upper_attrs = {a.upper() for a in attributes}
    if "RO" in upper_attrs and not bool(config.get("basic.show_readonly_partitions", True)):
        return False
    if "H" in upper_attrs and not bool(config.get("basic.show_hidden_partitions", False)):
        return False
    provider = str(logical.get("ProviderName") or "")
    drive_type = str(logical.get("DriveType") or "")
    if _is_ram_disk_label(label) and not bool(config.get("basic.show_ram_disks", False)):
        return False
    if _is_web_disk_label(label, provider) and not bool(config.get("basic.show_web_disks", False)):
        return False
    # Win32_LogicalDisk DriveType=4 はネットワークドライブです。
    if drive_type == "4" and not bool(config.get("basic.show_remote_disks", False)):
        return False
    return True


def _ntfs_version(drive: str) -> str:
    """NTFS の詳細バージョンを取得します。取得できない場合は空文字です。"""
    if os.name != "nt" or not drive:
        return ""
    target = drive if drive.endswith(":") else drive[:2]
    try:
        result = subprocess.run(
            ["fsutil", "fsinfo", "ntfsinfo", target],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
            **_windows_subprocess_kwargs(),
        )
        text = (result.stdout or "") + "\n" + (result.stderr or "")
        match = re.search(r"NTFS\s+Version\s*[:：]\s*([0-9.]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    except Exception:
        return ""
    return ""


def _bitlocker_icon(meta: dict[str, Any], device: DeviceInfo | None = None) -> str:
    """ファイルシステム列に付ける状態アイコンを決めます。

    Get-BitLockerVolume は BitLocker 未使用の通常ボリュームも返す場合があります。
    そのため meta が存在するだけで BitLocker 使用中とは判断しません。
    """
    if meta:
        volume_status = str(meta.get("VolumeStatus", "")).strip().lower()
        protection_status = str(meta.get("ProtectionStatus", "")).strip().lower()
        lock_status = str(meta.get("LockStatus", "")).strip().lower()
        try:
            encryption = float(str(meta.get("EncryptionPercentage", "0") or 0))
        except Exception:
            encryption = 0.0

        fully_decrypted = volume_status in {"fullydecrypted", "fully decrypted", "0"}
        protection_off = protection_status in {"off", "0", "false", ""}
        unlocked_words = {"unlocked", "0", "false", ""}
        locked = lock_status in {"locked", "1", "true"}

        encrypted_statuses = {
            "fullyencrypted",
            "fully encrypted",
            "encryptioninprogress",
            "encryption in progress",
            "decryptioninprogress",
            "decryption in progress",
            "encryptionsuspended",
            "encryption suspended",
            "wipedencryptioninprogress",
            "wipe encryption in progress",
        }
        bitlocker_used = (
            locked
            or protection_status in {"on", "1", "true"}
            or encryption > 0
            or volume_status in encrypted_statuses
        )
        if bitlocker_used:
            return "🔐" if locked else "🔓"

    if device is not None and device.is_internal:
        return "💾"
    return "💿"


def _display_file_system(base_fs: str, drive: str, device: DeviceInfo, bitlocker: dict[str, Any]) -> str:
    fs = (base_fs or "").strip()
    if not fs:
        return ""
    fs_upper = fs.upper()
    if fs_upper == "NTFS":
        version = _ntfs_version(drive)
        if version:
            fs = f"NTFS {version}"
    return f"{_bitlocker_icon(bitlocker, device)} {fs}".strip()


class DriveScanner:
    def __init__(self, config: ConfigManager) -> None:
        self.config = config

    def scan(self) -> DiskSnapshot:
        errors: list[str] = []
        try:
            if os.name == "nt":
                devices = self._scan_windows(errors)
            else:
                devices = self._scan_portable(errors)
        except Exception as exc:
            errors.append(f"ディスク情報の取得中にエラーが発生しました: {exc}")
            devices = []
        return DiskSnapshot.from_devices(devices, errors)

    def _scan_windows(self, errors: list[str]) -> list[DeviceInfo]:
        (
            disks_by_system_index,
            drive_to_disk,
            partition_counts,
            physical_by_index,
            volume_meta,
            logical_meta,
            bitlocker_meta,
            system_disks,
        ) = _windows_disk_inventory()
        device_map: dict[int, DeviceInfo] = {}
        system_to_display: dict[int, int] = {}
        treat_system_disk_as_internal = bool(self.config.get("basic.treat_system_disk_as_internal", True))

        for display_index, system_index in enumerate(sorted(disks_by_system_index.keys()), start=1):
            raw = disks_by_system_index[system_index]
            physical = physical_by_index.get(system_index, {})
            model = str(raw.get("FriendlyName") or raw.get("Model") or physical.get("FriendlyName") or "").strip()
            name = model or f"Disk {system_index}"
            interface = str(raw.get("InterfaceType") or "").strip()
            bus_type = str(raw.get("BusType") or physical.get("BusType") or "").strip()
            media_type = _normalize_media_type(str(raw.get("MediaType") or physical.get("MediaType") or ""), model)
            pnp = str(raw.get("PNPDeviceID") or raw.get("UniqueId") or "")
            external = _is_external(interface, bus_type, pnp)
            if treat_system_disk_as_internal and system_index in system_disks:
                external = False
            kind = ("外部" if external else "内部") + " " + media_type
            serial = str(raw.get("SerialNumber") or physical.get("SerialNumber") or "").strip()
            try:
                size = int(raw.get("Size") or physical.get("Size") or 0)
            except Exception:
                size = 0
            attrs: list[str] = []
            if _bool_meta(raw, "IsReadOnly"):
                attrs.append("RO")
            if _bool_meta(raw, "IsOffline"):
                attrs.append("Offline")
            device = DeviceInfo(
                index=display_index,
                system_index=system_index,
                name=name,
                model=model,
                serial=serial,
                interface=_interface_label(interface, bus_type),
                bus_type=bus_type or interface,
                media_type=media_type,
                kind=kind,
                is_internal=not external,
                size=size,
                uuid=serial or str(raw.get("UniqueId") or raw.get("PNPDeviceID") or ""),
                partition_count=partition_counts.get(system_index, 0),
                attributes=attrs,
                raw={"disk": raw, "physical": physical},
            )
            override = self.config.settings.get("device_overrides", {}).get(device.device_key, {})
            if "is_internal" in override:
                device.is_internal = bool(override.get("is_internal"))
                device.kind = ("内部" if device.is_internal else "外部") + " " + media_type
            device_map[display_index] = device
            system_to_display[system_index] = display_index

        partitions = psutil.disk_partitions(all=False)
        if not partitions:
            # 非管理者環境や一部の仮想環境では all=False が空になる場合があります。
            # その場合は all=True で再取得し、後続の設定フィルターで不要な項目を除外します。
            partitions = psutil.disk_partitions(all=True)
        order_all = 0
        per_device_count: dict[int, int] = {}
        unknown_display_index: int | None = None
        for partition in partitions:
            mount = partition.mountpoint
            if not mount:
                continue
            drive = mount[:2].upper() if len(mount) >= 2 and mount[1] == ":" else partition.device.rstrip("\\/")
            try:
                usage = psutil.disk_usage(mount)
            except PermissionError:
                errors.append(f"権限不足のため使用状況を取得できません: {mount}")
                continue
            except OSError as exc:
                errors.append(f"使用状況を取得できません: {mount} ({exc})")
                continue

            system_index = drive_to_disk.get(drive)
            display_index = system_to_display.get(system_index) if system_index is not None else None
            if display_index is None:
                # 対応関係が取れない環境では、パーティションごとに未知ディスクを増やさず、
                # まとめて「未識別ディスク」に入れます。
                if unknown_display_index is None:
                    unknown_display_index = max(device_map.keys(), default=0) + 1
                    fallback = DeviceInfo(index=unknown_display_index, system_index=None, name="未識別ディスク", interface="不明", media_type="不明", kind="内部 不明", is_internal=True)
                    device_map[unknown_display_index] = fallback
                display_index = unknown_display_index

            device = device_map[display_index]
            label, fs_name, volume_attrs = _volume_label_and_fs(mount)
            meta = volume_meta.get(drive, {})
            logical = logical_meta.get(drive, {})
            label = label or str(meta.get("Label") or logical.get("VolumeName") or "")
            base_fstype = partition.fstype or fs_name or str(meta.get("FileSystem") or logical.get("FileSystem") or "")
            fstype = _display_file_system(base_fstype, drive, device, bitlocker_meta.get(drive, {}))
            partition_kind = _partition_kind(meta)
            attributes = list(dict.fromkeys(volume_attrs))
            opts = (partition.opts or "").lower()
            if "ro" in opts or _bool_meta(meta, "IsReadOnly"):
                attributes.append("RO")
            if _bool_meta(meta, "IsHidden"):
                attributes.append("H")
            if _bool_meta(meta, "IsOffline"):
                attributes.append("Offline")
            if partition_kind in {"ESP", "MSR", "OEM"}:
                attributes.append(partition_kind)
            if str(meta.get("Type") or "").lower() == "reserved":
                attributes.append("Reserved")
            if str(logical.get("DriveType") or "") == "4":
                attributes.append("Remote")
            if _is_ram_disk_label(label):
                attributes.append("RAM")
            if _is_web_disk_label(label, str(logical.get("ProviderName") or "")):
                attributes.append("Web")
            attributes = list(dict.fromkeys(attributes))
            if not _should_show_partition(self.config, partition_kind, attributes, label, logical):
                continue
            order_all += 1
            per_device_count[display_index] = per_device_count.get(display_index, 0) + 1

            key = drive or mount
            note = self.config.drive_note(key)
            volume = VolumeInfo(
                key=key,
                drive=drive,
                mountpoint=mount,
                label=label,
                file_system=fstype,
                total=int(usage.total),
                used=int(usage.used),
                free=int(usage.free),
                percent=float(usage.percent),
                order_all=order_all,
                order_device=per_device_count[display_index],
                device_index=display_index,
                attributes=list(dict.fromkeys(attributes)),
                group=str(note.get("group", "")),
                purpose=str(note.get("purpose", "")),
                memo=str(note.get("memo", "")),
                partition_type=partition_kind,
                selected=bool(note.get("selected", False)),
            )
            device.volumes.append(volume)

        devices = [device_map[key] for key in sorted(device_map.keys())]
        if not bool(self.config.get("basic.show_small_unidentified_disks", False)):
            devices = [
                device
                for device in devices
                if not (device.name == "未識別ディスク" and device.total_capacity <= 1024 * 1024)
            ]
        return devices

    def _scan_portable(self, errors: list[str]) -> list[DeviceInfo]:
        """Windows以外で開発画面を確認するための簡易取得です。"""
        devices: list[DeviceInfo] = []
        roots: list[Path] = [Path("/")]
        if sys.platform == "darwin":
            roots.extend(Path("/Volumes").glob("*"))
        order_all = 0
        device = DeviceInfo(index=1, name="Local Disk", interface="不明", media_type="不明", kind="内部 不明", is_internal=True)
        for root in roots:
            try:
                usage = shutil.disk_usage(root)
            except Exception as exc:
                errors.append(f"使用状況を取得できません: {root} ({exc})")
                continue
            order_all += 1
            key = str(root)
            note = self.config.drive_note(key)
            device.volumes.append(
                VolumeInfo(
                    key=key,
                    drive=str(root),
                    mountpoint=str(root),
                    label=root.name or str(root),
                    file_system="",
                    total=usage.total,
                    used=usage.used,
                    free=usage.free,
                    percent=(usage.used / usage.total * 100) if usage.total else 0,
                    order_all=order_all,
                    order_device=order_all,
                    device_index=1,
                    group=str(note.get("group", "")),
                    purpose=str(note.get("purpose", "")),
                    memo=str(note.get("memo", "")),
                    selected=bool(note.get("selected", False)),
                )
            )
        devices.append(device)
        return devices

    def smart_info_data(self, device: DeviceInfo) -> dict[str, Any]:
        """S.M.A.R.T / 信頼性情報の生データを取得します。

        UI 側では CimClass などの key-value 構造をツリー表示できるよう、
        ここでは dict のまま返します。
        """
        if os.name != "nt" or device.system_index is None:
            return {"状態": "この環境ではS.M.A.R.T情報を取得できません"}
        script = rf'''
$ErrorActionPreference = 'SilentlyContinue'
$pd = Get-PhysicalDisk | Where-Object {{$_.DeviceId -eq {device.system_index}}}
if ($pd) {{
  $rel = $pd | Get-StorageReliabilityCounter
  $rel | Select-Object * | ConvertTo-Json -Depth 8 -Compress
}}
'''
        data = _powershell_json(script, timeout=8)
        if not data:
            return {"状態": "S.M.A.R.T情報を取得できませんでした。管理者権限や対応デバイスが必要な場合があります。"}
        return data

    def smart_info(self, device: DeviceInfo) -> list[tuple[str, str]]:
        data = self.smart_info_data(device)
        labels = {
            "Temperature": "温度",
            "TemperatureMax": "最高温度",
            "PowerOnHours": "電源投入時間",
            "ReadErrorsTotal": "読み取りエラー総数",
            "WriteErrorsTotal": "書き込みエラー総数",
            "Wear": "消耗率",
            "DeviceId": "設備ID",
        }
        rows: list[tuple[str, str]] = []

        def add_flat(prefix: str, value: Any) -> None:
            if value is None or str(value) == "":
                return
            if isinstance(value, dict):
                for child_key, child_value in value.items():
                    add_flat(f"{prefix} > {child_key}", child_value)
            elif isinstance(value, list):
                for i, child_value in enumerate(value, start=1):
                    add_flat(f"{prefix} > {i}", child_value)
            else:
                rows.append((prefix, str(value)))

        for key, value in data.items():
            name = labels.get(key, key)
            add_flat(name, value)
        return rows or [("状態", "表示できるS.M.A.R.T項目がありません")]
