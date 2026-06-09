from __future__ import annotations


def format_bytes(value: int | float, decimals: int = 2) -> str:
    try:
        amount = float(value)
    except Exception:
        amount = 0.0
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    unit_index = 0
    while abs(amount) >= 1024 and unit_index < len(units) - 1:
        amount /= 1024.0
        unit_index += 1
    if unit_index == 0:
        return f"{int(amount)} {units[unit_index]}"
    return f"{amount:.{decimals}f} {units[unit_index]}"


def format_percent(value: float, decimals: int = 2) -> str:
    try:
        return f"{float(value):.{decimals}f} %"
    except Exception:
        return f"{0:.{decimals}f} %"
