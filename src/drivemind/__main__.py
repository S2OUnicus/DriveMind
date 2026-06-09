from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from drivemind.ui.main_window import MainWindow
from drivemind.version import APP_NAME


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("S2OUnicus")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
