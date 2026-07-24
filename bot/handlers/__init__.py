from aiogram import Router

from bot.handlers.commands import router as commands_router


def get_root_router() -> Router:
    """Собирает корневой роутер со всеми обработчиками."""
    root = Router(name="root")
    root.include_router(commands_router)
    return root


__all__ = ["get_root_router"]
