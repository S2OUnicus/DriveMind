from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
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
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from drivemind.core.config import ConfigManager
from drivemind.core.update_checker import check_latest_release, today_iso


GROUP_COLOR_PALETTE: dict[str, list[str]] = {
    "s": ["#e57373", "#f06292", "#ba68c8", "#64b5f6", "#4dd0e1", "#81c784", "#ffd54f", "#ff8a65"],
    "b": ["#ff8a80", "#ff80ab", "#ea80fc", "#82b1ff", "#84ffff", "#b9f6ca", "#ffff8d", "#ffd180"],
    "v": ["#f44336", "#e91e63", "#9c27b0", "#2196f3", "#00bcd4", "#4caf50", "#ffc107", "#ff5722"],
    "ltg": ["#d7ccc8", "#cfd8dc", "#d1c4e9", "#bbdefb", "#b2dfdb", "#c8e6c9", "#f0f4c3", "#ffe0b2"],
}


def _contrast_text_color(color: QColor) -> str:
    luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
    return "#141414" if luminance >= 0.55 else "#f5f5f5"


class GroupManagerTab(QWidget):
    def __init__(self, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self.config = config
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
        right.addStretch(1)
        body.addLayout(right, 2)
        root.addLayout(body, 1)
        self.reload()

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

    def current_name(self) -> str:
        item = self.list_widget.currentItem()
        return item.text().strip() if item else ""

    def _on_current_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        name = current.text().strip() if current else ""
        self.name_edit.setText(name)
        self.current_color = self.config.group_color(name) if name else ""
        self._update_preview()

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


class TextCatalogTab(QWidget):
    def __init__(self, config: ConfigManager, kind: str, title: str, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.kind = kind
        self.title = title
        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"{title}の既存内容を管理します。削除した内容を使っているパーティションは空欄に戻ります。", self))
        self.list_widget = QListWidget(self)
        root.addWidget(self.list_widget, 1)
        row = QHBoxLayout()
        add_button = QPushButton("追加", self)
        rename_button = QPushButton("名前変更", self)
        delete_button = QPushButton("削除", self)
        add_button.clicked.connect(self._add)
        rename_button.clicked.connect(self._rename)
        delete_button.clicked.connect(self._delete)
        row.addWidget(add_button)
        row.addWidget(rename_button)
        row.addWidget(delete_button)
        row.addStretch(1)
        root.addLayout(row)
        self.reload()

    def _values(self) -> list[str]:
        return self.config.known_purposes() if self.kind == "purpose" else self.config.known_memos()

    def reload(self) -> None:
        current = self.current_value()
        self.list_widget.clear()
        for value in self._values():
            item = QListWidgetItem(value)
            self.list_widget.addItem(item)
            if value == current:
                self.list_widget.setCurrentItem(item)
        if self.list_widget.count() and self.list_widget.currentRow() < 0:
            self.list_widget.setCurrentRow(0)

    def current_value(self) -> str:
        item = self.list_widget.currentItem()
        return item.text().strip() if item else ""

    def _add(self) -> None:
        value, ok = QInputDialog.getText(self, f"{self.title}追加", f"{self.title}")
        if not ok or not value.strip():
            return
        if self.kind == "purpose":
            self.config.add_purpose(value.strip())
        else:
            self.config.add_memo(value.strip())
        self.reload()

    def _rename(self) -> None:
        old_value = self.current_value()
        if not old_value:
            return
        new_value, ok = QInputDialog.getText(self, f"{self.title}名前変更", f"{self.title}", text=old_value)
        if not ok or not new_value.strip() or new_value.strip() == old_value:
            return
        # 名前変更は、旧内容を使っているパーティションも新内容へ移します。
        new_value = new_value.strip()
        if self.kind == "purpose":
            self.config.add_purpose(new_value)
            for note in self.config.settings.get("drive_notes", {}).values():
                if str(note.get("purpose", "")).strip() == old_value:
                    note["purpose"] = new_value
            self.config.remove_purpose(old_value)
            self.config.add_purpose(new_value)
        else:
            self.config.add_memo(new_value)
            for note in self.config.settings.get("drive_notes", {}).values():
                if str(note.get("memo", "")).strip() == old_value:
                    note["memo"] = new_value
            self.config.remove_memo(old_value)
            self.config.add_memo(new_value)
        self.reload()

    def _delete(self) -> None:
        value = self.current_value()
        if not value:
            return
        reply = QMessageBox.question(
            self,
            f"{self.title}削除",
            f"「{value}」を削除します。\nこの内容を使っているすべてのパーティションの{self.title}設定は空欄に戻ります。\n続行しますか？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        changed = self.config.remove_purpose(value) if self.kind == "purpose" else self.config.remove_memo(value)
        self.reload()
        QMessageBox.information(self, "削除完了", f"削除しました。\n初期値に戻したパーティション: {changed} 件")


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self._settings_backup = deepcopy(config.settings)
        self.setWindowTitle("設定 - DriveMind")
        self.resize(760, 580)

        root = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        root.addWidget(self.tabs)

        self._build_basic_tab()
        self._build_naotu_tab()
        self._build_mindmap_tab()
        self.group_tab = GroupManagerTab(self.config, self)
        self.purpose_tab = TextCatalogTab(self.config, "purpose", "用途", self)
        self.memo_tab = TextCatalogTab(self.config, "memo", "メモ", self)
        self.tabs.addTab(self.group_tab, "グループ")
        self.tabs.addTab(self.purpose_tab, "用途管理")
        self.tabs.addTab(self.memo_tab, "メモ管理")
        self._build_other_tab()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        buttons.button(QDialogButtonBox.Ok).setText("保存")
        buttons.button(QDialogButtonBox.Cancel).setText("キャンセル")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

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

        self.system_disk_internal_cb = QCheckBox("システムパーティションが存在するディスクを内部ドライブとして扱う", tab)
        form.addRow("内部/外部判定", self.system_disk_internal_cb)

        self.show_esp_cb = QCheckBox("ESP パーティションを表示する", tab)
        self.show_msr_cb = QCheckBox("MSR パーティションを表示する", tab)
        self.show_oem_cb = QCheckBox("OEM パーティションを表示する", tab)
        form.addRow("特殊パーティション", self.show_esp_cb)
        form.addRow("", self.show_msr_cb)
        form.addRow("", self.show_oem_cb)

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

        self.skip_version_edit = QLineEdit(tab)
        self.skip_version_edit.setPlaceholderText("例: v1.2.0")
        form.addRow("提示しないバージョン", self.skip_version_edit)

        self.last_check_label = QLabel("未確認", tab)
        form.addRow("最後の確認日", self.last_check_label)

        layout.addLayout(form)
        self.check_now_button = QPushButton("今すぐ更新確認", tab)
        self.check_now_button.clicked.connect(self._check_now)
        layout.addWidget(self.check_now_button, alignment=Qt.AlignLeft)
        layout.addStretch(1)
        self.tabs.addTab(tab, "その他")

    def _load_values(self) -> None:
        self.refresh_spin.setValue(int(self.config.get("basic.refresh_interval_seconds", 180)))
        self.autosave_spin.setValue(int(self.config.get("basic.autosave_minutes", 5)))
        self.capacity_decimals_spin.setValue(int(self.config.get("basic.capacity_decimals", 2)))
        self.percent_decimals_spin.setValue(int(self.config.get("basic.percent_decimals", 2)))
        self.system_disk_internal_cb.setChecked(bool(self.config.get("basic.treat_system_disk_as_internal", True)))
        self.show_esp_cb.setChecked(bool(self.config.get("basic.show_esp_partitions", False)))
        self.show_msr_cb.setChecked(bool(self.config.get("basic.show_msr_partitions", False)))
        self.show_oem_cb.setChecked(bool(self.config.get("basic.show_oem_partitions", False)))
        self.run_as_admin_cb.setChecked(bool(self.config.get("basic.run_as_admin", False)))
        self.config_path_edit.setText(str(self.config.path))
        self.naotu_path_edit.setText(str(self.config.get("desktop_naotu.exe_path", "")))
        self.exclude_text.setPlainText("\n".join(self.config.get("mindmap.exclude_names", [])))
        self.include_hidden_cb.setChecked(bool(self.config.get("mindmap.include_hidden", True)))
        self.mark_hidden_cb.setChecked(bool(self.config.get("mindmap.mark_hidden", True)))
        self.include_system_cb.setChecked(bool(self.config.get("mindmap.include_system", False)))
        self.include_files_cb.setChecked(bool(self.config.get("mindmap.include_files", False)))
        self.include_extensions_cb.setChecked(bool(self.config.get("mindmap.include_extensions", True)))
        self.max_depth_spin.setValue(int(self.config.get("mindmap.max_depth", 48)))
        self.max_files_spin.setValue(int(self.config.get("mindmap.max_files_per_folder", 16)))
        freq = self.config.get("other.update_check_frequency", "daily")
        idx = self.update_freq_combo.findData(freq)
        self.update_freq_combo.setCurrentIndex(max(idx, 0))
        self.skip_version_edit.setText(str(self.config.get("other.skip_version", "")))
        self.last_check_label.setText(str(self.config.get("other.last_update_check", "未確認") or "未確認"))

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
            self.group_tab.reload()
            self.purpose_tab.reload()
            self.memo_tab.reload()
            QMessageBox.information(self, "読み込み完了", "使える設定項目を現在の設定に取り込みました。")
        else:
            QMessageBox.warning(self, "読み込み失敗", "設定ファイルを読み込めませんでした。")

    def _browse_naotu_path(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "DesktopNaotuを選択", str(Path.home()), "Executable (*.exe);;All files (*.*)")
        if path:
            self.naotu_path_edit.setText(path)

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

    def accept(self) -> None:
        self.config.set_config_file_path(self.config_path_edit.text().strip())
        self.config.set("basic.refresh_interval_seconds", self.refresh_spin.value())
        self.config.set("basic.autosave_minutes", self.autosave_spin.value())
        self.config.set("basic.capacity_decimals", self.capacity_decimals_spin.value())
        self.config.set("basic.percent_decimals", self.percent_decimals_spin.value())
        self.config.set("basic.treat_system_disk_as_internal", self.system_disk_internal_cb.isChecked())
        self.config.set("basic.show_esp_partitions", self.show_esp_cb.isChecked())
        self.config.set("basic.show_msr_partitions", self.show_msr_cb.isChecked())
        self.config.set("basic.show_oem_partitions", self.show_oem_cb.isChecked())
        self.config.set("basic.run_as_admin", self.run_as_admin_cb.isChecked())
        self.config.set("desktop_naotu.exe_path", self.naotu_path_edit.text().strip())
        excludes = [line.strip() for line in self.exclude_text.toPlainText().splitlines() if line.strip()]
        self.config.set("mindmap.exclude_names", excludes)
        self.config.set("mindmap.include_hidden", self.include_hidden_cb.isChecked())
        self.config.set("mindmap.mark_hidden", self.mark_hidden_cb.isChecked())
        self.config.set("mindmap.include_system", self.include_system_cb.isChecked())
        self.config.set("mindmap.include_files", self.include_files_cb.isChecked())
        self.config.set("mindmap.include_extensions", self.include_extensions_cb.isChecked())
        self.config.set("mindmap.max_depth", self.max_depth_spin.value())
        self.config.set("mindmap.max_files_per_folder", self.max_files_spin.value())
        self.config.set("other.update_check_frequency", self.update_freq_combo.currentData())
        self.config.set("other.skip_version", self.skip_version_edit.text().strip())
        self.config.save()
        super().accept()

    def reject(self) -> None:
        self.config.settings = deepcopy(self._settings_backup)
        super().reject()
