from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, QThread, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QAbstractItemView,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from drivemind.core.config import ConfigManager
from drivemind.core.formatting import format_bytes, format_percent
from drivemind.core.models import DeviceInfo, VolumeInfo
from drivemind.core.mindmap import path_flags


CATEGORY_EXTENSIONS: dict[str, set[str]] = {
    "ドキュメント": {
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".pdf", ".md", ".csv", ".json", ".xml", ".html", ".htm",
    },
    "音楽": {".mp3", ".aac", ".ogg", ".flac", ".wav", ".m4a", ".wma", ".opus", ".aiff"},
    "ビデオ": {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".m4v", ".ts"},
    "プログラム": {".exe", ".msi", ".dll", ".sys", ".bat", ".cmd", ".ps1", ".vbs", ".jar", ".py", ".js", ".ts", ".sh", ".app"},
}
CATEGORY_COLORS: dict[str, str] = {
    "ドキュメント": "#64b5f6",
    "音楽": "#81c784",
    "ビデオ": "#ffb74d",
    "プログラム": "#ba68c8",
    "その他": "#b0bec5",
}


def _category_for(path: Path) -> str:
    suffix = path.suffix.lower()
    for category, suffixes in CATEGORY_EXTENSIONS.items():
        if suffix in suffixes:
            return category
    return "その他"


class UsagePolarWidget(QWidget):
    def __init__(self, volume: VolumeInfo, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self.volume = volume
        self.config = config
        self.setMinimumSize(210, 210)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(18, 18, -18, -18)
        used_ratio = 0.0 if self.volume.total <= 0 else max(0.0, min(1.0, self.volume.used / self.volume.total))
        free_ratio = 1.0 - used_ratio

        bg_pen = QPen(QColor("#d7d7d7"), 18, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, 90 * 16, -360 * 16)

        if free_ratio >= 0.50:
            used_color = QColor("#bcefb4")
        elif free_ratio >= 0.25:
            used_color = QColor("#faec9c")
        elif free_ratio >= 0.12:
            used_color = QColor("#f8b2b2")
        else:
            used_color = QColor("#dabef4")
        painter.setPen(QPen(used_color, 18, Qt.SolidLine, Qt.RoundCap))
        painter.drawArc(rect, 90 * 16, int(-360 * used_ratio * 16))

        painter.setPen(self.palette().color(self.foregroundRole()))
        percent_decimals = int(self.config.get("basic.percent_decimals", 2))
        decimals = int(self.config.get("basic.capacity_decimals", 2))
        percent = self.volume.percent
        painter.drawText(rect, Qt.AlignCenter, f"{format_percent(percent, percent_decimals)}\n{format_bytes(self.volume.used, decimals)} / {format_bytes(self.volume.total, decimals)}")


class PiePadWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.values: dict[str, int] = {}
        self.setMinimumSize(260, 240)

    def set_values(self, values: dict[str, int]) -> None:
        self.values = dict(values)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(20, 20, -20, -20)
        total = sum(v for v in self.values.values() if v > 0)
        if total <= 0:
            painter.setPen(self.palette().color(self.foregroundRole()))
            painter.drawText(rect, Qt.AlignCenter, "分析結果なし")
            return
        start = 90.0
        pad = 2.0
        for name, value in self.values.items():
            if value <= 0:
                continue
            span = max(0.0, 360.0 * value / total - pad)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(CATEGORY_COLORS.get(name, "#b0bec5")))
            painter.drawPie(rect, int(start * 16), int(-span * 16))
            start -= span + pad




def _foreground_for_background(color_hex: str) -> str:
    color = QColor(color_hex)
    # W3C系の相対輝度に近い簡易計算。明るい背景なら黒、暗い背景なら白にする。
    luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255.0
    return "#141414" if luminance >= 0.62 else "#ffffff"


class CategoryCard(QFrame):
    openRequested = Signal(str)

    def __init__(self, category: str, summary_text: str, color_hex: str, parent=None) -> None:
        super().__init__(parent)
        self.category = category
        self.setObjectName("categoryCard")
        self.setCursor(Qt.PointingHandCursor)
        fg = _foreground_for_background(color_hex)
        border = QColor(color_hex).darker(115).name()
        self.setStyleSheet(
            "QFrame#categoryCard {"
            f"background-color: {color_hex};"
            f"color: {fg};"
            f"border: 1px solid {border};"
            "border-radius: 12px;"
            "}"
            "QPushButton {"
            "background-color: rgba(255, 255, 255, 0.82);"
            "color: #202020;"
            "border: 1px solid rgba(0, 0, 0, 0.18);"
            "border-radius: 8px;"
            "padding: 4px 8px;"
            "}"
            "QPushButton:hover { background-color: rgba(255, 255, 255, 0.95); }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(8)
        label = QLabel(summary_text, self)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {fg};")
        layout.addWidget(label, 1)
        button = QPushButton("ファイルリスト", self)
        button.clicked.connect(lambda: self.openRequested.emit(self.category))
        layout.addWidget(button, 0)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.openRequested.emit(self.category)
        super().mouseDoubleClickEvent(event)

class FileAnalysisWorker(QObject):
    finished = Signal(object, object, object)

    def __init__(self, root: str) -> None:
        super().__init__()
        self.root = root

    def run(self) -> None:
        totals = {name: 0 for name in CATEGORY_COLORS}
        files_by_category: dict[str, list[tuple[str, int]]] = {name: [] for name in CATEGORY_COLORS}
        errors: list[str] = []
        root_path = Path(self.root)
        stack = [root_path]
        seen: set[str] = set()
        while stack:
            folder = stack.pop()
            try:
                resolved = str(folder.resolve())
            except Exception:
                resolved = str(folder)
            if resolved in seen:
                continue
            seen.add(resolved)
            try:
                entries = list(folder.iterdir())
            except PermissionError:
                errors.append(f"権限不足: {folder}")
                continue
            except (FileNotFoundError, OSError) as exc:
                errors.append(f"読み取り不可: {folder} ({exc})")
                continue
            for entry in entries:
                try:
                    flags = path_flags(entry)
                    if flags.symlink:
                        continue
                    if entry.is_dir():
                        stack.append(entry)
                    elif entry.is_file():
                        category = _category_for(entry)
                        try:
                            size = entry.stat().st_size
                            totals[category] += size
                            files_by_category.setdefault(category, []).append((str(entry), int(size)))
                        except OSError:
                            errors.append(f"サイズ取得不可: {entry}")
                except OSError as exc:
                    errors.append(f"読み取り不可: {entry} ({exc})")
        self.finished.emit(totals, errors[:200], files_by_category)




class FileListDialog(QDialog):
    PAGE_SIZE = 100

    def __init__(self, category: str, files: list[tuple[str, int]], config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self.category = category
        # 初期表示は分析時に得られた自然な順番のままにする。サイズ順にはしない。
        self._original_files = list(files)
        self.files = list(files)
        self.config = config
        self.current_page = 1
        self._size_sort_desc: bool | None = None
        self._column_width_initialized = False
        self.setWindowTitle(f"ファイルリスト - {category}")
        self.resize(980, 640)
        self._build_ui()
        self._set_loading(True)
        QTimer.singleShot(0, self._render_current_page)

    @property
    def total_pages(self) -> int:
        if not self.files:
            return 1
        return max(1, (len(self.files) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self.note = QLabel(f"{self.category} に分類されたファイル: {len(self.files)} 件", self)
        root.addWidget(self.note)

        self.loading_progress = QProgressBar(self)
        self.loading_progress.setRange(0, 0)
        self.loading_progress.hide()
        root.addWidget(self.loading_progress)

        self.table = QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels(["ファイル", "サイズ"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        root.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.page_area = QHBoxLayout()
        self.page_area.setSpacing(4)
        bottom.addLayout(self.page_area, 1)
        bottom.addStretch(1)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok, self)
        buttons.button(QDialogButtonBox.Ok).setText("閉じる")
        buttons.accepted.connect(self.accept)
        bottom.addWidget(buttons)
        root.addLayout(bottom)

    def _set_loading(self, loading: bool) -> None:
        self.loading_progress.setVisible(loading)
        self.table.setEnabled(not loading)

    def _on_header_clicked(self, section: int) -> None:
        # サイズ列のみソート対象にする。
        if section != 1:
            return
        self._set_loading(True)
        QTimer.singleShot(0, self._toggle_size_sort)

    def _toggle_size_sort(self) -> None:
        self._size_sort_desc = False if self._size_sort_desc is True else True
        self.files = sorted(self._original_files, key=lambda item: item[1], reverse=self._size_sort_desc)
        arrow = "↓" if self._size_sort_desc else "↑"
        self.table.setHorizontalHeaderLabels(["ファイル", f"サイズ {arrow}"])
        self.current_page = 1
        self._render_current_page()

    def _render_current_page(self) -> None:
        self.current_page = max(1, min(self.current_page, self.total_pages))
        self.table.setRowCount(0)
        decimals = int(self.config.get("basic.capacity_decimals", 2))
        start = (self.current_page - 1) * self.PAGE_SIZE
        end = min(start + self.PAGE_SIZE, len(self.files))
        for path, size in self.files[start:end]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            file_item = QTableWidgetItem(path)
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            size_item = QTableWidgetItem(format_bytes(size, decimals))
            size_item.setFlags(size_item.flags() & ~Qt.ItemIsEditable)
            size_item.setData(Qt.UserRole, int(size))
            self.table.setItem(row, 0, file_item)
            self.table.setItem(row, 1, size_item)
        self.note.setText(
            f"{self.category} に分類されたファイル: {len(self.files)} 件  "
            f"/ {self.current_page} / {self.total_pages} ページ  "
            f"/ 1ページ {self.PAGE_SIZE} 件"
        )
        self._update_page_buttons()
        self._apply_initial_column_widths()
        self._set_loading(False)

    def _apply_initial_column_widths(self) -> None:
        if self._column_width_initialized:
            return
        width = max(200, self.table.viewport().width())
        self.table.setColumnWidth(0, int(width * 0.70))
        self.table.setColumnWidth(1, max(120, int(width * 0.28)))
        self._column_width_initialized = True

    def _visible_page_tokens(self) -> list[int | str]:
        total = self.total_pages
        current = self.current_page
        if total <= 8:
            return list(range(1, total + 1))
        if current <= 6:
            return [1, 2, 3, 4, 5, 6, "...", total]
        if current >= total - 5:
            return [1, "...", *range(total - 5, total + 1)]
        return [1, "...", current - 2, current - 1, current, current + 1, current + 2, "...", total]

    def _update_page_buttons(self) -> None:
        while self.page_area.count():
            item = self.page_area.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for token in self._visible_page_tokens():
            button = QPushButton(str(token), self)
            button.setMinimumWidth(30)
            if token == "...":
                button.setToolTip("ページを選択")
                button.clicked.connect(self._choose_page)
            else:
                page = int(token)
                if page == self.current_page:
                    button.setStyleSheet("font-weight: bold; color: #d32f2f;")
                    button.setEnabled(False)
                button.clicked.connect(lambda checked=False, page=page: self._goto_page(page))
            self.page_area.addWidget(button)

    def _choose_page(self) -> None:
        pages = [str(i) for i in range(1, self.total_pages + 1)]
        selected, ok = QInputDialog.getItem(
            self,
            "ページ選択",
            "移動するページを選択してください:",
            pages,
            max(0, self.current_page - 1),
            False,
        )
        if ok and selected:
            self._goto_page(int(selected))

    def _goto_page(self, page: int) -> None:
        self.current_page = max(1, min(page, self.total_pages))
        self._set_loading(True)
        QTimer.singleShot(0, self._render_current_page)


class PartitionInfoDialog(QDialog):
    def __init__(self, device: DeviceInfo, volume: VolumeInfo, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self.device = device
        self.volume = volume
        self.config = config
        self._analysis_thread: QThread | None = None
        self._analysis_worker: FileAnalysisWorker | None = None
        self._files_by_category: dict[str, list[tuple[str, int]]] = {}
        self.setWindowTitle(f"パーティション情報 - {volume.drive}")
        self.resize(900, 680)
        self._build_ui()
        self._load_info()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        body = QWidget(scroll)
        body_layout = QVBoxLayout(body)

        top = QHBoxLayout()
        self.usage_widget = UsagePolarWidget(self.volume, self.config, body)
        top.addWidget(self.usage_widget, 0)
        self.info_table = QTableWidget(0, 2, body)
        self.info_table.setHorizontalHeaderLabels(["項目", "内容"])
        self.info_table.horizontalHeader().setStretchLastSection(True)
        top.addWidget(self.info_table, 1)
        body_layout.addLayout(top)

        line = QFrame(body)
        line.setFrameShape(QFrame.HLine)
        body_layout.addWidget(line)

        self.analysis_status = QLabel("ファイル分析を実行すると、種類別の容量を表示します。", body)
        body_layout.addWidget(self.analysis_status)
        self.analysis_progress = QProgressBar(body)
        self.analysis_progress.setRange(0, 0)
        self.analysis_progress.hide()
        body_layout.addWidget(self.analysis_progress)

        analysis = QHBoxLayout()
        self.pie_widget = PiePadWidget(body)
        analysis.addWidget(self.pie_widget, 1)
        right = QVBoxLayout()
        self.category_scroll = QScrollArea(body)
        self.category_scroll.setWidgetResizable(True)
        self.category_container = QWidget(self.category_scroll)
        self.category_layout = QVBoxLayout(self.category_container)
        self.category_layout.setContentsMargins(6, 6, 6, 6)
        self.category_layout.setSpacing(8)
        self.category_layout.addStretch(1)
        self.category_scroll.setWidget(self.category_container)
        right.addWidget(self.category_scroll, 1)
        analysis.addLayout(right, 1)
        body_layout.addLayout(analysis, 1)

        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        bottom = QHBoxLayout()
        self.analyze_button = QPushButton("ファイル分析", self)
        self.close_button = QPushButton("閉じる", self)
        self.analyze_button.clicked.connect(self._start_analysis)
        self.close_button.clicked.connect(self.accept)
        bottom.addWidget(self.analyze_button)
        bottom.addStretch(1)
        bottom.addWidget(self.close_button)
        root.addLayout(bottom)

    def _add_row(self, key: str, value: str) -> None:
        row = self.info_table.rowCount()
        self.info_table.insertRow(row)
        self.info_table.setItem(row, 0, QTableWidgetItem(key))
        self.info_table.setItem(row, 1, QTableWidgetItem(value))

    def _load_info(self) -> None:
        decimals = int(self.config.get("basic.capacity_decimals", 2))
        percent_decimals = int(self.config.get("basic.percent_decimals", 2))
        rows = [
            ("所属デバイス", self.device.name),
            ("設備順番", str(self.device.index)),
            ("物理ディスク番号", "" if self.device.system_index is None else str(self.device.system_index)),
            ("ドライブ", self.volume.drive),
            ("マウントポイント", self.volume.mountpoint),
            ("ラベル", self.volume.label),
            ("ファイルシステム", self.volume.file_system),
            ("種類", self.device.display_kind),
            ("インターフェース", self.device.interface),
            ("パーティション種類", self.volume.partition_type),
            ("グループ", self.volume.group),
            ("用途", self.volume.purpose),
            ("メモ", self.volume.memo),
            ("属性", ", ".join(self.volume.attributes)),
            ("使用済み", format_bytes(self.volume.used, decimals)),
            ("空き容量", format_bytes(self.volume.free, decimals)),
            ("総容量", format_bytes(self.volume.total, decimals)),
            ("使用率", format_percent(self.volume.percent, percent_decimals)),
            ("UUID/シリアル", self.device.uuid),
        ]
        for key, value in rows:
            self._add_row(key, value)
        self.info_table.resizeColumnsToContents()

    def _start_analysis(self) -> None:
        root = self.volume.mountpoint or self.volume.drive
        if not root:
            QMessageBox.warning(self, "分析不可", "マウントポイントがありません。")
            return
        self.analyze_button.setEnabled(False)
        self.analysis_status.setText("ファイルを分析中です。大きなドライブでは時間がかかります...")
        self.analysis_progress.show()
        self._analysis_thread = QThread(self)
        self._analysis_worker = FileAnalysisWorker(root)
        self._analysis_worker.moveToThread(self._analysis_thread)
        self._analysis_thread.started.connect(self._analysis_worker.run)
        self._analysis_worker.finished.connect(self._on_analysis_finished)
        self._analysis_worker.finished.connect(self._analysis_thread.quit)
        self._analysis_worker.finished.connect(self._analysis_worker.deleteLater)
        self._analysis_thread.finished.connect(self._analysis_thread.deleteLater)
        self._analysis_thread.finished.connect(self._clear_analysis_thread)
        self._analysis_thread.start()

    def _clear_analysis_thread(self) -> None:
        self._analysis_thread = None
        self._analysis_worker = None

    def _clear_category_cards(self) -> None:
        while self.category_layout.count():
            item = self.category_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.category_layout.addStretch(1)

    def _on_analysis_finished(self, totals: dict[str, int], errors: list[str], files_by_category: dict[str, list[tuple[str, int]]]) -> None:
        self.analysis_progress.hide()
        self.analyze_button.setEnabled(True)
        self._files_by_category = files_by_category
        self.pie_widget.set_values(totals)
        self._clear_category_cards()
        total = sum(totals.values())
        decimals = int(self.config.get("basic.capacity_decimals", 2))
        percent_decimals = int(self.config.get("basic.percent_decimals", 2))

        # 「その他」は常に最後。その他以外は容量の大きい順に並べる。
        ordered = sorted(
            [(name, value) for name, value in totals.items() if name != "その他"],
            key=lambda item: item[1],
            reverse=True,
        )
        if "その他" in totals:
            ordered.append(("その他", totals.get("その他", 0)))

        # stretch は最後に置くので、カードは stretch の手前へ挿入する。
        stretch_index = max(0, self.category_layout.count() - 1)
        for name, value in ordered:
            percent = (value / total * 100) if total else 0.0
            file_count = len(files_by_category.get(name, []))
            summary = (
                f"{name}\n"
                f"{format_bytes(value, decimals)}  ({format_percent(percent, percent_decimals)})  "
                f"/ {file_count} 件"
            )
            card = CategoryCard(name, summary, CATEGORY_COLORS.get(name, "#b0bec5"), self.category_container)
            card.openRequested.connect(self._open_category_files)
            self.category_layout.insertWidget(stretch_index, card)
            stretch_index += 1
        msg = f"分析完了: {format_bytes(total, decimals)}"
        if errors:
            msg += f" / 読み取りできなかった項目: {len(errors)} 件"
        self.analysis_status.setText(msg)

    def _open_category_files(self, category: str) -> None:
        files = self._files_by_category.get(category, [])
        if not files:
            QMessageBox.information(self, "ファイルなし", "この項目に表示できるファイルがありません。")
            return
        FileListDialog(category, files, self.config, self).exec()
