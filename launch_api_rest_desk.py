import sys

from PyQt6.QtWidgets import QApplication

from api_rest_desk.config import APP_NAME, APP_VERSION
from api_rest_desk.main_window import RestClientWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    window = RestClientWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
