"""Базовый интерфейс парсера биржи."""
from __future__ import annotations

import abc

from loguru import logger

from parsers.dto import Project
from utils.http import HttpClient


class BaseParser(abc.ABC):
    """Абстрактный парсер одной биржи.

    Наследники обязаны определить:
      * ``source_id``   — идентификатор источника (совпадает с ключом в БД);
      * ``source_name`` — красивое имя для уведомлений;
      * ``parse``       — метод, возвращающий список Project.

    Класс намеренно ничего не знает о фильтрах и БД (принцип единственной
    ответственности): его задача — только получить и распарсить данные.
    """

    source_id: str = ""
    source_name: str = ""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    @abc.abstractmethod
    async def parse(self) -> list[Project]:
        """Возвращает список свежих заданий. Не должен бросать исключения —
        любые ошибки логируются, наружу отдаётся пустой список."""
        raise NotImplementedError

    async def safe_parse(self) -> list[Project]:
        """Обёртка над parse с перехватом любых исключений.

        Гарантирует, что падение одного парсера не остановит весь цикл
        мониторинга (устойчивость к изменению HTML-разметки и сетевым сбоям).
        """
        try:
            logger.info("[{}] Запуск парсера", self.source_name)
            projects = await self.parse()
            logger.info("[{}] Получено заданий: {}", self.source_name, len(projects))
            return projects
        except Exception as err:  # noqa: BLE001 — намеренно ловим всё
            logger.exception("[{}] Ошибка парсинга: {}", self.source_name, err)
            return []


__all__ = ["BaseParser"]
