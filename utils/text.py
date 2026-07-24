"""Утилиты для работы с текстом: парсинг бюджета, обрезка описаний."""
from __future__ import annotations

import re

_DIGITS_RE = re.compile(r"\d[\d\s ]*")


def parse_budget(raw: str | None) -> int | None:
    """Извлекает числовое значение бюджета из произвольной строки.

    Примеры:
        "25 000 ₽"        -> 25000
        "от 5000 руб."    -> 5000
        "договорная"      -> None
        "1 500 – 3 000 ₽" -> 1500  (берётся первое число)
    """
    if not raw:
        return None

    match = _DIGITS_RE.search(raw)
    if not match:
        return None

    cleaned = re.sub(r"[\s ]", "", match.group())
    try:
        return int(cleaned)
    except ValueError:
        return None


def truncate(text: str | None, limit: int = 500) -> str:
    """Обрезает текст до limit символов, добавляя многоточие."""
    if not text:
        return ""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


__all__ = ["parse_budget", "truncate"]
