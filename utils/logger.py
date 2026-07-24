"""Настройка логирования на базе loguru."""
from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

_configured = False


def setup_logging(level: str = "INFO", log_file: str = "logs/bot.log") -> None:
    """Настраивает вывод логов в консоль и файл с ротацией.

    Логи в файле хранятся с ротацией по размеру и сжимаются.
    """
    global _configured
    if _configured:
        return

    logger.remove()

    logger.add(
        sys.stderr,
        level=level,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path,
        level=level,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,  # безопасно при работе из нескольких корутин/потоков
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} - {message}"
        ),
    )

    _configured = True
    logger.info("Логирование инициализировано (level=%s, file=%s)" % (level, log_file))


__all__ = ["setup_logging", "logger"]
