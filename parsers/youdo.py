"""Парсер биржи YouDo (https://youdo.com).

Публичный листинг открытых заданий доступен в HTML. YouDo активно использует
JS, поэтому при пустом результате рекомендуется включить Playwright
(USE_PLAYWRIGHT=true) — базовый класс парсинга через браузер описан в
README. Здесь реализован быстрый путь через aiohttp + BeautifulSoup, а также
попытка вытащить встроенный JSON-стейт.
"""
from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup, Tag
from loguru import logger

from parsers.base import BaseParser
from parsers.dto import Project
from utils.text import parse_budget, truncate

_LISTING_URL = "https://youdo.com/tasks-all-opened-all/"
_BASE_URL = "https://youdo.com"
_STATE_RE = re.compile(r"window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});", re.DOTALL)


class YouDoParser(BaseParser):
    source_id = "youdo"
    source_name = "YouDo"

    async def parse(self) -> list[Project]:
        html = await self._http.get_text(_LISTING_URL)
        if not html:
            logger.warning("[{}] Пустой ответ от {}", self.source_name, _LISTING_URL)
            return []

        # Сначала пытаемся распарсить встроенный стейт (надёжнее HTML).
        projects = self._parse_state(html)
        if projects:
            return projects

        # Fallback: HTML-карточки.
        return self._parse_html(html)

    def _parse_state(self, html: str) -> list[Project]:
        match = _STATE_RE.search(html)
        if not match:
            return []
        try:
            state = json.loads(match.group(1))
        except json.JSONDecodeError:
            return []

        # Структура стейта нестабильна — обходим её защищённо.
        tasks = self._dig_tasks(state)
        projects: list[Project] = []
        for task in tasks:
            if not isinstance(task, dict):
                continue
            title = str(task.get("name") or task.get("title") or "").strip()
            task_id = task.get("id") or task.get("taskId")
            if not title or not task_id:
                continue
            budget_raw = str(task.get("priceFormatted") or task.get("price") or "")
            projects.append(
                Project(
                    title=title,
                    url=f"{_BASE_URL}/t{task_id}",
                    source=self.source_name,
                    description=truncate(str(task.get("description", "")), 800),
                    budget_raw=budget_raw,
                    budget_value=parse_budget(budget_raw),
                    category=str(task.get("categoryName") or ""),
                    published_raw=str(task.get("dateCreated") or ""),
                )
            )
        return projects

    @staticmethod
    def _dig_tasks(state: dict) -> list:
        """Пытается найти список задач в произвольной структуре стейта."""
        for key in ("tasks", "items", "list"):
            node = state.get(key)
            if isinstance(node, list) and node:
                return node
            if isinstance(node, dict):
                for sub in node.values():
                    if isinstance(sub, list) and sub:
                        return sub
        return []

    def _parse_html(self, html: str) -> list[Project]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("div.TasksList__item") or soup.select("[data-test='task-item']")
        projects: list[Project] = []
        for card in cards:
            project = self._parse_card(card)
            if project is not None:
                projects.append(project)
        return projects

    def _parse_card(self, card: Tag) -> Project | None:
        link = card.select_one("a")
        if not isinstance(link, Tag):
            return None
        title = link.get_text(strip=True)
        href = str(link.get("href", "")).strip()
        if not title or not href:
            return None
        url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        budget_el = card.select_one("[class*='price']")
        budget_raw = budget_el.get_text(" ", strip=True) if budget_el else ""
        desc_el = card.select_one("[class*='description']")

        return Project(
            title=title,
            url=url,
            source=self.source_name,
            description=truncate(desc_el.get_text(" ", strip=True) if desc_el else "", 800),
            budget_raw=budget_raw,
            budget_value=parse_budget(budget_raw),
        )


__all__ = ["YouDoParser"]
