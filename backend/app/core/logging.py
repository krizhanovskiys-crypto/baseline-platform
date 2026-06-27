"""Structured logging configuration for the entire application."""
import logging
import sys

from backend.app.core.config import get_settings


def setup_logging() -> None:
    """Configure root logger based on settings.

    Call once at application startup (both bot and API entrypoints).
    """
    settings = get_settings()
    level = getattr(logging, settings.log_level, logging.INFO)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=date_fmt,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Quieten noisy third-party loggers
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )
