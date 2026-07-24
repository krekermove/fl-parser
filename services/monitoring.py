"""Оркестратор цикла мониторинга.

Один цикл:
  1. Получить активных пользователей.
  2. Собрать объединённый список нужных бирж и распарсить каждую ОДИН раз
     (кэш на цикл — экономим запросы к сайтам).
  3. Для каждого пользователя применить его фильтры, отсеять уже отправленные
     задания и разослать новые.
"""
from __future__ import annotations

import asyncio

from aiogram import Bot
from loguru import logger

from config.settings import Settings
from database.repository import Repository, UserSettings
from filters.project_filter import FilterCriteria, ProjectFilter
from parsers import build_parsers
from parsers.dto import Project
from services.notifier import Notifier
from utils.http import HttpClient

# Пауза между сообщениями одному пользователю (защита от флуд-контроля TG).
_SEND_INTERVAL = 0.4
# Максимум уведомлений одному пользователю за один цикл (защита от спама).
_MAX_PER_USER_PER_CYCLE = 15


class MonitoringService:
    def __init__(self, bot: Bot, repository: Repository, settings: Settings) -> None:
        self._repo = repository
        self._settings = settings
        self._notifier = Notifier(bot)
        self._running_lock = asyncio.Lock()

    async def run_cycle(self) -> None:
        """Выполняет один полный цикл проверки. Не бросает исключений наружу."""
        # Не даём двум циклам пересечься, если предыдущий затянулся.
        if self._running_lock.locked():
            logger.warning("Предыдущий цикл ещё выполняется — пропуск.")
            return

        async with self._running_lock:
            try:
                await self._run_cycle_inner()
            except Exception as err:  # noqa: BLE001
                logger.exception("Сбой цикла мониторинга: {}", err)

    async def _run_cycle_inner(self) -> None:
        user_ids = await self._repo.get_active_users()
        if not user_ids:
            logger.debug("Активных пользователей нет — цикл пропущен.")
            return

        logger.info("Старт цикла мониторинга. Активных пользователей: {}", len(user_ids))

        settings_map: dict[int, UserSettings] = {}
        needed_sources: set[str] = set()
        for uid in user_ids:
            us = await self._repo.get_settings(uid)
            if us is None:
                continue
            settings_map[uid] = us
            needed_sources.update(us.enabled_sources)

        if not needed_sources:
            logger.info("Ни у кого не выбрано ни одной биржи — нечего парсить.")
            return

        projects_by_source = await self._fetch_sources(sorted(needed_sources))

        total_sent = 0
        for uid, us in settings_map.items():
            sent = await self._process_user(uid, us, projects_by_source)
            total_sent += sent
            await self._repo.update_last_check(uid)

        logger.info("Цикл завершён. Всего отправлено уведомлений: {}", total_sent)

    async def _fetch_sources(self, source_ids: list[str]) -> dict[str, list[Project]]:
        """Парсит все нужные биржи параллельно, по одному разу за цикл."""
        result: dict[str, list[Project]] = {}
        async with HttpClient(
            timeout=self._settings.request_timeout,
            retries=self._settings.request_retries,
            delay_min=self._settings.request_delay_min,
            delay_max=self._settings.request_delay_max,
            proxy=self._settings.http_proxy,
        ) as http:
            parsers = build_parsers(source_ids, http)
            tasks = [p.safe_parse() for p in parsers]
            results = await asyncio.gather(*tasks)
            for parser, projects in zip(parsers, results):
                result[parser.source_id] = projects
        return result

    async def _process_user(
        self,
        user_id: int,
        us: UserSettings,
        projects_by_source: dict[str, list[Project]],
    ) -> int:
        criteria = FilterCriteria(
            keywords=us.keywords,
            stopwords=us.stopwords,
            min_budget=us.min_budget,
            max_budget=us.max_budget,
        )
        project_filter = ProjectFilter(criteria)

        sent_count = 0
        for source_id in us.enabled_sources:
            for project in projects_by_source.get(source_id, []):
                if sent_count >= _MAX_PER_USER_PER_CYCLE:
                    logger.info("user={} достигнут лимит уведомлений за цикл", user_id)
                    return sent_count

                result = project_filter.check(project)
                if not result.passed:
                    continue

                if await self._repo.is_sent(user_id, project.uid):
                    continue

                # Помечаем отправленным ДО send, чтобы при сбое не задублировать.
                await self._repo.mark_sent(
                    user_id, project.uid, project.source, project.url
                )
                ok = await self._notifier.send(user_id, project)
                if ok:
                    sent_count += 1
                    await asyncio.sleep(_SEND_INTERVAL)

        return sent_count


__all__ = ["MonitoringService"]
