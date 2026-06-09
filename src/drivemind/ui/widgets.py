from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QPushButton


class LongPressButton(QPushButton):
    longPressed = Signal()

    def __init__(self, text: str = "", parent=None, long_press_ms: int = 800) -> None:
        super().__init__(text, parent)
        self._long_press_ms = long_press_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._emit_long_press)
        self._long_pressed = False

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self._long_pressed = False
        self._timer.start(self._long_press_ms)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self._timer.isActive():
            self._timer.stop()
            super().mouseReleaseEvent(event)
            return
        if self._long_pressed:
            self.setDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _emit_long_press(self) -> None:
        self._long_pressed = True
        self.longPressed.emit()
