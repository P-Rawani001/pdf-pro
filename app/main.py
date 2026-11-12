"""Entry point for PDF Pro desktop application."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.config import APP_NAME, APP_ORG, APP_VERSION
from app.services.file_service import FileService
from app.services.logging_service import setup_logging
from app.ui.main_window import MainWindow


def main() -> int:
    logger = setup_logging()
    logger.info("Starting %s v%s", APP_NAME, APP_VERSION)

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    app.setApplicationVersion(APP_VERSION)
    app.setFont(QFont("Segoe UI", 10))

    file_service = FileService()
    window = MainWindow(file_service=file_service)
    window.show()

    exit_code = app.exec()
    logger.info("Exiting %s with code %d", APP_NAME, exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
