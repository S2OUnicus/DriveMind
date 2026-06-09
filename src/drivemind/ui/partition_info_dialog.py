from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QRectF, QThread, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
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


class FileAnalysisWorker(QObject):
    finished = Signal(object, object)

    def __init__(self, root: str) -> None:
        super().__init__()
        self.root = root

    def run(self) -> None:
        totals = {name: 0 for name in CATEGORY_COLORS}
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
                            totals[category] += entry.stat().st_size
                        except OSError:
                            errors.append(f"サイズ取得不可: {entry}")
                except OSError as exc:
                    errors.append(f"読み取り不可: {entry} ({exc})")
        self.finished.emit(totals, errors[:200])


class PartitionInfoDialog(QDialog):
    def __init__(self, device: DeviceInfo, volume: VolumeInfo, config: ConfigManager, parent=None) -> None:
        super().__init__(parent)
        self.device = device
        self.volume = volume
        self.config = config
        self._analysis_thread: QThread | None = None
        self._analysis_worker: FileAnalysisWorker | None = None
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
        self.category_list = QListWidget(body)
        right.addWidget(self.category_list, 1)
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

    def _on_analysis_finished(self, totals: dict[str, int], errors: list[str]) -> None:
        self.analysis_progress.hide()
        self.analyze_button.setEnabled(True)
        self.pie_widget.set_values(totals)
        self.category_list.clear()
        total = sum(totals.values())
        decimals = int(self.config.get("basic.capacity_decimals", 2))
        percent_decimals = int(self.config.get("basic.percent_decimals", 2))
        for name, value in sorted(totals.items(), key=lambda item: item[1], reverse=True):
            percent = (value / total * 100) if total else 0.0
            item = QListWidgetItem(f"{name}: {format_bytes(value, decimals)}  ({format_percent(percent, percent_decimals)})")
            item.setBackground(QColor(CATEGORY_COLORS.get(name, "#b0bec5")))
            item.setForeground(QColor("#141414"))
            self.category_list.addItem(item)
        msg = f"分析完了: {format_bytes(total, decimals)}"
        if errors:
            msg += f" / 読み取りできなかった項目: {len(errors)} 件"
        self.analysis_status.setText(msg)
