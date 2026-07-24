"""Обработчики команд Telegram-бота."""
from __future__ import annotations

import html

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message
from loguru import logger

from bot.keyboards import SOURCE_CALLBACK_PREFIX, sources_keyboard
from config.settings import Settings
from database.repository import Repository
from parsers import SOURCE_TITLES
from services.monitoring import MonitoringService

router = Router(name="commands")

HELP_TEXT = (
    "🤖 <b>Мониторинг фриланс-бирж</b>\n\n"
    "Я слежу за новыми заданиями на <b>Kwork</b>, <b>YouDo</b> и <b>FL.ru</b> "
    "и присылаю только то, что подходит под ваши фильтры.\n\n"
    "<b>Команды:</b>\n"
    "/start — запуск и регистрация\n"
    "/help — эта справка\n"
    "/settings — показать текущие настройки\n"
    "/keywords — ключевые слова (искать)\n"
    "/stopwords — стоп-слова (игнорировать)\n"
    "/budget — диапазон бюджета\n"
    "/sources — выбрать биржи\n"
    "/status — статус мониторинга\n"
    "/start_monitoring — включить уведомления\n"
    "/stop_monitoring — выключить уведомления\n\n"
    "<b>Работа со словами:</b>\n"
    "<code>/keywords</code> — показать список\n"
    "<code>/keywords add python, telegram, django</code>\n"
    "<code>/keywords del python</code>\n"
    "<code>/keywords clear</code>\n\n"
    "<b>Бюджет:</b>\n"
    "<code>/budget 5000 50000</code> — от 5000 до 50000\n"
    "<code>/budget 5000 -</code> — только минимум\n"
    "<code>/budget clear</code> — сбросить\n"
)


def _split_words(raw: str) -> list[str]:
    """Разбивает строку по запятым/переносам в список слов."""
    parts = raw.replace("\n", ",").split(",")
    return [p.strip() for p in parts if p.strip()]


# --------------------------------------------------------------------- /start
@router.message(Command("start"))
async def cmd_start(message: Message, repo: Repository, app_settings: Settings) -> None:
    assert message.from_user is not None
    await repo.get_or_create_user(
        message.from_user.id, default_sources=app_settings.available_sources
    )
    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Вы зарегистрированы. Настройте фильтры и включите мониторинг:\n"
        "1️⃣ /keywords — что искать\n"
        "2️⃣ /stopwords — что игнорировать\n"
        "3️⃣ /budget — бюджет\n"
        "4️⃣ /sources — биржи\n"
        "5️⃣ /start_monitoring — запуск\n\n"
        "Полная справка — /help",
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT)


# ------------------------------------------------------------------ /settings
@router.message(Command("settings"))
async def cmd_settings(message: Message, repo: Repository) -> None:
    assert message.from_user is not None
    us = await repo.get_settings(message.from_user.id)
    if us is None:
        await message.answer("Сначала выполните /start.")
        return

    kw = ", ".join(us.keywords) if us.keywords else "—"
    sw = ", ".join(us.stopwords) if us.stopwords else "—"
    sources = ", ".join(SOURCE_TITLES.get(s, s) for s in us.enabled_sources) or "—"
    budget_min = us.min_budget if us.min_budget is not None else "—"
    budget_max = us.max_budget if us.max_budget is not None else "—"

    await message.answer(
        "⚙️ <b>Текущие настройки</b>\n\n"
        f"🔎 <b>Ключевые слова:</b> {html.escape(kw)}\n"
        f"🚫 <b>Стоп-слова:</b> {html.escape(sw)}\n"
        f"💰 <b>Бюджет:</b> от {budget_min} до {budget_max}\n"
        f"🏷 <b>Биржи:</b> {html.escape(sources)}\n"
        f"📡 <b>Мониторинг:</b> {'включён ✅' if us.monitoring_active else 'выключен ❌'}",
    )


# ------------------------------------------------------------------ /keywords
@router.message(Command("keywords"))
async def cmd_keywords(message: Message, command: CommandObject, repo: Repository) -> None:
    await _handle_word_command(
        message,
        command,
        repo,
        list_fn=repo.list_keywords,
        add_fn=repo.add_keyword,
        del_fn=repo.remove_keyword,
        clear_fn=repo.clear_keywords,
        title="Ключевые слова",
        emoji="🔎",
    )


@router.message(Command("stopwords"))
async def cmd_stopwords(message: Message, command: CommandObject, repo: Repository) -> None:
    await _handle_word_command(
        message,
        command,
        repo,
        list_fn=repo.list_stopwords,
        add_fn=repo.add_stopword,
        del_fn=repo.remove_stopword,
        clear_fn=repo.clear_stopwords,
        title="Стоп-слова",
        emoji="🚫",
    )


async def _handle_word_command(
    message: Message,
    command: CommandObject,
    repo: Repository,
    *,
    list_fn,
    add_fn,
    del_fn,
    clear_fn,
    title: str,
    emoji: str,
) -> None:
    assert message.from_user is not None
    user_id = message.from_user.id
    args = (command.args or "").strip()

    if not args:
        words = await list_fn(user_id)
        current = ", ".join(words) if words else "список пуст"
        await message.answer(
            f"{emoji} <b>{title}</b>\n{html.escape(current)}\n\n"
            f"Добавить: <code>/{command.command} add слово1, слово2</code>\n"
            f"Удалить: <code>/{command.command} del слово</code>\n"
            f"Очистить: <code>/{command.command} clear</code>"
        )
        return

    action, _, payload = args.partition(" ")
    action = action.lower()

    if action == "clear":
        await clear_fn(user_id)
        await message.answer(f"{emoji} {title}: список очищен.")
        return

    if action in {"add", "del"}:
        words = _split_words(payload)
        if not words:
            await message.answer("Укажите хотя бы одно слово.")
            return
        changed = 0
        for w in words:
            ok = await (add_fn if action == "add" else del_fn)(user_id, w)
            changed += int(ok)
        verb = "Добавлено" if action == "add" else "Удалено"
        await message.answer(f"{emoji} {verb}: {changed} из {len(words)}.")
        return

    await message.answer(
        "Неизвестное действие. Используйте add / del / clear."
    )


# -------------------------------------------------------------------- /budget
@router.message(Command("budget"))
async def cmd_budget(message: Message, command: CommandObject, repo: Repository) -> None:
    assert message.from_user is not None
    user_id = message.from_user.id
    args = (command.args or "").strip()

    if not args:
        us = await repo.get_settings(user_id)
        mn = us.min_budget if us and us.min_budget is not None else "—"
        mx = us.max_budget if us and us.max_budget is not None else "—"
        await message.answer(
            f"💰 <b>Бюджет:</b> от {mn} до {mx}\n\n"
            "Установить: <code>/budget 5000 50000</code>\n"
            "Только минимум: <code>/budget 5000 -</code>\n"
            "Сбросить: <code>/budget clear</code>"
        )
        return

    if args.lower() == "clear":
        await repo.set_budget(user_id, None, None)
        await message.answer("💰 Бюджетные ограничения сброшены.")
        return

    parts = args.split()
    min_budget = _parse_budget_arg(parts[0]) if len(parts) >= 1 else None
    max_budget = _parse_budget_arg(parts[1]) if len(parts) >= 2 else None

    if len(parts) == 1 and min_budget is None:
        await message.answer("Не удалось разобрать число. Пример: <code>/budget 5000 50000</code>")
        return

    await repo.set_budget(user_id, min_budget, max_budget)
    await message.answer(
        f"💰 Бюджет сохранён: от {min_budget if min_budget is not None else '—'} "
        f"до {max_budget if max_budget is not None else '—'}."
    )


def _parse_budget_arg(token: str) -> int | None:
    token = token.strip()
    if token in {"-", "—", "*", ""}:
        return None
    digits = "".join(ch for ch in token if ch.isdigit())
    return int(digits) if digits else None


# ------------------------------------------------------------------- /sources
@router.message(Command("sources"))
async def cmd_sources(message: Message, repo: Repository, app_settings: Settings) -> None:
    assert message.from_user is not None
    await repo.get_or_create_user(
        message.from_user.id, default_sources=app_settings.available_sources
    )
    enabled = await repo.get_sources(message.from_user.id)
    await message.answer(
        "🏷 <b>Биржи</b>\nНажмите, чтобы включить/выключить:",
        reply_markup=sources_keyboard(enabled),
    )


@router.callback_query(F.data.startswith(SOURCE_CALLBACK_PREFIX))
async def on_source_toggle(callback: CallbackQuery, repo: Repository) -> None:
    assert callback.from_user is not None
    assert callback.data is not None
    source_id = callback.data[len(SOURCE_CALLBACK_PREFIX):]
    if source_id not in SOURCE_TITLES:
        await callback.answer("Неизвестная биржа.")
        return

    new_state = await repo.toggle_source(callback.from_user.id, source_id)
    enabled = await repo.get_sources(callback.from_user.id)
    if isinstance(callback.message, Message):
        await callback.message.edit_reply_markup(reply_markup=sources_keyboard(enabled))
    await callback.answer(
        f"{SOURCE_TITLES[source_id]}: {'включена' if new_state else 'выключена'}"
    )


# -------------------------------------------------------------------- /status
@router.message(Command("status"))
async def cmd_status(message: Message, repo: Repository) -> None:
    assert message.from_user is not None
    us = await repo.get_settings(message.from_user.id)
    if us is None:
        await message.answer("Сначала выполните /start.")
        return

    last_check = (
        us.last_check_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        if us.last_check_at
        else "ещё не было"
    )
    await message.answer(
        "📡 <b>Статус мониторинга</b>\n\n"
        f"Состояние: {'🟢 включён' if us.monitoring_active else '🔴 выключен'}\n"
        f"Последняя проверка: {last_check}\n"
        f"Ключевых слов: {len(us.keywords)}\n"
        f"Стоп-слов: {len(us.stopwords)}\n"
        f"Активных бирж: {len(us.enabled_sources)}"
    )


# ---------------------------------------------------- /start_monitoring, /stop
@router.message(Command("start_monitoring"))
async def cmd_start_monitoring(
    message: Message, repo: Repository, monitoring: MonitoringService
) -> None:
    assert message.from_user is not None
    user_id = message.from_user.id
    us = await repo.get_settings(user_id)
    if us and not us.enabled_sources:
        await message.answer("⚠️ Не выбрано ни одной биржи. Откройте /sources.")
        return

    await repo.set_monitoring(user_id, True)
    await message.answer(
        "🟢 Мониторинг включён. Проверяю биржи в фоне и пришлю подходящие задания.\n"
        "Запускаю первую проверку…"
    )
    logger.info("Пользователь {} включил мониторинг", user_id)
    # Немедленная первая проверка, чтобы пользователь не ждал следующего тика.
    await monitoring.run_cycle()


@router.message(Command("stop_monitoring"))
async def cmd_stop_monitoring(message: Message, repo: Repository) -> None:
    assert message.from_user is not None
    await repo.set_monitoring(message.from_user.id, False)
    await message.answer("🔴 Мониторинг выключен.")
    logger.info("Пользователь {} выключил мониторинг", message.from_user.id)


__all__ = ["router"]
