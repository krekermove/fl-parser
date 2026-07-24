"""Загрузка и валидация конфигурации приложения из окружения (.env)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Загружаем .env из корня проекта (если файл есть).
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


def _get_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class Settings:
    """Неизменяемая конфигурация приложения."""

    bot_token: str

    check_interval_minutes: int = 5
    request_delay_min: float = 1.5
    request_delay_max: float = 4.0
    request_timeout: int = 20
    request_retries: int = 3

    database_url: str = "sqlite+aiosqlite:///./fl_parser.db"
    http_proxy: str | None = None

    log_level: str = "INFO"
    log_file: str = "logs/bot.log"

    use_playwright: bool = False

    # Список поддерживаемых бирж (идентификатор источника).
    available_sources: tuple[str, ...] = field(
        default_factory=lambda: ("kwork", "youdo", "flru")
    )

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "BOT_TOKEN не задан. Скопируйте .env.example в .env и укажите токен бота."
            )

        proxy = os.getenv("HTTP_PROXY", "").strip() or None

        return cls(
            bot_token=token,
            check_interval_minutes=_get_int("CHECK_INTERVAL_MINUTES", 5),
            request_delay_min=_get_float("REQUEST_DELAY_MIN", 1.5),
            request_delay_max=_get_float("REQUEST_DELAY_MAX", 4.0),
            request_timeout=_get_int("REQUEST_TIMEOUT", 20),
            request_retries=_get_int("REQUEST_RETRIES", 3),
            database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fl_parser.db"),
            http_proxy=proxy,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            log_file=os.getenv("LOG_FILE", "logs/bot.log"),
            use_playwright=_get_bool("USE_PLAYWRIGHT", False),
        )


# Единый экземпляр настроек на всё приложение.
# Инициализируется лениво, чтобы импорт модуля не падал без .env (например, в тестах).
try:
    settings: Settings = Settings.from_env()
except RuntimeError:
    settings = None  # type: ignore[assignment]
