from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from drivemind.core.config import ConfigManager
from drivemind.core.disk_scanner import DriveScanner
from drivemind.core.formatting import format_bytes
from drivemind.core.models import DeviceInfo, DiskSnapshot
from drivemind.ui.progress_bar import DiskUsageBar


class InfoDialog(QDialog):
    def __init__(self, snapshot: DiskSnapshot, scanner: DriveScanner, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self.snapshot = snapshot
        self.scanner = scanner
        self.config = config
        self.setWindowTitle("ディスク情報 - DriveMind")
        self.resize(780, 560)

        root = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs, 1)
        self._build_total_tab()
        for device in self.snapshot.devices:
            label = f"{'内部' if device.is_internal else '外部'}{device.index}"
            self.tabs.addTab(self._device_tab(device), label)

        row = QHBoxLayout()
        self.save_button = QPushButton("保存", self)
        self.save_button.clicked.connect(self._save_report)
        close_button = QPushButton("閉じる", self)
        close_button.clicked.connect(self.accept)
        row.addWidget(self.save_button, alignment=Qt.AlignLeft)
        row.addStretch(1)
        row.addWidget(close_button, alignment=Qt.AlignRight)
        root.addLayout(row)

    def _decimals(self) -> tuple[int, int]:
        return int(self.config.get("basic.capacity_decimals", 2)), int(self.config.get("basic.percent_decimals", 2))

    def _build_total_tab(self) -> None:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        decimals, percent_decimals = self._decimals()
        form = QFormLayout()
        form.addRow("すべての容量", QLabel(format_bytes(self.snapshot.all_total, decimals), tab))
        form.addRow("すべての使用済み", QLabel(format_bytes(self.snapshot.all_used, decimals), tab))
        form.addRow("すべての空き容量", QLabel(format_bytes(self.snapshot.all_free, decimals), tab))
        form.addRow("内部ディスク容量", QLabel(format_bytes(self.snapshot.internal_total, decimals), tab))
        form.addRow("外部ディスク容量", QLabel(format_bytes(self.snapshot.external_total, decimals), tab))
        layout.addLayout(form)
        layout.addWidget(QLabel("内部ディスク総計", tab))
        layout.addWidget(DiskUsageBar(self.snapshot.internal_used, self.snapshot.internal_free, self.snapshot.internal_total, decimals, percent_decimals, tab))
        layout.addWidget(QLabel("外部ディスク総計", tab))
        layout.addWidget(DiskUsageBar(self.snapshot.external_used, self.snapshot.external_free, self.snapshot.external_total, decimals, percent_decimals, tab))
        table = QTableWidget(tab)
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["設備", "種類", "インターフェース", "パーティション数", "容量"])
        table.setRowCount(len(self.snapshot.devices))
        for row, device in enumerate(self.snapshot.devices):
            values = [device.name, device.display_kind, device.interface, str(device.partition_count), format_bytes(device.total_capacity, decimals)]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))
        table.resizeColumnsToContents()
        layout.addWidget(table, 1)
        self.tabs.addTab(tab, "総計")

    def _device_tab(self, device: DeviceInfo) -> QWidget:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        decimals, percent_decimals = self._decimals()
        form = QFormLayout()
        form.addRow("ディスク名", QLabel(device.name, tab))
        form.addRow("設備順番", QLabel(str(device.index), tab))
        form.addRow("属性", QLabel(device.display_kind, tab))
        form.addRow("インターフェース", QLabel(device.interface, tab))
        form.addRow("パーティション数", QLabel(str(device.partition_count), tab))
        form.addRow("UUID / Serial", QLabel(device.uuid or "不明", tab))
        layout.addLayout(form)
        layout.addWidget(DiskUsageBar(device.total_used, device.total_free, device.total_capacity, decimals, percent_decimals, tab))

        table = QTableWidget(tab)
        rows = self.scanner.smart_info(device)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["項目", "値"])
        table.setRowCount(len(rows))
        for row, (name, value) in enumerate(rows):
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(value))
        table.resizeColumnsToContents()
        layout.addWidget(QLabel("S.M.A.R.T / 信頼性情報", tab))
        layout.addWidget(table, 1)
        return tab

    def _save_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "ディスク情報を保存", str(Path.home() / "DriveMind_report.txt"), "Text files (*.txt);;All files (*.*)")
        if not path:
            return
        try:
            Path(path).write_text(self._make_report(), encoding="utf-8")
        except Exception as exc:
            QMessageBox.warning(self, "保存失敗", f"レポートを保存できませんでした。\n{exc}")
            return
        QMessageBox.information(self, "保存完了", "ディスク情報レポートを保存しました。")

    def _make_report(self) -> str:
        decimals = int(self.config.get("basic.capacity_decimals", 2))
        lines: list[str] = []
        lines.append("DriveMind ディスク情報レポート")
        lines.append("=" * 40)
        lines.append(f"総容量: {format_bytes(self.snapshot.all_total, decimals)}")
        lines.append(f"使用済み: {format_bytes(self.snapshot.all_used, decimals)}")
        lines.append(f"空き容量: {format_bytes(self.snapshot.all_free, decimals)}")
        lines.append("")
        for device in self.snapshot.devices:
            lines.append(f"[{device.display_kind}] {device.name}")
            lines.append(f"設備順番: {device.index}")
            lines.append(f"インターフェース: {device.interface}")
            lines.append(f"パーティション数: {device.partition_count}")
            lines.append(f"UUID / Serial: {device.uuid or '不明'}")
            lines.append(f"容量: {format_bytes(device.total_capacity, decimals)}")
            for volume in device.volumes:
                lines.append(f"  - {volume.drive} {volume.label} {volume.file_system} 使用済み {format_bytes(volume.used, decimals)} / {format_bytes(volume.total, decimals)}")
            lines.append("S.M.A.R.T / 信頼性情報:")
            for name, value in self.scanner.smart_info(device):
                lines.append(f"  {name}: {value}")
            lines.append("")
        if self.snapshot.errors:
            lines.append("取得時の注意:")
            for error in self.snapshot.errors:
                lines.append(f"- {error}")
        return "\n".join(lines)
