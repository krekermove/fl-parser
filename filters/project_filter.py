"""Гибкая система фильтрации заданий.

Модуль намеренно не содержит побочных эффектов (ни сети, ни БД): это чистая
доменная логика, которую легко покрыть юнит-тестами.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from parsers.dto import Project


@dataclass(slots=True)
class FilterCriteria:
    """Критерии фильтрации, заданные пользователем.

    Пустые коллекции означают «не ограничивать по этому признаку».
    """

    keywords: list[str] = field(default_factory=list)
    stopwords: list[str] = field(default_factory=list)
    min_budget: int | None = None
    max_budget: int | None = None
    categories: list[str] = field(default_factory=list)
    excluded_categories: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)  # красивые имена бирж

    def normalized(self) -> "FilterCriteria":
        """Возвращает копию с приведёнными к нижнему регистру строками."""
        lower = lambda items: [s.strip().lower() for s in items if s.strip()]
        return FilterCriteria(
            keywords=lower(self.keywords),
            stopwords=lower(self.stopwords),
            min_budget=self.min_budget,
            max_budget=self.max_budget,
            categories=lower(self.categories),
            excluded_categories=lower(self.excluded_categories),
            sources=lower(self.sources),
        )


@dataclass(slots=True)
class MatchResult:
    """Результат проверки задания с причиной отклонения (для логов)."""

    passed: bool
    reason: str = ""


class ProjectFilter:
    """Применяет критерии к заданию.

    Порядок проверок выстроен от самых дешёвых/частых отсечений к более
    затратным, но на практике все проверки — O(n) по числу слов.
    """

    def __init__(self, criteria: FilterCriteria) -> None:
        self._c = criteria.normalized()

    def check(self, project: Project) -> MatchResult:
        haystack = self._haystack(project)

        # 1. Источник (биржа).
        if self._c.sources and project.source.strip().lower() not in self._c.sources:
            return MatchResult(False, f"источник '{project.source}' не выбран")

        # 2. Стоп-слова — мгновенное отклонение.
        for stop in self._c.stopwords:
            if stop in haystack:
                return MatchResult(False, f"стоп-слово '{stop}'")

        # 3. Исключаемые категории.
        category = project.category.strip().lower()
        if category and any(exc in category for exc in self._c.excluded_categories):
            return MatchResult(False, f"исключённая категория '{project.category}'")

        # 4. Разрешённые категории (если заданы).
        if self._c.categories and not any(cat in category for cat in self._c.categories):
            return MatchResult(False, f"категория '{project.category}' вне списка")

        # 5. Ключевые слова — должно совпасть хотя бы одно (если заданы).
        if self._c.keywords and not any(kw in haystack for kw in self._c.keywords):
            return MatchResult(False, "нет совпадений по ключевым словам")

        # 6. Бюджет.
        budget_ok, budget_reason = self._check_budget(project)
        if not budget_ok:
            return MatchResult(False, budget_reason)

        return MatchResult(True)

    def matches(self, project: Project) -> bool:
        return self.check(project).passed

    def _check_budget(self, project: Project) -> tuple[bool, str]:
        value = project.budget_value
        # Если бюджет не распознан, а ограничения заданы — пропускаем задание,
        # чтобы не потерять «договорные» проекты. Пользователь увидит и решит сам.
        if value is None:
            return True, ""
        if self._c.min_budget is not None and value < self._c.min_budget:
            return False, f"бюджет {value} < min {self._c.min_budget}"
        if self._c.max_budget is not None and value > self._c.max_budget:
            return False, f"бюджет {value} > max {self._c.max_budget}"
        return True, ""

    @staticmethod
    def _haystack(project: Project) -> str:
        """Единая строка для поиска слов (заголовок + описание + категория)."""
        return " ".join(
            (project.title, project.description, project.category)
        ).lower()


__all__ = ["FilterCriteria", "ProjectFilter", "MatchResult"]
