from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


def _set_light_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#f4f6f8"))
    palette.setColor(QPalette.WindowText, QColor("#202124"))
    palette.setColor(QPalette.Base, QColor("#ffffff"))
    palette.setColor(QPalette.AlternateBase, QColor("#eef1f5"))
    palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
    palette.setColor(QPalette.ToolTipText, QColor("#202124"))
    palette.setColor(QPalette.Text, QColor("#202124"))
    palette.setColor(QPalette.Button, QColor("#f3f4f6"))
    palette.setColor(QPalette.ButtonText, QColor("#202124"))
    palette.setColor(QPalette.BrightText, QColor("#d32f2f"))
    palette.setColor(QPalette.Highlight, QColor("#1976d2"))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.Link, QColor("#1565c0"))
    palette.setColor(QPalette.Light, QColor("#ffffff"))
    palette.setColor(QPalette.Midlight, QColor("#f2f4f8"))
    palette.setColor(QPalette.Mid, QColor("#d0d7de"))
    palette.setColor(QPalette.Dark, QColor("#8c959f"))
    palette.setColor(QPalette.Shadow, QColor("#6e7781"))
    app.setPalette(palette)


def _set_dark_palette(app: QApplication) -> None:
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
    palette.setColor(QPalette.Light, QColor("#4f4f52"))
    palette.setColor(QPalette.Midlight, QColor("#3e3e42"))
    palette.setColor(QPalette.Mid, QColor("#555555"))
    palette.setColor(QPalette.Dark, QColor("#202020"))
    palette.setColor(QPalette.Shadow, QColor("#101010"))
    app.setPalette(palette)


def apply_theme(app: QApplication, theme: str) -> None:
    """DriveMind の lightmode / darkmode を適用します。

    Qt の標準パレットは OS 側のダーク/ライト設定に引きずられることがあります。
    そのため lightmode でも確実に明るい配色になるよう、DriveMind 側で明示的に
    palette と主要 widget の stylesheet を指定します。
    """
    app.setStyle("Fusion")
    normalized = (theme or "dark").lower()
    if normalized == "light":
        _set_light_palette(app)
        app.setStyleSheet(
            "QWidget { background-color: #f4f6f8; color: #202124; }"
            "QMainWindow, QDialog { background-color: #f4f6f8; color: #202124; }"
            "QMenuBar, QMenu { background-color: #ffffff; color: #202124; border: 1px solid #d0d7de; }"
            "QMenuBar::item { background: transparent; padding: 4px 8px; }"
            "QMenuBar::item:selected, QMenu::item:selected { background-color: #e8f0fe; color: #174ea6; }"
            "QTreeWidget, QTableWidget, QListWidget, QTextEdit, QLineEdit, QComboBox, QSpinBox {"
            " background-color: #ffffff; color: #202124; alternate-background-color: #f2f4f8;"
            " border: 1px solid #d0d7de; selection-background-color: #1976d2; selection-color: #ffffff; }"
            "QTreeWidget::item, QTableWidget::item { padding: 2px; }"
            "QHeaderView::section { background-color: #eaeef3; color: #202124; padding: 4px; border: 1px solid #d0d7de; }"
            "QToolButton, QPushButton { background-color: #f3f4f6; color: #202124; border: 1px solid #c9d1d9; border-radius: 4px; padding: 4px 8px; }"
            "QToolButton:hover, QPushButton:hover { background-color: #eaeef3; }"
            "QToolButton:pressed, QPushButton:pressed { background-color: #dbe3ec; }"
            "QPushButton:disabled, QToolButton:disabled { color: #8c959f; background-color: #eef1f5; }"
            "QTabWidget::pane { border: 1px solid #d0d7de; background: #ffffff; }"
            "QTabBar::tab { background: #eaeef3; color: #202124; border: 1px solid #d0d7de; padding: 6px 12px; }"
            "QTabBar::tab:selected { background: #ffffff; border-bottom-color: #ffffff; }"
            "QScrollBar { background: #f2f4f8; }"
            "QScrollBar::handle { background: #c9d1d9; border-radius: 4px; }"
            "QStatusBar { background: #f4f6f8; color: #202124; }"
        )
        return

    _set_dark_palette(app)
    app.setStyleSheet(
        "QMenuBar, QMenu { background-color: #2d2d30; color: #f0f0f0; border: 1px solid #555; }"
        "QMenuBar::item { background: transparent; padding: 4px 8px; }"
        "QMenuBar::item:selected, QMenu::item:selected { background-color: #3e3e42; }"
        "QTreeWidget, QTableWidget, QListWidget, QTextEdit, QLineEdit, QComboBox, QSpinBox {"
        " background-color: #1e1e1e; color: #f0f0f0; alternate-background-color: #2d2d30;"
        " border: 1px solid #555; selection-background-color: #007acc; selection-color: #ffffff; }"
        "QToolButton, QPushButton { padding: 4px 8px; }"
        "QHeaderView::section { background-color: #3e3e42; color: #f0f0f0; padding: 4px; border: 1px solid #555; }"
        "QTabBar::tab { background: #2d2d30; color: #f0f0f0; border: 1px solid #555; padding: 6px 12px; }"
        "QTabBar::tab:selected { background: #3e3e42; }"
    )
