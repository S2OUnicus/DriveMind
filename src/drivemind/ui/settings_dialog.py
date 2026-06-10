from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from drivemind.core.config import DEFAULT_SETTINGS, ConfigManager
from drivemind.core.models import DeviceInfo, DiskSnapshot, VolumeInfo
from drivemind.core.update_checker import check_latest_release, today_iso
from drivemind.core.formatting import format_bytes
from drivemind.core.app_logger import configure_logging, delete_all_logs, log_dir, log_total_size, open_log_folder
from drivemind.ui.i18n import LANGUAGES, tr


GROUP_COLOR_PALETTE: dict[str, list[str]] = {
    "s": ["#e57373", "#f06292", "#ba68c8", "#64b5f6", "#4dd0e1", "#81c784", "#ffd54f", "#ff8a65"],
    "b": ["#ff8a80", "#ff80ab", "#ea80fc", "#82b1ff", "#84ffff", "#b9f6ca", "#ffff8d", "#ffd180"],
    "v": ["#f44336", "#e91e63", "#9c27b0", "#2196f3", "#00bcd4", "#4caf50", "#ffc107", "#ff5722"],
    "ltg": ["#d7ccc8", "#cfd8dc", "#d1c4e9", "#bbdefb", "#b2dfdb", "#c8e6c9", "#f0f4c3", "#ffe0b2"],
}


def _contrast_text_color(color: QColor) -> str:
    luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
    return "#141414" if luminance >= 0.55 else "#f5f5f5"


def _volume_display(volume: VolumeInfo) -> str:
    label = volume.label.strip()
    return f"{volume.drive} （{label}）" if label else volume.drive


class GroupManagerTab(QWidget):
    def __init__(self, config: ConfigManager, snapshot: DiskSnapshot | None = None, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.snapshot = snapshot or DiskSnapshot()
        self.current_color = ""
        root = QVBoxLayout(self)
        root.addWidget(QLabel("グループ名と色を管理します。色はメイン画面のグループ列だけに背景色として表示されます。", self))

        body = QHBoxLayout()
        self.list_widget = QListWidget(self)
        self.list_widget.currentItemChanged.connect(self._on_current_changed)
        body.addWidget(self.list_widget, 1)

        right = QVBoxLayout()
        form = QFormLayout()
        self.name_edit = QLineEdit(self)
        form.addRow("グループ名", self.name_edit)
        self.preview = QLabel(" 色プレビュー ", self)
        self.preview.setMinimumHeight(28)
        form.addRow("色", self.preview)
        right.addLayout(form)

        palette_box = QGroupBox("色パネル", self)
        palette = QGridLayout(palette_box)
        row = 0
        for tone, colors in GROUP_COLOR_PALETTE.items():
            palette.addWidget(QLabel(tone, palette_box), row, 0)
            for col, color in enumerate(colors, start=1):
                btn = QPushButton("", palette_box)
                btn.setFixedSize(26, 22)
                btn.setStyleSheet(f"background-color: {color}; border: 1px solid #888;")
                btn.clicked.connect(lambda checked=False, c=color: self._set_current_color(c))
                palette.addWidget(btn, row, col)
            row += 1
        right.addWidget(palette_box)

        self.related_list = QListWidget(self)
        self.related_list.setMinimumHeight(110)
        right.addWidget(QLabel("このグループに対応するパーティション", self))
        right.addWidget(self.related_list, 1)

        button_row = QHBoxLayout()
        self.add_button = QPushButton("追加", self)
        self.apply_button = QPushButton("更新", self)
        self.rename_button = QPushButton("名前変更", self)
        self.delete_button = QPushButton("削除", self)
        self.rgb_button = QPushButton("RGB指定", self)
        self.clear_color_button = QPushButton("色なし", self)
        self.add_button.clicked.connect(self._add_group)
        self.apply_button.clicked.connect(self._apply_group)
        self.rename_button.clicked.connect(self._rename_group)
        self.delete_button.clicked.connect(self._delete_group)
        self.rgb_button.clicked.connect(self._choose_rgb)
        self.clear_color_button.clicked.connect(lambda: self._set_current_color(""))
        for button in [self.add_button, self.apply_button, self.rename_button, self.delete_button, self.rgb_button, self.clear_color_button]:
            button_row.addWidget(button)
        right.addLayout(button_row)
        body.addLayout(right, 2)
        root.addLayout(body, 1)
        self.reload()

    def set_snapshot(self, snapshot: DiskSnapshot) -> None:
        self.snapshot = snapshot
        self._reload_related()

    def reload(self) -> None:
        current = self.current_name()
        self.list_widget.clear()
        for group in self.config.known_groups():
            item = QListWidgetItem(group)
            color_text = self.config.group_color(group)
            color = QColor(color_text) if color_text else QColor()
            if color.isValid():
                item.setBackground(color)
                item.setForeground(QColor(_contrast_text_color(color)))
            self.list_widget.addItem(item)
            if group == current:
                self.list_widget.setCurrentItem(item)
        if self.list_widget.count() and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)
        self._update_preview()
        self._reload_related()

    def current_name(self) -> str:
        item = self.list_widget.currentItem()
        return item.text().strip() if item else ""

    def _on_current_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        name = current.text().strip() if current else ""
        self.name_edit.setText(name)
        self.current_color = self.config.group_color(name) if name else ""
        self._update_preview()
        self._reload_related()

    def _reload_related(self) -> None:
        self.related_list.clear()
        group = self.current_name()
        if not group:
            return
        for device in self.snapshot.devices:
            for volume in device.volumes:
                note_group = str(self.config.drive_note(volume.key).get("group", volume.group))
                if note_group == group:
                    self.related_list.addItem(f"{device.name} / {_volume_display(volume)}")

    def _set_current_color(self, color: str) -> None:
        self.current_color = color
        self._update_preview()

    def _update_preview(self) -> None:
        color = QColor(self.current_color) if self.current_color else QColor()
        if color.isValid():
            text_color = _contrast_text_color(color)
            self.preview.setStyleSheet(f"background-color: {self.current_color}; color: {text_color}; border: 1px solid #888; padding: 4px;")
            self.preview.setText(f" {self.current_color} ")
        else:
            self.preview.setStyleSheet("border: 1px solid #888; padding: 4px;")
            self.preview.setText(" 色なし ")

    def _add_group(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            name, ok = QInputDialog.getText(self, "グループ追加", "グループ名")
            if not ok:
                return
            name = name.strip()
        if not name:
            return
        self.config.add_group(name, self.current_color)
        self.reload()

    def _apply_group(self) -> None:
        name = self.name_edit.text().strip() or self.current_name()
        if not name:
            return
        self.config.set_group_color(name, self.current_color)
        self.reload()

    def _rename_group(self) -> None:
        old_name = self.current_name()
        new_name = self.name_edit.text().strip()
        if not old_name or not new_name or old_name == new_name:
            return
        self.config.rename_group(old_name, new_name)
        self.config.set_group_color(new_name, self.current_color)
        self.reload()

    def _delete_group(self) -> None:
        name = self.current_name()
        if not name:
            return
        reply = QMessageBox.question(
            self,
            "グループ削除",
            f"グループ「{name}」を削除します。\nこのグループを使っているすべてのパーティションのグループ設定は空欄に戻ります。\n続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        changed = self.config.remove_group(name)
        self.reload()
        QMessageBox.information(self, "削除完了", f"グループを削除しました。\n初期値に戻したパーティション: {changed} 件")

    def _choose_rgb(self) -> None:
        initial = QColor(self.current_color) if self.current_color else QColor("#80cbc4")
        color = QColorDialog.getColor(initial, self, "グループ色を選択")
        if color.isValid():
            self._set_current_color(color.name())


class PartitionTextManagerTab(QWidget):
    def __init__(self, config: ConfigManager, snapshot: DiskSnapshot, field: str, title: str, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.snapshot = snapshot
        self.field = field
        self.title = title
        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"{title}はパーティションごとに一対一で管理します。内容の重複も使用できます。", self))
        self.tree = QTreeWidget(self)
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["選択", "ドライブ（ラベル）", title])
        self.tree.setRootIsDecorated(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.itemChanged.connect(self._on_item_changed)
        root.addWidget(self.tree, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        self.bulk_combo = QComboBox(self)
        self.bulk_combo.addItem("一括削除", "delete")
        self.bulk_combo.addItem("一括変更", "edit")
        self.bulk_button = QPushButton("一括操作", self)
        self.bulk_button.clicked.connect(self._bulk_action)
        row.addWidget(self.bulk_combo)
        row.addWidget(self.bulk_button)
        root.addLayout(row)
        self.reload()

    def set_snapshot(self, snapshot: DiskSnapshot) -> None:
        self.snapshot = snapshot
        self.reload()

    def reload(self) -> None:
        self.tree.blockSignals(True)
        self.tree.clear()
        for device in self.snapshot.devices:
            parent = QTreeWidgetItem(self.tree)
            parent.setText(1, device.title)
            parent.setFlags(parent.flags() & ~Qt.ItemIsUserCheckable & ~Qt.ItemIsEditable)
            for volume in device.volumes:
                child = QTreeWidgetItem(parent)
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
                child.setCheckState(0, Qt.Unchecked)
                child.setData(0, Qt.UserRole, volume.key)
                child.setText(1, _volume_display(volume))
                child.setText(2, str(self.config.drive_note(volume.key).get(self.field, getattr(volume, self.field, ""))))
            parent.setExpanded(True)
        self.tree.resizeColumnToContents(0)
        self.tree.resizeColumnToContents(1)
        self.tree.blockSignals(False)

    def _selected_keys(self) -> list[str]:
        keys: list[str] = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0) == Qt.Checked:
                    key = str(child.data(0, Qt.UserRole) or "")
                    if key:
                        keys.append(key)
        return keys

    def _show_context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        if not item or item.parent() is None:
            return
        key = str(item.data(0, Qt.UserRole) or "")
        if not key:
            return
        menu = QMenu(self)
        edit_action = QAction(f"{self.title}編集", self)
        delete_action = QAction("削除", self)
        edit_action.triggered.connect(lambda: self._edit_item(item, key))
        delete_action.triggered.connect(lambda: self._set_value(item, key, ""))
        menu.addAction(edit_action)
        menu.addAction(delete_action)
        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _edit_item(self, item: QTreeWidgetItem, key: str) -> None:
        text, ok = QInputDialog.getText(self, f"{self.title}編集", self.title, text=item.text(2))
        if ok:
            self._set_value(item, key, text.strip())

    def _set_value(self, item: QTreeWidgetItem | None, key: str, value: str) -> None:
        self.config.set_drive_note_value(key, self.field, value)
        if item is not None:
            item.setText(2, value)

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if column != 2 or item.parent() is None:
            return
        key = str(item.data(0, Qt.UserRole) or "")
        if key:
            self.config.set_drive_note_value(key, self.field, item.text(2).strip())

    def _bulk_action(self) -> None:
        keys = self._selected_keys()
        if not keys:
            QMessageBox.information(self, "選択なし", "一括操作するパーティションを選択してください。")
            return
        action = self.bulk_combo.currentData()
        if action == "delete":
            reply = QMessageBox.question(self, "一括削除", f"選択した {len(keys)} 件の{self.title}を空欄に戻します。続行しますか？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
            value = ""
        else:
            value, ok = QInputDialog.getText(self, "一括変更", f"新しい{self.title}")
            if not ok:
                return
            value = value.strip()
        for key in keys:
            self.config.set_drive_note_value(key, self.field, value)
        self.reload()


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, snapshot: DiskSnapshot | None = None, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.snapshot = snapshot or DiskSnapshot()
        self._settings_backup = deepcopy(config.settings)
        self.setWindowTitle("設定 - DriveMind")
        self.resize(840, 640)

        root = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs)

        self._build_basic_tab()
        self._build_naotu_tab()
        self._build_mindmap_tab()
        self.group_tab = GroupManagerTab(self.config, self.snapshot, self)
        self.purpose_tab = PartitionTextManagerTab(self.config, self.snapshot, "purpose", "用途", self)
        self.memo_tab = PartitionTextManagerTab(self.config, self.snapshot, "memo", "メモ", self)
        self.tabs.addTab(self.group_tab, "グループ")
        self.tabs.addTab(self.purpose_tab, "用途管理")
        self.tabs.addTab(self.memo_tab, "メモ管理")
        self._build_log_tab()
        self._build_other_tab()

        bottom = QHBoxLayout()
        self.reset_tab_button = QPushButton("このタブを初期値に戻す", self)
        self.reset_tab_button.clicked.connect(self._reset_current_tab)
        bottom.addWidget(self.reset_tab_button)
        bottom.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.button(QDialogButtonBox.Ok).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("キャンセル")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        bottom.addWidget(buttons)
        root.addLayout(bottom)

        self._load_values()

    def _build_basic_tab(self) -> None:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        form = QFormLayout()

        self.refresh_spin = QSpinBox(tab)
        self.refresh_spin.setRange(1, 3600)
        self.refresh_spin.setSuffix(" 秒")
        form.addRow("ディスクリスト自動更新間隔", self.refresh_spin)

        self.autosave_spin = QSpinBox(tab)
        self.autosave_spin.setRange(1, 1440)
        self.autosave_spin.setSuffix(" 分")
        form.addRow("自動保存間隔", self.autosave_spin)

        self.capacity_decimals_spin = QSpinBox(tab)
        self.capacity_decimals_spin.setRange(0, 4)
        form.addRow("容量表示の小数桁", self.capacity_decimals_spin)

        self.percent_decimals_spin = QSpinBox(tab)
        self.percent_decimals_spin.setRange(0, 4)
        form.addRow("パーセント表示の小数桁", self.percent_decimals_spin)

        self.language_combo = QComboBox(tab)
        for code, label in LANGUAGES:
            self.language_combo.addItem(label, code)
        form.addRow("表示言語", self.language_combo)

        self.theme_combo = QComboBox(tab)
        self.theme_combo.addItem("🌙 darkmode", "dark")
        self.theme_combo.addItem("☀ lightmode", "light")
        form.addRow("テーマ", self.theme_combo)

        self.system_disk_internal_cb = QCheckBox("システムパーティションが存在するディスクを内部ドライブとして扱う", tab)
        form.addRow("内部/外部判定", self.system_disk_internal_cb)

        self.show_esp_cb = QCheckBox("ESP パーティションを表示する", tab)
        self.show_msr_cb = QCheckBox("MSR パーティションを表示する", tab)
        self.show_oem_cb = QCheckBox("OEM パーティションを表示する", tab)
        self.show_ro_cb = QCheckBox("読み取り専用パーティションを表示する", tab)
        self.show_hidden_partition_cb = QCheckBox("隠れたパーティションを表示する", tab)
        form.addRow("特殊パーティション", self.show_esp_cb)
        form.addRow("", self.show_msr_cb)
        form.addRow("", self.show_oem_cb)
        form.addRow("", self.show_ro_cb)
        form.addRow("", self.show_hidden_partition_cb)

        self.show_ram_disks_cb = QCheckBox("RAMCache / RamDisk などの RAM ディスクを表示する", tab)
        self.show_web_disks_cb = QCheckBox("Google Drive などの WebDisk を表示する", tab)
        self.show_remote_disks_cb = QCheckBox("ネットワーク共有 / リモートドライブを表示する", tab)
        form.addRow("仮想/リモート", self.show_ram_disks_cb)
        form.addRow("", self.show_web_disks_cb)
        form.addRow("", self.show_remote_disks_cb)

        self.run_as_admin_cb = QCheckBox("次回から管理者として起動する", tab)
        form.addRow("管理者権限", self.run_as_admin_cb)

        path_row = QHBoxLayout()
        self.config_path_edit = QLineEdit(tab)
        browse_config = QPushButton("参照", tab)
        browse_config.clicked.connect(self._browse_config_path)
        path_row.addWidget(self.config_path_edit, 1)
        path_row.addWidget(browse_config)
        form.addRow("設定ファイル", path_row)

        layout.addLayout(form)

        load_box = QGroupBox("ほかの設定ファイルを読み込む", tab)
        load_layout = QVBoxLayout(load_box)
        load_text = QLabel("別PCの設定ファイルなどを読み込み、使える項目だけ現在の設定に取り込みます。", load_box)
        load_text.setWordWrap(True)
        load_button = QPushButton("設定ファイルを読み込む", load_box)
        load_button.clicked.connect(self._load_external_config)
        load_layout.addWidget(load_text)
        load_layout.addWidget(load_button, alignment=Qt.AlignLeft)
        layout.addWidget(load_box)
        layout.addStretch(1)
        self.tabs.addTab(tab, "基本設定")

    def _build_naotu_tab(self) -> None:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        form = QFormLayout()
        row = QHBoxLayout()
        self.naotu_path_edit = QLineEdit(tab)
        browse = QPushButton("参照", tab)
        browse.clicked.connect(self._browse_naotu_path)
        row.addWidget(self.naotu_path_edit, 1)
        row.addWidget(browse)
        form.addRow("DesktopNaotu 実行ファイル", row)
        layout.addLayout(form)
        note = QLabel("未設定の場合、木閲覧ボタンを押した時に実行ファイルを選択できます。", tab)
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch(1)
        self.tabs.addTab(tab, "DesktopNaotu")

    def _build_mindmap_tab(self) -> None:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        form = QFormLayout()

        self.exclude_text = QTextEdit(tab)
        self.exclude_text.setPlaceholderText("1行に1つずつ除外名を書きます")
        form.addRow("出力しない名前", self.exclude_text)

        self.include_hidden_cb = QCheckBox("隠しファイル・隠しフォルダを出力する", tab)
        form.addRow("隠し項目", self.include_hidden_cb)

        self.mark_hidden_cb = QCheckBox("隠し項目名の後ろに [Hide] を付ける", tab)
        form.addRow("隠し表記", self.mark_hidden_cb)

        self.include_system_cb = QCheckBox("システムファイル・システムフォルダを出力する", tab)
        form.addRow("システム項目", self.include_system_cb)

        self.include_files_cb = QCheckBox("ファイルも出力する（オフの場合はフォルダのみ）", tab)
        form.addRow("ファイル", self.include_files_cb)

        self.include_extensions_cb = QCheckBox("ファイルの拡張子を出力する", tab)
        form.addRow("拡張子", self.include_extensions_cb)

        self.output_device_name_cb = QCheckBox("デバイス名を出力する（オンの場合は従来のデバイス > パーティション構造）", tab)
        form.addRow("出力構造", self.output_device_name_cb)

        self.include_program_folders_cb = QCheckBox("プログラムフォルダも中身まで出力する", tab)
        form.addRow("プログラムフォルダ", self.include_program_folders_cb)

        self.adobe_project_folder_only_cb = QCheckBox("Adobe系プロジェクトはフォルダだけ出力する", tab)
        form.addRow("Adobeプロジェクト", self.adobe_project_folder_only_cb)

        self.max_depth_spin = QSpinBox(tab)
        self.max_depth_spin.setRange(1, 128)
        form.addRow("初期最大フォルダ階層", self.max_depth_spin)

        self.max_files_spin = QSpinBox(tab)
        self.max_files_spin.setRange(0, 10000)
        self.max_files_spin.setSpecialValueText("制限しない")
        form.addRow("同一フォルダ内の初期最大ファイル数", self.max_files_spin)

        layout.addLayout(form)
        layout.addStretch(1)
        self.tabs.addTab(tab, "マインドマップ")

    def _build_log_tab(self) -> None:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        form = QFormLayout()

        self.log_level_combo = QComboBox(tab)
        self.log_level_combo.addItem("Debug", "debug")
        self.log_level_combo.addItem("Info", "info")
        self.log_level_combo.addItem("Warning", "warning")
        self.log_level_combo.addItem("Error", "error")
        form.addRow("ログ完全度", self.log_level_combo)

        self.log_keep_days_spin = QSpinBox(tab)
        self.log_keep_days_spin.setRange(1, 3650)
        self.log_keep_days_spin.setSuffix(" 日")
        form.addRow("保留日数", self.log_keep_days_spin)

        self.log_max_size_spin = QSpinBox(tab)
        self.log_max_size_spin.setRange(1, 4096)
        self.log_max_size_spin.setSuffix(" MB")
        form.addRow("サイズ制限", self.log_max_size_spin)

        layout.addLayout(form)
        info = QLabel(f"ログは {log_dir()} に .log ファイルとして保存されます。", tab)
        info.setWordWrap(True)
        layout.addWidget(info)
        self.log_size_label = QLabel("現在のログサイズ: 計算中", tab)
        layout.addWidget(self.log_size_label)

        row = QHBoxLayout()
        self.open_log_button = QPushButton("ログを開く", tab)
        self.delete_log_button = QPushButton("ログを全部削除", tab)
        self.open_log_button.clicked.connect(self._open_logs)
        self.delete_log_button.clicked.connect(self._delete_logs)
        row.addWidget(self.open_log_button)
        row.addWidget(self.delete_log_button)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addStretch(1)
        self.tabs.addTab(tab, "ログ")

    def _build_other_tab(self) -> None:
        tab = QWidget(self)
        layout = QVBoxLayout(tab)
        form = QFormLayout()

        self.update_freq_combo = QComboBox(tab)
        self.update_freq_combo.addItem("毎日確認", "daily")
        self.update_freq_combo.addItem("毎週確認", "weekly")
        self.update_freq_combo.addItem("毎月確認", "monthly")
        self.update_freq_combo.addItem("確認しない", "never")
        form.addRow("更新確認", self.update_freq_combo)

        self.last_check_label = QLabel("未確認", tab)
        form.addRow("最後の確認日", self.last_check_label)

        layout.addLayout(form)

        button_row = QHBoxLayout()
        self.reset_all_button = QPushButton("すべての設定を初期化", tab)
        self.reset_all_button.clicked.connect(self._reset_all_settings)
        self.reset_update_notice_button = QPushButton("バージョン提示をリセット", tab)
        self.reset_update_notice_button.clicked.connect(self._reset_update_notice)
        self.check_now_button = QPushButton("今すぐ更新確認", tab)
        self.check_now_button.clicked.connect(self._check_now)
        button_row.addWidget(self.reset_all_button)
        button_row.addStretch(1)
        button_row.addWidget(self.reset_update_notice_button)
        button_row.addWidget(self.check_now_button)
        layout.addLayout(button_row)
        layout.addStretch(1)
        self.tabs.addTab(tab, "その他")

    def _load_values(self) -> None:
        self.refresh_spin.setValue(int(self.config.get("basic.refresh_interval_seconds", 180)))
        self.autosave_spin.setValue(int(self.config.get("basic.autosave_minutes", 5)))
        self.capacity_decimals_spin.setValue(int(self.config.get("basic.capacity_decimals", 2)))
        self.percent_decimals_spin.setValue(int(self.config.get("basic.percent_decimals", 2)))
        lang_index = self.language_combo.findData(str(self.config.get("basic.language", "ja")))
        self.language_combo.setCurrentIndex(max(0, lang_index))
        theme_index = self.theme_combo.findData(str(self.config.get("basic.theme", "dark")))
        self.theme_combo.setCurrentIndex(max(0, theme_index))
        self.system_disk_internal_cb.setChecked(bool(self.config.get("basic.treat_system_disk_as_internal", True)))
        self.show_esp_cb.setChecked(bool(self.config.get("basic.show_esp_partitions", False)))
        self.show_msr_cb.setChecked(bool(self.config.get("basic.show_msr_partitions", False)))
        self.show_oem_cb.setChecked(bool(self.config.get("basic.show_oem_partitions", False)))
        self.show_ro_cb.setChecked(bool(self.config.get("basic.show_readonly_partitions", True)))
        self.show_hidden_partition_cb.setChecked(bool(self.config.get("basic.show_hidden_partitions", False)))
        self.show_ram_disks_cb.setChecked(bool(self.config.get("basic.show_ram_disks", False)))
        self.show_web_disks_cb.setChecked(bool(self.config.get("basic.show_web_disks", False)))
        self.show_remote_disks_cb.setChecked(bool(self.config.get("basic.show_remote_disks", False)))
        self.run_as_admin_cb.setChecked(bool(self.config.get("basic.run_as_admin", False)))
        self.config_path_edit.setText(str(self.config.path))
        self.naotu_path_edit.setText(str(self.config.get("desktop_naotu.exe_path", "")))
        self.exclude_text.setPlainText("\n".join(self.config.get("mindmap.exclude_names", [])))
        self.include_hidden_cb.setChecked(bool(self.config.get("mindmap.include_hidden", True)))
        self.mark_hidden_cb.setChecked(bool(self.config.get("mindmap.mark_hidden", True)))
        self.include_system_cb.setChecked(bool(self.config.get("mindmap.include_system", False)))
        self.include_files_cb.setChecked(bool(self.config.get("mindmap.include_files", False)))
        self.include_extensions_cb.setChecked(bool(self.config.get("mindmap.include_extensions", True)))
        self.output_device_name_cb.setChecked(bool(self.config.get("mindmap.output_device_name", False)))
        self.include_program_folders_cb.setChecked(bool(self.config.get("mindmap.include_program_folders", False)))
        self.adobe_project_folder_only_cb.setChecked(bool(self.config.get("mindmap.adobe_project_folder_only", True)))
        self.max_depth_spin.setValue(int(self.config.get("mindmap.max_depth", 48)))
        self.max_files_spin.setValue(int(self.config.get("mindmap.max_files_per_folder", 16)))
        log_idx = self.log_level_combo.findData(str(self.config.get("log.level", "warning")).lower())
        self.log_level_combo.setCurrentIndex(max(log_idx, 0))
        self.log_keep_days_spin.setValue(int(self.config.get("log.keep_days", 7)))
        self.log_max_size_spin.setValue(int(self.config.get("log.max_size_mb", 64)))
        if hasattr(self, "log_size_label"):
            try:
                self.log_size_label.setText(f"現在のログサイズ: {format_bytes(log_total_size(), 2)}")
            except Exception:
                self.log_size_label.setText("現在のログサイズ: 取得できません")
        freq = self.config.get("other.update_check_frequency", "daily")
        idx = self.update_freq_combo.findData(freq)
        self.update_freq_combo.setCurrentIndex(max(idx, 0))
        self.last_check_label.setText(str(self.config.get("other.last_update_check", "未確認") or "未確認"))
        self.group_tab.reload()
        self.purpose_tab.reload()
        self.memo_tab.reload()

    def _browse_config_path(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "設定ファイルを選択", self.config_path_edit.text(), "Text files (*.txt);;All files (*.*)")
        if path:
            self.config_path_edit.setText(path)

    def _load_external_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "設定ファイルを読み込む", str(Path.home()), "Text files (*.txt);;All files (*.*)")
        if not path:
            return
        if self.config.load_from_file_merge(path):
            self._load_values()
            QMessageBox.information(self, "読み込み完了", "使える設定項目を現在の設定に取り込みました。")
        else:
            QMessageBox.warning(self, "読み込み失敗", "設定ファイルを読み込めませんでした。")

    def _browse_naotu_path(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "DesktopNaotuを選択", str(Path.home()), "Executable (*.exe);;All files (*.*)")
        if path:
            self.naotu_path_edit.setText(path)

    def _open_logs(self) -> None:
        try:
            open_log_folder()
        except Exception as exc:
            QMessageBox.warning(self, "ログ", f"ログフォルダを開けませんでした。\n{exc}")

    def _delete_logs(self) -> None:
        reply = QMessageBox.warning(
            self,
            "ログを全部削除",
            "すべてのログファイルを削除します。\n本当に続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        count = delete_all_logs()
        configure_logging(self.config)
        if hasattr(self, "log_size_label"):
            self.log_size_label.setText(f"現在のログサイズ: {format_bytes(log_total_size(), 2)}")
        QMessageBox.information(self, "ログ削除", f"削除したログファイル: {count} 件")

    def _check_now(self) -> None:
        self.check_now_button.setEnabled(False)
        try:
            result = check_latest_release()
            self.config.set("other.last_update_check", today_iso())
            self.last_check_label.setText(today_iso())
            if result.ok and result.has_update:
                QMessageBox.information(self, "更新があります", f"新しいバージョンがあります: {result.latest_version}")
            else:
                QMessageBox.information(self, "更新確認", result.message or "新しいバージョンはありません。")
        finally:
            self.check_now_button.setEnabled(True)

    def _reset_update_notice(self) -> None:
        reply = QMessageBox.question(
            self,
            "バージョン提示をリセット",
            "今日は提示しない設定と、提示しないバージョンの記録を削除します。\n続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.config.set("other.suppress_update_date", "")
        self.config.set("other.skip_version", "")
        QMessageBox.information(self, "リセット完了", "バージョン提示の抑制設定をリセットしました。")

    def _reset_all_settings(self) -> None:
        reply = QMessageBox.warning(
            self,
            "すべての設定を初期化",
            "すべての設定を初期値に戻します。\nグループ、用途、メモ、列設定、更新提示の記録も初期化されます。\n本当に続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self.config.settings = deepcopy(DEFAULT_SETTINGS)
        self._settings_backup = deepcopy(self.config.settings)
        self._load_values()
        QMessageBox.information(self, "初期化完了", "すべての設定を初期値に戻しました。保存を押すと設定ファイルに反映されます。")

    def _reset_current_tab(self) -> None:
        index = self.tabs.currentIndex()
        tab_name = self.tabs.tabText(index)
        reply = QMessageBox.warning(self, "初期値に戻す", f"「{tab_name}」タブの設定を初期値に戻します。\n本当に続行しますか？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        if tab_name == "基本設定":
            self.config.settings["basic"] = deepcopy(DEFAULT_SETTINGS["basic"])
        elif tab_name == "DesktopNaotu":
            self.config.settings["desktop_naotu"] = deepcopy(DEFAULT_SETTINGS["desktop_naotu"])
        elif tab_name == "マインドマップ":
            self.config.settings["mindmap"] = deepcopy(DEFAULT_SETTINGS["mindmap"])
        elif tab_name == "グループ":
            self.config.settings.setdefault("catalogs", {})["groups"] = {}
            for note in self.config.settings.get("drive_notes", {}).values():
                note["group"] = ""
        elif tab_name == "用途管理":
            self.config.settings.setdefault("catalogs", {})["purposes"] = []
            for note in self.config.settings.get("drive_notes", {}).values():
                note["purpose"] = ""
        elif tab_name == "メモ管理":
            self.config.settings.setdefault("catalogs", {})["memos"] = []
            for note in self.config.settings.get("drive_notes", {}).values():
                note["memo"] = ""
        elif tab_name == "ログ":
            self.config.settings["log"] = deepcopy(DEFAULT_SETTINGS["log"])
        elif tab_name == "その他":
            self.config.settings["other"] = deepcopy(DEFAULT_SETTINGS["other"])
        self._load_values()

    def accept(self) -> None:
        self.config.set_config_file_path(self.config_path_edit.text().strip())
        self.config.set("basic.refresh_interval_seconds", self.refresh_spin.value())
        self.config.set("basic.autosave_minutes", self.autosave_spin.value())
        self.config.set("basic.capacity_decimals", self.capacity_decimals_spin.value())
        self.config.set("basic.percent_decimals", self.percent_decimals_spin.value())
        self.config.set("basic.language", self.language_combo.currentData())
        self.config.set("basic.theme", self.theme_combo.currentData())
        self.config.set("basic.treat_system_disk_as_internal", self.system_disk_internal_cb.isChecked())
        self.config.set("basic.show_esp_partitions", self.show_esp_cb.isChecked())
        self.config.set("basic.show_msr_partitions", self.show_msr_cb.isChecked())
        self.config.set("basic.show_oem_partitions", self.show_oem_cb.isChecked())
        self.config.set("basic.show_readonly_partitions", self.show_ro_cb.isChecked())
        self.config.set("basic.show_hidden_partitions", self.show_hidden_partition_cb.isChecked())
        self.config.set("basic.show_ram_disks", self.show_ram_disks_cb.isChecked())
        self.config.set("basic.show_web_disks", self.show_web_disks_cb.isChecked())
        self.config.set("basic.show_remote_disks", self.show_remote_disks_cb.isChecked())
        self.config.set("basic.run_as_admin", self.run_as_admin_cb.isChecked())
        self.config.set("desktop_naotu.exe_path", self.naotu_path_edit.text().strip())
        excludes = [line.strip() for line in self.exclude_text.toPlainText().splitlines() if line.strip()]
        self.config.set("mindmap.exclude_names", excludes)
        self.config.set("mindmap.include_hidden", self.include_hidden_cb.isChecked())
        self.config.set("mindmap.mark_hidden", self.mark_hidden_cb.isChecked())
        self.config.set("mindmap.include_system", self.include_system_cb.isChecked())
        self.config.set("mindmap.include_files", self.include_files_cb.isChecked())
        self.config.set("mindmap.include_extensions", self.include_extensions_cb.isChecked())
        self.config.set("mindmap.output_device_name", self.output_device_name_cb.isChecked())
        self.config.set("mindmap.include_program_folders", self.include_program_folders_cb.isChecked())
        self.config.set("mindmap.adobe_project_folder_only", self.adobe_project_folder_only_cb.isChecked())
        self.config.set("mindmap.max_depth", self.max_depth_spin.value())
        self.config.set("mindmap.max_files_per_folder", self.max_files_spin.value())
        self.config.set("log.level", self.log_level_combo.currentData())
        self.config.set("log.keep_days", self.log_keep_days_spin.value())
        self.config.set("log.max_size_mb", self.log_max_size_spin.value())
        self.config.set("other.update_check_frequency", self.update_freq_combo.currentData())
        self.config.save()
        configure_logging(self.config)
        super().accept()

    def reject(self) -> None:
        self.config.settings = deepcopy(self._settings_backup)
        super().reject()
