"""Реестр парсеров бирж.

Позволяет получать парсеры по идентификатору источника, не завязываясь на
конкретные классы (Open/Closed: добавление новой биржи — это новый класс +
одна строка в реестре).
"""
from __future__ import annotations

from parsers.base import BaseParser
from parsers.dto import Project
from parsers.flru import FlRuParser
from parsers.kwork import KworkParser
from parsers.youdo import YouDoParser
from utils.http import HttpClient

# source_id -> класс парсера
PARSER_REGISTRY: dict[str, type[BaseParser]] = {
    KworkParser.source_id: KworkParser,
    YouDoParser.source_id: YouDoParser,
    FlRuParser.source_id: FlRuParser,
}

# Красивые имена для отображения в интерфейсе бота.
SOURCE_TITLES: dict[str, str] = {
    KworkParser.source_id: KworkParser.source_name,
    YouDoParser.source_id: YouDoParser.source_name,
    FlRuParser.source_id: FlRuParser.source_name,
}


def build_parsers(source_ids: list[str], http: HttpClient) -> list[BaseParser]:
    """Создаёт экземпляры парсеров для указанных источников."""
    parsers: list[BaseParser] = []
    for source_id in source_ids:
        parser_cls = PARSER_REGISTRY.get(source_id)
        if parser_cls is not None:
            parsers.append(parser_cls(http))
    return parsers


__all__ = [
    "BaseParser",
    "Project",
    "PARSER_REGISTRY",
    "SOURCE_TITLES",
    "build_parsers",
    "KworkParser",
    "YouDoParser",
    "FlRuParser",
]
