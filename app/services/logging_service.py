"""Privacy-safe application logging configuration (never logs PDF contents)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config import LOGS_DIR, ensure_app_directories


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure rotating local file logging and console output."""
    ensure_app_directories()
    logger = logging.getLogger("pdf_pro")
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log_file = LOGS_DIR / "pdf_pro.log"
    file_handler = RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
