"""Ротация User-Agent для снижения вероятности блокировки."""
from __future__ import annotations

import random

# Статический пул современных десктопных User-Agent'ов.
# Используется как fallback, если библиотека fake-useragent недоступна.
_FALLBACK_AGENTS: tuple[str, ...] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
)

try:
    from fake_useragent import UserAgent

    _ua = UserAgent(fallback=_FALLBACK_AGENTS[0])
except Exception:  # noqa: BLE001 — библиотека опциональна
    _ua = None


def random_user_agent() -> str:
    """Возвращает случайный User-Agent."""
    if _ua is not None:
        try:
            return _ua.random
        except Exception:  # noqa: BLE001
            pass
    return random.choice(_FALLBACK_AGENTS)


def default_headers() -> dict[str, str]:
    """Базовый набор заголовков, похожий на реальный браузер."""
    return {
        "User-Agent": random_user_agent(),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


__all__ = ["random_user_agent", "default_headers"]
