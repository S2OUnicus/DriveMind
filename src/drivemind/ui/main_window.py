from __future__ import annotations

import base64
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from PySide6.QtCore import QByteArray, QDate, QObject, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QFrame,
    QSpinBox,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from drivemind.core.config import ConfigManager
from drivemind.core.disk_scanner import DriveScanner
from drivemind.core.mindmap import MindmapExporter
from drivemind.core.models import DeviceInfo, DiskSnapshot, VolumeInfo
from drivemind.core.update_checker import UpdateResult, check_latest_release, should_check_update, today_iso
from drivemind.version import APP_TITLE, GITHUB_RELEASES_URL, __version__
from drivemind.ui.info_dialog import InfoDialog
from drivemind.ui.partition_info_dialog import PartitionInfoDialog
from drivemind.ui.progress_bar import DiskUsageBar
from drivemind.ui.settings_dialog import SettingsDialog
from drivemind.ui.widgets import LongPressButton


class UpdateWorker(QObject):
    finished = Signal(object)

    def run(self) -> None:
        self.finished.emit(check_latest_release())


class RefreshWorker(QObject):
    finished = Signal(object)

    def __init__(self, config: ConfigManager) -> None:
        super().__init__()
        self.config = config

    def run(self) -> None:
        # Windows のディスク取得は時間がかかる場合があるため、GUI スレッドから分離します。
        scanner = DriveScanner(self.config)
        self.finished.emit(scanner.scan())


class MindmapExportOptionsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("マインドマップ出力設定")
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.max_depth_spin = QSpinBox(self)
        self.max_depth_spin.setRange(1, 128)
        self.max_depth_spin.setValue(int(config.get("mindmap.max_depth", 48)))
        form.addRow("フォルダ最大階層", self.max_depth_spin)

        self.max_files_spin = QSpinBox(self)
        self.max_files_spin.setRange(0, 10000)
        self.max_files_spin.setSpecialValueText("制限しない")
        self.max_files_spin.setValue(int(config.get("mindmap.max_files_per_folder", 16)))
        form.addRow("同一フォルダ内の最大ファイル数", self.max_files_spin)

        note = QLabel("この設定は今回の出力だけに使います。初期値は 設定 > マインドマップ で変更できます。", self)
        note.setWordWrap(True)
        root.addWidget(note)
        root.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.button(QDialogButtonBox.Ok).setText("続行")
        buttons.button(QDialogButtonBox.Cancel).setText("キャンセル")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @property
    def max_depth(self) -> int:
        return self.max_depth_spin.value()

    @property
    def max_files_per_folder(self) -> int:
        return self.max_files_spin.value()


class MainWindow(QMainWindow):
    COL_SELECT = 0
    COL_ORDER = 1
    COL_DRIVE = 2
    COL_GROUP = 3
    COL_PURPOSE = 4
    COL_KIND = 5
    COL_MEMO = 6
    COL_FS = 7
    COL_USAGE = 8
    COL_ATTR = 9

    HEADERS = [
        "選択",
        "順番",
        "ドライブ（ラベル）",
        "グループ",
        "用途",
        "種類",
        "メモ",
        "ファイルシステム",
        "使用状況",
        "属性",
    ]

    SORTABLE_COLUMNS = {COL_ORDER, COL_DRIVE, COL_GROUP, COL_KIND, COL_USAGE}

    def __init__(self) -> None:
        super().__init__()
        self.config = ConfigManager()
        self.scanner = DriveScanner(self.config)
        self.snapshot = DiskSnapshot()
        self.volume_by_key: dict[str, VolumeInfo] = {}
        self.device_by_index: dict[int, DeviceInfo] = {}
        self._loading = False
        self._refreshing = False
        self._refresh_thread: QThread | None = None
        self._refresh_worker: RefreshWorker | None = None
        self._update_thread: QThread | None = None
        self._update_worker: UpdateWorker | None = None
        self._sort_column = int(self.config.get("ui.sort_column", self.COL_DRIVE))
        if self._sort_column not in self.SORTABLE_COLUMNS:
            self._sort_column = self.COL_DRIVE
        self._sort_desc = bool(self.config.get("ui.sort_desc", False))

        self.setWindowTitle(f"{APP_TITLE} v{__version__}")
        self.resize(1280, 760)
        self._build_ui()
        self._restore_header_state()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_disks)
        self._reset_refresh_timer()

        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.config.save)
        self.autosave_timer.start(int(self.config.get("basic.autosave_minutes", 5)) * 60 * 1000)

        QTimer.singleShot(100, self.refresh_disks)
        QTimer.singleShot(1500, self._maybe_startup_update_check)

    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)
        splitter = QSplitter(Qt.Vertical, central)
        root.addWidget(splitter, 1)
        self.setCentralWidget(central)

        self.tree = QTreeWidget(splitter)
        self.tree.setColumnCount(len(self.HEADERS))
        self.tree.setHeaderLabels(self.HEADERS)
        self.tree.setAlternatingRowColors(True)
        self.tree.setRootIsDecorated(True)
        # 展開アイコンのインデントを「ドライブ」列へ移し、チェックボックス列を一番左に固定します。
        self.tree.setTreePosition(self.COL_DRIVE)
        self.tree.setIndentation(18)
        self.tree.setUniformRowHeights(False)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        header = self.tree.header()
        header.setSectionsMovable(True)
        header.setStretchLastSection(False)
        header.sectionClicked.connect(self._on_header_clicked)
        header.setSortIndicatorShown(True)
        for col in range(len(self.HEADERS)):
            header.setSectionResizeMode(col, QHeaderView.Interactive)
        self._apply_default_column_widths()
        self._update_sort_indicator()
        splitter.addWidget(self.tree)

        bottom = QWidget(splitter)
        bottom_layout = QVBoxLayout(bottom)

        summary_row = QHBoxLayout()
        bars_box = QVBoxLayout()
        self.internal_label = QLabel("内部ディスク総計", bottom)
        self.internal_bar = DiskUsageBar(parent=bottom)
        self.external_label = QLabel("外部ディスク総計", bottom)
        self.external_bar = DiskUsageBar(parent=bottom)
        bars_box.addWidget(self.internal_label)
        bars_box.addWidget(self.internal_bar)
        bars_box.addWidget(self.external_label)
        bars_box.addWidget(self.external_bar)
        summary_row.addLayout(bars_box, 1)

        self.summary_toggle_button = QPushButton("総計表示へ切替", bottom)
        self.summary_toggle_button.clicked.connect(self._toggle_summary_mode)
        summary_row.addWidget(self.summary_toggle_button)
        bottom_layout.addLayout(summary_row)

        button_row = QHBoxLayout()
        self.refresh_button = QPushButton("更新", bottom)
        self.info_button = QPushButton("情報", bottom)
        self.export_button = QPushButton("木生成", bottom)
        self.open_button = LongPressButton("木閲覧", bottom)
        self.settings_button = QPushButton("設定", bottom)

        self.refresh_button.clicked.connect(self.refresh_disks)
        self.info_button.clicked.connect(self._open_info_dialog)
        self.export_button.clicked.connect(self._export_mindmap)
        self.open_button.clicked.connect(self._open_last_mindmap)
        self.open_button.longPressed.connect(self._open_selected_mindmap)
        self.settings_button.clicked.connect(self._open_settings)

        for button in [self.refresh_button, self.info_button, self.export_button, self.open_button, self.settings_button]:
            button_row.addWidget(button)
        button_row.addStretch(1)
        bottom_layout.addLayout(button_row)
        splitter.addWidget(bottom)
        splitter.setSizes([560, 200])

        self._create_loading_overlay(central)
        self.statusBar().showMessage("準備完了")

    def _create_loading_overlay(self, parent: QWidget) -> None:
        self.loading_overlay = QWidget(parent)
        self.loading_overlay.setObjectName("loadingOverlay")
        self.loading_overlay.setStyleSheet("#loadingOverlay { background-color: rgba(0, 0, 0, 110); }")
        overlay_layout = QVBoxLayout(self.loading_overlay)
        overlay_layout.addStretch(1)

        panel = QFrame(self.loading_overlay)
        panel.setFrameShape(QFrame.StyledPanel)
        panel.setMinimumWidth(340)
        panel_layout = QVBoxLayout(panel)
        self.loading_label = QLabel("読み込み中...", panel)
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_progress = QProgressBar(panel)
        self.loading_progress.setRange(0, 0)
        self.loading_progress.setTextVisible(False)
        panel_layout.addWidget(self.loading_label)
        panel_layout.addWidget(self.loading_progress)

        overlay_layout.addWidget(panel, alignment=Qt.AlignCenter)
        overlay_layout.addStretch(1)
        self.loading_overlay.hide()
        self._position_loading_overlay()

    def _position_loading_overlay(self) -> None:
        if hasattr(self, "loading_overlay") and self.centralWidget() is not None:
            self.loading_overlay.setGeometry(self.centralWidget().rect())
            self.loading_overlay.raise_()

    def _set_loading_visible(self, visible: bool, message: str = "読み込み中...") -> None:
        if not hasattr(self, "loading_overlay"):
            return
        self.loading_label.setText(message)
        if visible:
            self._position_loading_overlay()
            self.loading_overlay.show()
            self.loading_overlay.raise_()
        else:
            self.loading_overlay.hide()
        for button_name in ["refresh_button", "info_button", "export_button", "open_button", "settings_button"]:
            button = getattr(self, button_name, None)
            if button is not None:
                button.setEnabled(not visible)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_loading_overlay()

    def _apply_default_column_widths(self) -> None:
        width = max(1000, self.width() or 1280)
        defaults = {
            self.COL_SELECT: 44,
            self.COL_ORDER: 96,
            self.COL_DRIVE: max(210, width // 6),
            self.COL_GROUP: 82,
            self.COL_PURPOSE: 88,
            self.COL_KIND: 110,
            self.COL_MEMO: 104,
            self.COL_FS: 110,
            self.COL_USAGE: max(260, width // 4),
            self.COL_ATTR: 160,
        }
        for col, col_width in defaults.items():
            self.tree.setColumnWidth(col, col_width)

    def _reset_refresh_timer(self) -> None:
        interval = max(1, int(self.config.get("basic.refresh_interval_seconds", 180)))
        self.refresh_timer.start(interval * 1000)

    def _decimals(self) -> tuple[int, int]:
        return int(self.config.get("basic.capacity_decimals", 2)), int(self.config.get("basic.percent_decimals", 2))

    def refresh_disks(self) -> None:
        if self._refreshing:
            return
        self.statusBar().showMessage("ディスク情報を更新中...")
        self._refreshing = True
        self._set_loading_visible(True, "ディスク情報を読み込み中...")
        QApplication.setOverrideCursor(Qt.WaitCursor)

        self._refresh_thread = QThread(self)
        self._refresh_worker = RefreshWorker(self.config)
        self._refresh_worker.moveToThread(self._refresh_thread)
        self._refresh_thread.started.connect(self._refresh_worker.run)
        self._refresh_worker.finished.connect(self._on_refresh_finished)
        self._refresh_worker.finished.connect(self._refresh_thread.quit)
        self._refresh_worker.finished.connect(self._refresh_worker.deleteLater)
        self._refresh_thread.finished.connect(self._refresh_thread.deleteLater)
        self._refresh_thread.finished.connect(self._clear_refresh_thread)
        self._refresh_thread.start()

    def _clear_refresh_thread(self) -> None:
        self._refresh_thread = None
        self._refresh_worker = None

    def _on_refresh_finished(self, snapshot: DiskSnapshot) -> None:
        try:
            self.snapshot = snapshot
            self._populate_tree()
            self._update_summary_bars()
        finally:
            self._refreshing = False
            self._set_loading_visible(False)
            QApplication.restoreOverrideCursor()

        if self.snapshot.errors:
            self.statusBar().showMessage(f"更新完了（注意 {len(self.snapshot.errors)} 件）", 5000)
        else:
            self.statusBar().showMessage("更新完了", 3000)

    def _on_header_clicked(self, column: int) -> None:
        if column not in self.SORTABLE_COLUMNS:
            return
        if self._sort_column == column:
            self._sort_desc = not self._sort_desc
        else:
            self._sort_column = column
            self._sort_desc = False
        self.config.set("ui.sort_column", self._sort_column)
        self.config.set("ui.sort_desc", self._sort_desc)
        self.config.save()
        self._update_sort_indicator()
        self._populate_tree()

    def _update_sort_indicator(self) -> None:
        order = Qt.DescendingOrder if self._sort_desc else Qt.AscendingOrder
        self.tree.header().setSortIndicator(self._sort_column, order)

    def _drive_key(self, text: str) -> tuple[int, int, str]:
        value = (text or "").upper().strip()
        if len(value) >= 2 and value[1] == ":" and value[0].isalpha():
            return (0, ord(value[0]) - ord("A"), value)
        return (1, 999, value.casefold())

    def _device_usage_percent(self, device: DeviceInfo) -> float:
        total = device.total_capacity
        return (device.total_used / total * 100) if total else 0.0

    def _volume_sort_key(self, volume: VolumeInfo, device: DeviceInfo):
        col = self._sort_column
        if col == self.COL_ORDER:
            return (volume.order_all, volume.order_device, self._drive_key(volume.drive))
        if col == self.COL_DRIVE:
            return self._drive_key(volume.drive)
        if col == self.COL_GROUP:
            return ((volume.group or "").casefold(), self._drive_key(volume.drive))
        if col == self.COL_KIND:
            return (0 if device.is_internal else 1, (device.media_type or "").casefold(), self._drive_key(volume.drive))
        if col == self.COL_USAGE:
            return (volume.percent, self._drive_key(volume.drive))
        return self._drive_key(volume.drive)

    def _device_sort_key(self, device: DeviceInfo):
        volumes = device.volumes
        col = self._sort_column
        if col == self.COL_ORDER:
            first_order = min((v.order_all for v in volumes), default=999999)
            return (first_order, device.index)
        if col == self.COL_DRIVE:
            first_drive = min((self._drive_key(v.drive) for v in volumes), default=(1, 999, device.title.casefold()))
            return (first_drive, device.title.casefold())
        if col == self.COL_GROUP:
            first_group = min(((v.group or "").casefold() for v in volumes), default="")
            return (first_group, device.title.casefold())
        if col == self.COL_KIND:
            return (0 if device.is_internal else 1, (device.media_type or "").casefold(), device.title.casefold())
        if col == self.COL_USAGE:
            return (self._device_usage_percent(device), device.title.casefold())
        return (device.index,)

    def _sorted_devices(self) -> list[DeviceInfo]:
        return sorted(self.snapshot.devices, key=self._device_sort_key, reverse=self._sort_desc)

    def _sorted_volumes(self, device: DeviceInfo) -> list[VolumeInfo]:
        return sorted(device.volumes, key=lambda volume: self._volume_sort_key(volume, device), reverse=self._sort_desc)

    def _populate_tree(self) -> None:
        self._loading = True
        self.tree.clear()
        self.volume_by_key.clear()
        self.device_by_index = {device.index: device for device in self.snapshot.devices}
        decimals, percent_decimals = self._decimals()
        for device in self._sorted_devices():
            parent = QTreeWidgetItem(self.tree)
            parent.setText(self.COL_SELECT, "")
            parent.setTextAlignment(self.COL_SELECT, Qt.AlignLeft | Qt.AlignVCenter)
            parent.setText(self.COL_DRIVE, device.title)
            parent.setText(self.COL_KIND, device.display_kind)
            parent.setText(self.COL_ATTR, ", ".join(device.attributes))
            # 設備本体は選択対象ではありません。選択できるのはファイルシステムを持つパーティションだけです。
            parent.setFlags(parent.flags() & ~Qt.ItemIsUserCheckable & ~Qt.ItemIsEditable)
            self.tree.setItemWidget(parent, self.COL_USAGE, DiskUsageBar(device.total_used, device.total_free, device.total_capacity, decimals, percent_decimals, self.tree))

            checked_children = 0
            for volume in self._sorted_volumes(device):
                self.volume_by_key[volume.key] = volume
                child = QTreeWidgetItem(parent)
                child.setTextAlignment(self.COL_SELECT, Qt.AlignLeft | Qt.AlignVCenter)
                child.setData(self.COL_SELECT, Qt.UserRole, volume.key)
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
                child.setCheckState(self.COL_SELECT, Qt.Checked if volume.selected else Qt.Unchecked)
                if volume.selected:
                    checked_children += 1
                self._fill_volume_item(child, volume, device)
                self.tree.setItemWidget(child, self.COL_USAGE, DiskUsageBar(volume.used, volume.free, volume.total, decimals, percent_decimals, self.tree))

            parent.setExpanded(True)
        self._loading = False

    def _fill_volume_item(self, item: QTreeWidgetItem, volume: VolumeInfo, device: DeviceInfo) -> None:
        item.setText(self.COL_ORDER, f"{volume.order_all} - {device.index}:{volume.order_device}")
        label = volume.label.strip()
        item.setText(self.COL_DRIVE, f"{volume.drive} （{label}）" if label else volume.drive)
        item.setText(self.COL_GROUP, volume.group)
        item.setText(self.COL_PURPOSE, volume.purpose)
        item.setText(self.COL_KIND, device.display_kind)
        item.setText(self.COL_MEMO, volume.memo)
        item.setText(self.COL_FS, volume.file_system)
        item.setText(self.COL_ATTR, ", ".join(volume.attributes))
        self._apply_group_style(item, volume.group)

    def _apply_group_style(self, item: QTreeWidgetItem, group: str) -> None:
        color_text = self.config.group_color(group)
        color = QColor(color_text) if color_text else QColor()
        if not color.isValid():
            item.setData(self.COL_GROUP, Qt.BackgroundRole, None)
            item.setData(self.COL_GROUP, Qt.ForegroundRole, None)
            return
        luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
        text_color = QColor(20, 20, 20) if luminance >= 0.55 else QColor(245, 245, 245)
        item.setBackground(self.COL_GROUP, QBrush(color))
        item.setForeground(self.COL_GROUP, QBrush(text_color))

    def _update_summary_bars(self) -> None:
        decimals, percent_decimals = self._decimals()
        single = bool(self.config.get("ui.summary_single_mode", False))
        if single:
            self.internal_label.setText("すべてのディスク総計")
            self.internal_bar.set_values(self.snapshot.all_used, self.snapshot.all_free, self.snapshot.all_total, decimals, percent_decimals)
            self.external_label.hide()
            self.external_bar.hide()
            self.summary_toggle_button.setText("内部/外部表示へ切替")
        else:
            self.internal_label.setText("内部ディスク総計" if self.snapshot.internal_total else "内部ディスクなし")
            self.internal_bar.set_values(self.snapshot.internal_used, self.snapshot.internal_free, self.snapshot.internal_total, decimals, percent_decimals)
            self.external_label.setText("外部ディスク総計" if self.snapshot.external_total else "外部ディスクなし")
            self.external_bar.set_values(self.snapshot.external_used, self.snapshot.external_free, self.snapshot.external_total, decimals, percent_decimals)
            self.external_label.show()
            self.external_bar.show()
            self.summary_toggle_button.setText("総計表示へ切替")

    def _toggle_summary_mode(self) -> None:
        value = not bool(self.config.get("ui.summary_single_mode", False))
        self.config.set("ui.summary_single_mode", value)
        self.config.save()
        self._update_summary_bars()

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        if column in {self.COL_GROUP, self.COL_PURPOSE, self.COL_MEMO} and item.parent() is not None:
            self.tree.editItem(item, column)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._loading:
            return
        key = item.data(self.COL_SELECT, Qt.UserRole)
        if item.parent() is None:
            return
        if not key:
            return
        key = str(key)
        if column == self.COL_SELECT:
            self.config.set_drive_note_value(key, "selected", item.checkState(self.COL_SELECT) == Qt.Checked)
        elif column == self.COL_GROUP:
            group = item.text(column).strip()
            self.config.set_drive_note_value(key, "group", group)
            self._apply_group_style(item, group)
        elif column == self.COL_PURPOSE:
            self.config.set_drive_note_value(key, "purpose", item.text(column).strip())
        elif column == self.COL_MEMO:
            self.config.set_drive_note_value(key, "memo", item.text(column).strip())
        self.config.save()

    def _show_tree_context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if not item or item.parent() is None:
            return
        key = item.data(self.COL_SELECT, Qt.UserRole)
        if not key:
            return
        key = str(key)
        volume = self.volume_by_key.get(key)
        if volume is None:
            return

        menu = QMenu(self)
        open_action = QAction("パーティションを開く", self)
        open_action.triggered.connect(lambda: self._open_partition(volume))
        export_action = QAction("このパーティションの木を生成する", self)
        export_action.triggered.connect(lambda: self._export_mindmap({key}))
        info_action = QAction("パーティション情報", self)
        info_action.triggered.connect(lambda: self._open_partition_info(volume))
        purpose_action = QAction("用途編集", self)
        purpose_action.triggered.connect(lambda: self._ask_item_text(item, key, self.COL_PURPOSE, "purpose", "用途"))
        memo_action = QAction("メモ編集", self)
        memo_action.triggered.connect(lambda: self._ask_item_text(item, key, self.COL_MEMO, "memo", "メモ"))

        menu.addAction(open_action)
        menu.addAction(export_action)
        menu.addAction(info_action)
        menu.addSeparator()

        group_menu = menu.addMenu("グループ変更")
        groups = self.config.known_groups()
        if groups:
            for group in groups:
                action = QAction(group, self)
                action.triggered.connect(lambda checked=False, g=group: self._set_item_group(item, key, g))
                group_menu.addAction(action)
            group_menu.addSeparator()
        new_action = QAction("新しいグループを入力", self)
        new_action.triggered.connect(lambda: self._ask_item_group(item, key))
        clear_action = QAction("グループを消す", self)
        clear_action.triggered.connect(lambda: self._set_item_group(item, key, ""))
        group_menu.addAction(new_action)
        group_menu.addAction(clear_action)

        menu.addAction(purpose_action)
        menu.addAction(memo_action)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _set_item_group(self, item: QTreeWidgetItem, key: str, group: str) -> None:
        item.setText(self.COL_GROUP, group)
        self._apply_group_style(item, group)
        self.config.set_drive_note_value(key, "group", group)
        self.config.save()

    def _ask_item_group(self, item: QTreeWidgetItem, key: str) -> None:
        text, ok = QInputDialog.getText(self, "グループ", "グループ名", text=item.text(self.COL_GROUP))
        if ok:
            self._set_item_group(item, key, text.strip())

    def _selected_volume_keys(self) -> set[str]:
        keys: set[str] = set()
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                key = child.data(self.COL_SELECT, Qt.UserRole)
                if key and child.checkState(self.COL_SELECT) == Qt.Checked:
                    keys.add(str(key))
        return keys

    def _open_info_dialog(self) -> None:
        dialog = InfoDialog(self.snapshot, self.scanner, self.config, self)
        dialog.exec()

    def _export_mindmap(self, selected_override: set[str] | None = None) -> None:
        selected = selected_override or self._selected_volume_keys()
        if not selected:
            QMessageBox.information(self, "選択なし", "出力するドライブにチェックを入れてください。")
            return
        options = MindmapExportOptionsDialog(self.config, self)
        if options.exec() != QDialog.Accepted:
            return
        path, _ = QFileDialog.getSaveFileName(self, "マインドマップを保存", str(Path.home() / "DriveMind.km"), "DesktopNaotu Mindmap (*.km);;All files (*.*)")
        if not path:
            return
        if not path.lower().endswith(".km"):
            path += ".km"
        exporter = MindmapExporter(self.config)
        self._set_loading_visible(True, "マインドマップを生成中...")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            output = exporter.export(
                self.snapshot.devices,
                selected,
                path,
                max_depth=options.max_depth,
                max_files_per_folder=options.max_files_per_folder,
            )
        except Exception as exc:
            QApplication.restoreOverrideCursor()
            self._set_loading_visible(False)
            QMessageBox.warning(self, "出力失敗", f"マインドマップを出力できませんでした。\n{exc}")
            return
        QApplication.restoreOverrideCursor()
        self._set_loading_visible(False)
        message = f"マインドマップを出力しました。\n{output}"
        if exporter.errors:
            message += f"\n\n読み取りできなかった項目: {len(exporter.errors)} 件"
        QMessageBox.information(self, "出力完了", message)

    def _open_partition(self, volume: VolumeInfo) -> None:
        path = volume.mountpoint or volume.drive
        if not path:
            return
        try:
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as exc:
            QMessageBox.warning(self, "起動失敗", f"パーティションを開けませんでした。\n{exc}")

    def _open_partition_info(self, volume: VolumeInfo) -> None:
        device = self.device_by_index.get(volume.device_index)
        if device is None:
            QMessageBox.warning(self, "情報なし", "所属デバイス情報を取得できませんでした。")
            return
        dialog = PartitionInfoDialog(device, volume, self.config, self)
        dialog.exec()

    def _ask_item_text(self, item: QTreeWidgetItem, key: str, column: int, field: str, title: str) -> None:
        text, ok = QInputDialog.getText(self, title, title, text=item.text(column))
        if not ok:
            return
        value = text.strip()
        item.setText(column, value)
        self.config.set_drive_note_value(key, field, value)
        self.config.save()

    def _ensure_naotu_path(self) -> str:
        path = str(self.config.get("desktop_naotu.exe_path", "")).strip()
        if path and Path(path).exists():
            return path
        selected, _ = QFileDialog.getOpenFileName(self, "DesktopNaotuを選択", str(Path.home()), "Executable (*.exe);;All files (*.*)")
        if selected:
            self.config.set("desktop_naotu.exe_path", selected)
            self.config.save()
        return selected

    def _open_last_mindmap(self) -> None:
        path = str(self.config.get("runtime.last_export_path", "")).strip()
        if not path or not Path(path).exists():
            self._open_selected_mindmap()
            return
        self._open_mindmap_file(path)

    def _open_selected_mindmap(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "マインドマップを選択", str(Path.home()), "DesktopNaotu Mindmap (*.km);;All files (*.*)")
        if path:
            self.config.set("runtime.last_export_path", path)
            self.config.save()
            self._open_mindmap_file(path)

    def _open_mindmap_file(self, km_path: str) -> None:
        exe = self._ensure_naotu_path()
        if not exe:
            return
        try:
            subprocess.Popen([exe, km_path], close_fds=True)
        except Exception as exc:
            try:
                if os.name == "nt":
                    os.startfile(km_path)  # type: ignore[attr-defined]
                    return
            except Exception:
                pass
            QMessageBox.warning(self, "起動失敗", f"DesktopNaotuで開けませんでした。\n{exc}")

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self._reset_refresh_timer()
            self.autosave_timer.start(int(self.config.get("basic.autosave_minutes", 5)) * 60 * 1000)
            self._update_summary_bars()
            self.refresh_disks()

    def _maybe_startup_update_check(self) -> None:
        frequency = str(self.config.get("other.update_check_frequency", "daily"))
        last_check = str(self.config.get("other.last_update_check", ""))
        if not should_check_update(frequency, last_check):
            return
        self._start_update_check()

    def _start_update_check(self) -> None:
        if self._update_thread is not None:
            return
        self._update_thread = QThread(self)
        self._update_worker = UpdateWorker()
        self._update_worker.moveToThread(self._update_thread)
        self._update_thread.started.connect(self._update_worker.run)
        self._update_worker.finished.connect(self._on_update_check_finished)
        self._update_worker.finished.connect(self._update_thread.quit)
        self._update_worker.finished.connect(self._update_worker.deleteLater)
        self._update_thread.finished.connect(self._update_thread.deleteLater)
        self._update_thread.finished.connect(self._clear_update_thread)
        self._update_thread.start()

    def _clear_update_thread(self) -> None:
        self._update_thread = None
        self._update_worker = None

    def _on_update_check_finished(self, result: UpdateResult) -> None:
        self.config.set("other.last_update_check", today_iso())
        self.config.save()
        if not result.ok or not result.has_update:
            return
        skip_version = str(self.config.get("other.skip_version", "")).strip()
        suppress_date = str(self.config.get("other.suppress_update_date", "")).strip()
        if skip_version and skip_version.lstrip("v") == result.latest_version.lstrip("v"):
            return
        if suppress_date == QDate.currentDate().toString("yyyy-MM-dd"):
            return

        box = QMessageBox(self)
        box.setWindowTitle("更新があります")
        box.setIcon(QMessageBox.Information)
        box.setText(f"DriveMind の新しいバージョンがあります。\n現在: v{__version__}\n最新: {result.latest_version}")
        open_button = box.addButton("Releaseページを開く", QMessageBox.AcceptRole)
        today_button = box.addButton("今日は提示しない", QMessageBox.ActionRole)
        skip_button = box.addButton("このバージョンを提示しない", QMessageBox.ActionRole)
        box.addButton("閉じる", QMessageBox.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked == open_button:
            webbrowser.open(result.release_url or GITHUB_RELEASES_URL)
        elif clicked == today_button:
            self.config.set("other.suppress_update_date", today_iso())
            self.config.save()
        elif clicked == skip_button:
            self.config.set("other.skip_version", result.latest_version)
            self.config.save()

    def _restore_header_state(self) -> None:
        state_text = str(self.config.get("ui.column_order_state", ""))
        if state_text:
            try:
                state = QByteArray.fromBase64(state_text.encode("ascii"))
                self.tree.header().restoreState(state)
            except Exception:
                pass
        self._force_select_column_first()
        self._apply_default_column_widths()
        self._update_sort_indicator()

    def _force_select_column_first(self) -> None:
        header = self.tree.header()
        visual = header.visualIndex(self.COL_SELECT)
        if visual > 0:
            header.moveSection(visual, 0)

    def _save_header_state(self) -> None:
        try:
            state = bytes(self.tree.header().saveState().toBase64()).decode("ascii")
            self.config.set("ui.column_order_state", state)
        except Exception:
            pass

    def closeEvent(self, event) -> None:  # noqa: N802
        self._save_header_state()
        self.config.save()
        super().closeEvent(event)
