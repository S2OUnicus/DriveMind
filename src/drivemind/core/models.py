from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class VolumeInfo:
    key: str
    drive: str
    mountpoint: str
    label: str = ""
    file_system: str = ""
    total: int = 0
    used: int = 0
    free: int = 0
    percent: float = 0.0
    order_all: int = 0
    order_device: int = 0
    device_index: int = 0
    attributes: list[str] = field(default_factory=list)
    group: str = ""
    purpose: str = ""
    memo: str = ""
    partition_type: str = ""
    selected: bool = False

    @property
    def display_label(self) -> str:
        return self.label or "無題"

    @property
    def usage_tuple(self) -> tuple[int, int, int]:
        return self.used, self.free, self.total


@dataclass(slots=True)
class DeviceInfo:
    index: int
    system_index: int | None = None
    name: str = "不明なディスク"
    model: str = ""
    serial: str = ""
    interface: str = ""
    bus_type: str = ""
    media_type: str = "不明"
    kind: str = "不明"
    is_internal: bool = True
    size: int = 0
    uuid: str = ""
    partition_count: int = 0
    volumes: list[VolumeInfo] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def title(self) -> str:
        side = "内部ドライブ" if self.is_internal else "外部ドライブ"
        media = self.media_type or "不明"
        return f"{self.name}（{media}、{side}、設備: {self.index}）"

    @property
    def display_kind(self) -> str:
        return self.kind or (("内部" if self.is_internal else "外部") + " " + (self.media_type or "不明"))

    @property
    def total_used(self) -> int:
        return sum(v.used for v in self.volumes)

    @property
    def total_free(self) -> int:
        return sum(v.free for v in self.volumes)

    @property
    def total_capacity(self) -> int:
        if self.volumes:
            return sum(v.total for v in self.volumes)
        return int(self.size or 0)


@dataclass(slots=True)
class DiskSnapshot:
    devices: list[DeviceInfo] = field(default_factory=list)
    internal_used: int = 0
    internal_free: int = 0
    internal_total: int = 0
    external_used: int = 0
    external_free: int = 0
    external_total: int = 0
    all_used: int = 0
    all_free: int = 0
    all_total: int = 0
    errors: list[str] = field(default_factory=list)

    @classmethod
    def from_devices(cls, devices: list[DeviceInfo], errors: list[str] | None = None) -> "DiskSnapshot":
        snap = cls(devices=devices, errors=errors or [])
        for device in devices:
            used = device.total_used
            free = device.total_free
            total = device.total_capacity
            snap.all_used += used
            snap.all_free += free
            snap.all_total += total
            if device.is_internal:
                snap.internal_used += used
                snap.internal_free += free
                snap.internal_total += total
            else:
                snap.external_used += used
                snap.external_free += free
                snap.external_total += total
        return snap
