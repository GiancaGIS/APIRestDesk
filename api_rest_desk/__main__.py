from __future__ import annotations

import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from api_rest_desk.config import APP_NAME, APP_VERSION
from api_rest_desk.main_window import RestClientWindow
from api_rest_desk.resources import app_icon_path


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    icon = QIcon(app_icon_path())
    app.setWindowIcon(icon)
    window = RestClientWindow()
    window.setWindowIcon(icon)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
