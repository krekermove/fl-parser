"""Точка входа: поднимает бота, планировщик и цикл мониторинга."""
from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from bot.bot import create_dispatcher, setup_bot_commands
from config.settings import Settings
from database.engine import init_database
from database.repository import Repository
from services.monitoring import MonitoringService
from utils.logger import setup_logging


async def main() -> None:
    # 1. Конфигурация.
    settings = Settings.from_env()

    # 2. Логирование.
    setup_logging(settings.log_level, settings.log_file)
    logger.info("Запуск приложения. Интервал проверки: {} мин", settings.check_interval_minutes)

    # 3. База данных.
    database = init_database(settings.database_url)
    await database.create_all()
    repository = Repository(database.session_factory)

    # 4. Бот и зависимости.
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    monitoring = MonitoringService(bot, repository, settings)
    dp = create_dispatcher(repository, monitoring, settings)

    # 5. Планировщик периодической проверки.
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        monitoring.run_cycle,
        trigger="interval",
        minutes=settings.check_interval_minutes,
        id="monitoring_cycle",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )

    # 6. Запуск.
    await setup_bot_commands(bot)
    scheduler.start()
    logger.info("Планировщик запущен. Бот начинает поллинг.")

    try:
        # Пропускаем накопившиеся апдейты, чтобы не отвечать на старые команды.
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        logger.info("Остановка приложения…")
        scheduler.shutdown(wait=False)
        await bot.session.close()
        await database.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Завершение по сигналу пользователя.")
