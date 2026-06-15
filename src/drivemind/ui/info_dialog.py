from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from drivemind.core.config import ConfigManager
from drivemind.core.disk_scanner import DriveScanner
from drivemind.core.formatting import format_bytes
from drivemind.core.models import DeviceInfo, DiskSnapshot
from drivemind.ui.progress_bar import DiskUsageBar
from drivemind.ui.partition_info_dialog import PartitionInfoDialog, _open_path, _show_system_file_properties


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

    def _uuid_widget(self, device: DeviceInfo) -> QWidget:
        widget = QWidget(self)
        row = QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        always_show = bool(self.config.get("basic.always_show_uuid", False))
        label = QLabel(device.uuid or "不明", widget) if always_show else QLabel("……", widget)
        row.addWidget(label, 1)
        if not always_show:
            button = QPushButton("UUIDを表す", widget)
            button.clicked.connect(lambda: label.setText(device.uuid or "不明"))
            row.addWidget(button, 0)
        return widget

    def _partition_buttons_widget(self, device: DeviceInfo) -> QWidget:
        wrapper = QWidget(self)
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(0, 0, 0, 0)
        if not device.volumes:
            outer.addWidget(QLabel("ドライブなし", wrapper))
            return wrapper

        scroll = QScrollArea(wrapper)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedHeight(120)
        inner = QWidget(scroll)
        grid = QGridLayout(inner)
        grid.setContentsMargins(2, 2, 2, 2)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        for i, volume in enumerate(device.volumes):
            row = i // 6
            col = i % 6
            page_col = col + (i // 18) * 6
            button_text = volume.drive or volume.label or volume.mountpoint
            if volume.label:
                button_text = f"{volume.drive} ({volume.label})"
            button = QPushButton(button_text, inner)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet("QPushButton { border-radius: 9px; padding: 5px 10px; }")
            button.clicked.connect(lambda checked=False, volume=volume: self._open_volume(volume))
            button.setContextMenuPolicy(Qt.CustomContextMenu)
            button.customContextMenuRequested.connect(lambda pos, button=button, volume=volume: self._show_volume_button_menu(button, volume, pos))
            grid.addWidget(button, row % 3, page_col)

        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return wrapper

    def _open_volume(self, volume) -> None:
        target = volume.mountpoint or (volume.drive + "\\")
        try:
            _open_path(target)
        except Exception as exc:
            QMessageBox.warning(self, "起動失敗", f"ドライブを開けませんでした。\n{target}\n\n{exc}")

    def _show_volume_button_menu(self, button: QPushButton, volume, pos) -> None:
        menu = QMenu(self)
        open_action = menu.addAction("ドライブを開く")
        app_prop_action = menu.addAction("ドライブ属性")
        sys_prop_action = menu.addAction("システム属性")
        chosen = menu.exec(button.mapToGlobal(pos))
        if chosen == open_action:
            self._open_volume(volume)
        elif chosen == app_prop_action:
            PartitionInfoDialog(self._device_for_volume(volume), volume, self.config, self).exec()
        elif chosen == sys_prop_action:
            target = volume.mountpoint or (volume.drive + "\\")
            try:
                _show_system_file_properties(target)
            except Exception as exc:
                QMessageBox.warning(self, "表示失敗", f"システム属性を表示できませんでした。\n{target}\n\n{exc}")

    def _device_for_volume(self, volume) -> DeviceInfo:
        for device in self.snapshot.devices:
            if volume in device.volumes:
                return device
        return self.snapshot.devices[0] if self.snapshot.devices else DeviceInfo(index=0)

    def _add_tree_value(self, parent: QTreeWidgetItem, key: str, value) -> None:
        labels = {
            "Temperature": "温度",
            "TemperatureMax": "最高温度",
            "PowerOnHours": "電源投入時間",
            "ReadErrorsTotal": "読み取りエラー総数",
            "WriteErrorsTotal": "書き込みエラー総数",
            "Wear": "消耗率",
            "DeviceId": "設備ID",
        }
        name = labels.get(str(key), str(key))
        if isinstance(value, dict):
            item = QTreeWidgetItem([name, ""])
            parent.addChild(item)
            for child_key, child_value in value.items():
                self._add_tree_value(item, str(child_key), child_value)
            item.setExpanded(str(key).startswith("Cim"))
        elif isinstance(value, list):
            item = QTreeWidgetItem([name, ""])
            parent.addChild(item)
            for i, child_value in enumerate(value, start=1):
                self._add_tree_value(item, str(i), child_value)
            item.setExpanded(str(key).startswith("Cim"))
        else:
            parent.addChild(QTreeWidgetItem([name, "" if value is None else str(value)]))

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
        form.addRow("ドライブ", self._partition_buttons_widget(device))
        form.addRow("UUID / Serial", self._uuid_widget(device))
        layout.addLayout(form)
        layout.addWidget(DiskUsageBar(device.total_used, device.total_free, device.total_capacity, decimals, percent_decimals, tab))

        tree = QTreeWidget(tab)
        tree.setColumnCount(2)
        tree.setHeaderLabels(["項目", "値"])
        data = self.scanner.smart_info_data(device)
        root_item = tree.invisibleRootItem()
        if isinstance(data, dict):
            for key, value in data.items():
                self._add_tree_value(root_item, str(key), value)
        else:
            self._add_tree_value(root_item, "状態", data)
        tree.resizeColumnToContents(0)
        layout.addWidget(QLabel("S.M.A.R.T / 信頼性情報", tab))
        layout.addWidget(tree, 1)
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
            uuid_text = (device.uuid or '不明') if bool(self.config.get("basic.always_show_uuid", False)) else '……'
            lines.append(f"UUID / Serial: {uuid_text}")
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
