"""Парсер биржи Kwork (https://kwork.ru).

Раздел «Биржа проектов» (kwork.ru/projects) отдаёт данные внутри JS-переменной
``window.stateData`` — её и парсим (это надёжнее, чем ловить меняющуюся
верстку). Обратите внимание: полный доступ к бирже проектов Kwork требует
авторизации. Для стабильной работы задайте авторизованные cookie через прокси
или включите Playwright-режим (см. README).
"""
from __future__ import annotations

import json
import re

from loguru import logger

from .base import BaseParser
from .dto import Project
from utils.text import parse_budget, truncate

# Костыль: жёстко ограничиваем биржу нужной категорией (c=11 — Разработка).
_LISTING_URL = "https://kwork.ru/projects?c=11"
_BASE_URL = "https://kwork.ru"
_STATE_RE = re.compile(r"window\.stateData\s*=\s*(\{.*?\});", re.DOTALL)


class KworkParser(BaseParser):
    source_id = "kwork"
    source_name = "Kwork"

    async def parse(self) -> list[Project]:
        html = await self._http.get_text(_LISTING_URL)
        if not html:
            logger.warning("[{}] Пустой ответ от {}", self.source_name, _LISTING_URL)
            return []

        match = _STATE_RE.search(html)
        if not match:
            logger.warning(
                "[{}] Не найден stateData — вероятно, требуется авторизация.",
                self.source_name,
            )
            return []

        try:
            state = json.loads(match.group(1))
        except json.JSONDecodeError as err:
            logger.warning("[{}] Не удалось разобрать stateData: {}", self.source_name, err)
            return []

        wants = self._extract_wants(state)
        projects: list[Project] = []
        for want in wants:
            project = self._parse_want(want)
            if project is not None:
                projects.append(project)
        return projects

    @staticmethod
    def _extract_wants(state: dict) -> list:
        """Достаёт список проектов из stateData (ключ 'wants')."""
        node = state.get("wants")
        if isinstance(node, list):
            return node
        if isinstance(node, dict):
            for value in node.values():
                if isinstance(value, list):
                    return value
        # Иногда данные лежат в pagesData / другой обёртке.
        pages = state.get("pagesData") or {}
        if isinstance(pages, dict):
            for value in pages.values():
                if isinstance(value, dict) and isinstance(value.get("wants"), list):
                    return value["wants"]
        return []

    def _parse_want(self, want: dict) -> Project | None:
        if not isinstance(want, dict):
            return None
        title = str(want.get("name") or want.get("title") or "").strip()
        want_id = want.get("id")
        if not title or not want_id:
            return None

        budget_raw = str(
            want.get("priceLimit") or want.get("price") or want.get("budget") or ""
        )
        return Project(
            title=title,
            url=f"{_BASE_URL}/projects/{want_id}/view",
            source=self.source_name,
            description=truncate(str(want.get("description", "")), 800),
            budget_raw=budget_raw,
            budget_value=parse_budget(budget_raw),
            category=str(want.get("category_name") or want.get("categoryName") or ""),
            published_raw=str(want.get("date_confirm") or want.get("dateCreate") or ""),
        )


__all__ = ["KworkParser"]
