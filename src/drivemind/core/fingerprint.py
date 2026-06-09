from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import uuid


def _windows_machine_guid() -> str:
    if os.name != "nt":
        return ""
    try:
        import winreg  # type: ignore

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(value).strip()
    except Exception:
        return ""


def _windows_smbios_uuid() -> str:
    if os.name != "nt":
        return ""
    commands = [
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            "(Get-CimInstance Win32_ComputerSystemProduct).UUID",
        ],
        ["wmic", "csproduct", "get", "uuid"],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
            text = (result.stdout or "").strip()
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line in lines:
                if line.lower() == "uuid":
                    continue
                if len(line) >= 8 and "FFFFFFFF" not in line.upper():
                    return line
        except Exception:
            continue
    return ""


def generate_machine_fingerprint(length: int = 16) -> str:
    """PCごとの設定ファイル名に使う短い識別値を生成します。"""
    parts = [
        _windows_machine_guid(),
        _windows_smbios_uuid(),
        platform.node(),
        platform.system(),
        platform.release(),
    ]
    if not any(parts):
        parts = [platform.node(), str(uuid.getnode())]
    source = "|".join(part for part in parts if part)
    digest = hashlib.sha256(source.encode("utf-8", errors="ignore")).hexdigest()
    return digest[:length]
