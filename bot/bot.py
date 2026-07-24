"""Сборка Dispatcher и вспомогательные функции бота."""
from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from bot.handlers import get_root_router
from config.settings import Settings
from database.repository import Repository
from services.monitoring import MonitoringService

_BOT_COMMANDS: list[BotCommand] = [
    BotCommand(command="start", description="Запуск и регистрация"),
    BotCommand(command="help", description="Справка по командам"),
    BotCommand(command="settings", description="Показать настройки"),
    BotCommand(command="keywords", description="Ключевые слова"),
    BotCommand(command="stopwords", description="Стоп-слова"),
    BotCommand(command="budget", description="Диапазон бюджета"),
    BotCommand(command="sources", description="Выбор бирж"),
    BotCommand(command="status", description="Статус мониторинга"),
    BotCommand(command="start_monitoring", description="Включить уведомления"),
    BotCommand(command="stop_monitoring", description="Выключить уведомления"),
]


def create_dispatcher(
    repository: Repository,
    monitoring: MonitoringService,
    app_settings: Settings,
) -> Dispatcher:
    """Создаёт Dispatcher и прокидывает зависимости в обработчики.

    Зависимости передаются через workflow data — aiogram сам подставит их
    в обработчики по имени параметра (repo, monitoring, app_settings).
    """
    dp = Dispatcher()
    dp["repo"] = repository
    dp["monitoring"] = monitoring
    dp["app_settings"] = app_settings
    dp.include_router(get_root_router())
    return dp


async def setup_bot_commands(bot: Bot) -> None:
    """Регистрирует меню команд в интерфейсе Telegram."""
    await bot.set_my_commands(_BOT_COMMANDS)


__all__ = ["create_dispatcher", "setup_bot_commands"]
