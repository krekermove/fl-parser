"""Инлайн-клавиатуры бота."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from parsers import SOURCE_TITLES

SOURCE_CALLBACK_PREFIX = "src_toggle:"


def sources_keyboard(enabled: dict[str, bool]) -> InlineKeyboardMarkup:
    """Клавиатура переключения бирж.

    ``enabled`` — словарь source_id -> bool. Отсутствующие ключи считаются
    выключенными.
    """
    rows: list[list[InlineKeyboardButton]] = []
    for source_id, title in SOURCE_TITLES.items():
        is_on = enabled.get(source_id, False)
        mark = "✅" if is_on else "❌"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {title}",
                    callback_data=f"{SOURCE_CALLBACK_PREFIX}{source_id}",
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


__all__ = ["sources_keyboard", "SOURCE_CALLBACK_PREFIX"]
