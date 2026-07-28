"""Парсер биржи FL.ru (https://www.fl.ru).

FL.ru отдаёт листинг проектов в HTML, поэтому используется requests-подход
(aiohttp) + BeautifulSoup. Разметка биржи периодически меняется, поэтому
парсинг сделан максимально устойчивым: каждое поле извлекается независимо,
отсутствие поля не роняет весь парсер.
"""
from __future__ import annotations

from bs4 import BeautifulSoup, Tag
from loguru import logger

from .base import BaseParser
from .dto import Project
from utils.text import parse_budget, truncate

_BASE_URL = "https://www.fl.ru"

# Костыль: парсим только нужные категории FL.ru (по одному листингу на категорию).
_CATEGORY_URLS: tuple[str, ...] = (
    "https://www.fl.ru/projects/category/saity/",
    "https://www.fl.ru/projects/category/programmirovanie/",
    "https://www.fl.ru/projects/category/ai-iskusstvenniy-intellekt/",
    "https://www.fl.ru/projects/category/mobile/",
)


class FlRuParser(BaseParser):
    source_id = "flru"
    source_name = "FL.ru"

    async def parse(self) -> list[Project]:
        projects: list[Project] = []
        seen: set[str] = set()  # дедуп внутри цикла (категории могут пересекаться)

        for url in _CATEGORY_URLS:
            html = await self._http.get_text(url)
            if not html:
                logger.warning("[{}] Пустой ответ от {}", self.source_name, url)
                continue

            for project in self._parse_listing(html):
                if project.url in seen:
                    continue
                seen.add(project.url)
                projects.append(project)

        return projects

    def _parse_listing(self, html: str) -> list[Project]:
        soup = BeautifulSoup(html, "lxml")
        projects: list[Project] = []

        # Проектные карточки. Пробуем несколько селекторов — верстка меняется.
        cards = (
            soup.select("div.b-post")
            or soup.select("div[id^='project-item']")
            or soup.select("div.project-item")
        )

        for card in cards:
            project = self._parse_card(card)
            if project is not None:
                projects.append(project)

        return projects

    def _parse_card(self, card: Tag) -> Project | None:
        # Заголовок и ссылка.
        link = card.select_one("h2 a") or card.select_one("a.b-post__link") or card.find("a")
        if not isinstance(link, Tag):
            return None

        title = link.get_text(strip=True)
        href = str(link.get("href", "")).strip()
        if not title or not href:
            return None
        url = href if href.startswith("http") else f"{_BASE_URL}{href}"

        # Описание.
        desc_el = (
            card.select_one("div.b-post__body")
            or card.select_one("div.b-post__txt")
            or card.select_one("div.project-description")
        )
        description = truncate(desc_el.get_text(" ", strip=True) if desc_el else "", 800)

        # Бюджет.
        budget_el = card.select_one("div.b-post__price") or card.select_one(".project-price")
        budget_raw = budget_el.get_text(" ", strip=True) if budget_el else ""

        # Категория.
        cat_el = card.select_one("a.b-post__link_grey") or card.select_one(".project-category")
        category = cat_el.get_text(strip=True) if cat_el else ""

        # Дата публикации (обычно относительная строка).
        date_el = card.select_one("span.b-post__foot-i") or card.select_one(".project-date")
        published_raw = date_el.get_text(strip=True) if date_el else ""

        return Project(
            title=title,
            url=url,
            source=self.source_name,
            description=description,
            budget_raw=budget_raw,
            budget_value=parse_budget(budget_raw),
            category=category,
            published_raw=published_raw,
        )


__all__ = ["FlRuParser"]
