from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication, theme: str) -> None:
    """DriveMind の lightmode / darkmode を適用します。"""
    app.setStyle("Fusion")
    if theme == "light":
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet("")
        return

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(37, 37, 38))
    palette.setColor(QPalette.WindowText, QColor(240, 240, 240))
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.AlternateBase, QColor(45, 45, 48))
    palette.setColor(QPalette.ToolTipBase, QColor(250, 250, 250))
    palette.setColor(QPalette.ToolTipText, QColor(20, 20, 20))
    palette.setColor(QPalette.Text, QColor(240, 240, 240))
    palette.setColor(QPalette.Button, QColor(45, 45, 48))
    palette.setColor(QPalette.ButtonText, QColor(240, 240, 240))
    palette.setColor(QPalette.BrightText, QColor(255, 80, 80))
    palette.setColor(QPalette.Highlight, QColor(0, 122, 204))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.Link, QColor(80, 180, 255))
    app.setPalette(palette)
    app.setStyleSheet(
        "QMenuBar, QMenu { background-color: #2d2d30; color: #f0f0f0; }"
        "QMenuBar::item:selected, QMenu::item:selected { background-color: #3e3e42; }"
        "QToolButton, QPushButton, QComboBox { padding: 4px 8px; }"
        "QHeaderView::section { background-color: #3e3e42; color: #f0f0f0; padding: 4px; border: 1px solid #555; }"
    )
