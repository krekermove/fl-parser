"""Единая модель задания, возвращаемая всеми парсерами."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Project:
    """Задание с фриланс-биржи.

    Все парсеры обязаны возвращать объекты этого типа.
    """

    title: str
    url: str
    source: str  # человекочитаемое имя биржи, напр. "FL.ru"
    description: str = ""
    budget_raw: str = ""  # исходная строка бюджета ("25 000 ₽", "договорная")
    budget_value: int | None = None  # распарсенное числовое значение
    category: str = ""
    published_at: datetime | None = None
    published_raw: str = ""  # исходная строка даты публикации
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def uid(self) -> str:
        """Стабильный уникальный идентификатор задания для дедупликации.

        Основан на URL — самом надёжном ключе. Если URL пустой, используется
        комбинация источника и заголовка.
        """
        key = self.url.strip() or f"{self.source}:{self.title}".strip()
        return hashlib.sha256(key.encode("utf-8")).hexdigest()


__all__ = ["Project"]
