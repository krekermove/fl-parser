"""Форматирование и отправка уведомлений о найденных заданиях."""
from __future__ import annotations

import asyncio
import html

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from loguru import logger

from parsers.dto import Project
from utils.text import truncate


class Notifier:
    """Отправляет пользователю красиво оформленные уведомления."""

    def __init__(self, bot: Bot) -> None:
        self._bot = bot

    @staticmethod
    def format_project(project: Project) -> str:
        """Формирует HTML-сообщение по заданию."""
        e = html.escape
        budget = project.budget_raw.strip() or "не указан"
        category = project.category.strip() or "—"
        description = truncate(project.description, 500) or "—"

        lines = [
            "📌 <b>Новое задание</b>",
            "",
            f"🏷 <b>Биржа:</b> {e(project.source)}",
            f"📝 <b>Название:</b> {e(project.title)}",
            f"💰 <b>Бюджет:</b> {e(budget)}",
            f"📂 <b>Категория:</b> {e(category)}",
        ]
        if project.published_raw:
            lines.append(f"🕒 <b>Опубликовано:</b> {e(project.published_raw)}")
        lines += [
            "",
            "<b>Описание:</b>",
            e(description),
            "",
            f'🔗 <a href="{e(project.url)}">Открыть проект</a>',
        ]
        return "\n".join(lines)

    async def send(self, user_id: int, project: Project) -> bool:
        """Отправляет уведомление. Возвращает True при успехе.

        Обрабатывает флуд-контроль Telegram (RetryAfter) и блокировку бота
        пользователем (Forbidden).
        """
        text = self.format_project(project)
        try:
            await self._bot.send_message(
                user_id,
                text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
            logger.info("Отправлено уведомление user={} project={}", user_id, project.url)
            return True
        except TelegramRetryAfter as err:
            logger.warning("Флуд-контроль, ждём {}с (user={})", err.retry_after, user_id)
            await asyncio.sleep(err.retry_after + 1)
            return await self.send(user_id, project)
        except TelegramForbiddenError:
            logger.warning("Пользователь {} заблокировал бота — пропуск", user_id)
            return False
        except Exception as err:  # noqa: BLE001 — ошибка Telegram API не должна ронять цикл
            logger.exception("Ошибка отправки user={}: {}", user_id, err)
            return False


__all__ = ["Notifier"]
