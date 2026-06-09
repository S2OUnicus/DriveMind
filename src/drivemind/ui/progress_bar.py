from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPalette, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from drivemind.core.formatting import format_bytes, format_percent


def _contrast_text_color(background: QColor) -> QColor:
    luminance = (0.299 * background.red() + 0.587 * background.green() + 0.114 * background.blue()) / 255
    return QColor(20, 20, 20) if luminance >= 0.55 else QColor(245, 245, 245)


class DiskUsageBar(QWidget):
    """DriveMind専用の容量表示バーです。"""

    def __init__(self, used: int = 0, free: int = 0, total: int = 0, decimals: int = 2, percent_decimals: int = 2, parent=None) -> None:
        super().__init__(parent)
        self.used = used
        self.free = free
        self.total = total
        self.decimals = decimals
        self.percent_decimals = percent_decimals
        self.setMinimumHeight(26)
        self.setMinimumWidth(220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_values(self, used: int, free: int, total: int, decimals: int | None = None, percent_decimals: int | None = None) -> None:
        self.used = int(used or 0)
        self.free = int(free or 0)
        self.total = int(total or 0)
        if decimals is not None:
            self.decimals = decimals
        if percent_decimals is not None:
            self.percent_decimals = percent_decimals
        self.update()

    def _used_color(self) -> QColor:
        if self.total <= 0:
            return QColor(220, 220, 220)
        free_ratio = max(0.0, min(1.0, self.free / self.total))
        if free_ratio >= 0.50:
            return QColor(188, 240, 180)  # 浅い緑
        if free_ratio >= 0.25:
            return QColor(250, 236, 156)  # 浅い黄色
        if free_ratio >= 0.12:
            return QColor(248, 178, 178)  # 浅い赤
        return QColor(218, 190, 244)      # 浅い紫

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(2, 3, -2, -3)
        if rect.width() <= 10 or rect.height() <= 4:
            return

        total_label_width = max(110, int(rect.width() * 0.18))
        bar_rect = rect.adjusted(0, 0, -total_label_width, 0)
        radius = 5

        border_color = self.palette().color(QPalette.Mid)
        painter.setPen(QPen(border_color, 2))
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(bar_rect, radius, radius)

        used_ratio = 0.0 if self.total <= 0 else max(0.0, min(1.0, self.used / self.total))
        fill_width = int((bar_rect.width() - 3) * used_ratio)
        used_color = self._used_color()
        if fill_width > 0:
            fill_rect = bar_rect.adjusted(2, 2, -bar_rect.width() + fill_width + 1, -2)
            painter.setPen(Qt.NoPen)
            painter.setBrush(used_color)
            painter.drawRoundedRect(fill_rect, radius - 2, radius - 2)

        fm = QFontMetrics(painter.font())
        percent = 0 if self.total <= 0 else self.used / self.total * 100
        left_text = format_bytes(self.used, self.decimals)
        center_text = format_percent(percent, self.percent_decimals)
        right_text = format_bytes(self.free, self.decimals)
        total_text = format_bytes(self.total, self.decimals)

        y = bar_rect.center().y() + fm.ascent() // 2 - 1
        # バー内部は白背景/浅色背景なので、読みやすい濃色を使います。
        painter.setPen(QColor(20, 20, 20))
        painter.drawText(bar_rect.left() + 10, y, left_text)
        painter.drawText(bar_rect.center().x() - fm.horizontalAdvance(center_text) // 2, y, center_text)
        painter.drawText(bar_rect.right() - fm.horizontalAdvance(right_text) - 10, y, right_text)

        # バー外の総容量文字は、ダークモードでも見えるように現在テーマの文字色を使います。
        painter.setPen(self.palette().color(QPalette.WindowText))
        painter.drawText(bar_rect.right() + 18, y, total_text)
