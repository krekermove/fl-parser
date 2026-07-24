"""Инициализация async-движка SQLAlchemy и фабрики сессий."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from loguru import logger

from database.models import Base


class Database:
    """Держатель движка и фабрики сессий."""

    def __init__(self, url: str, echo: bool = False) -> None:
        self._engine: AsyncEngine = create_async_engine(url, echo=echo, future=True)
        self._session_factory = async_sessionmaker(
            self._engine, expire_on_commit=False, class_=AsyncSession
        )
        self._url = url

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    async def create_all(self) -> None:
        """Создаёт таблицы, если их ещё нет.

        Для продакшена рекомендуется Alembic (см. README), но для быстрого
        старта достаточно create_all.
        """
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Схема БД готова ({})", self._url)

    async def dispose(self) -> None:
        await self._engine.dispose()


_db: Database | None = None


def init_database(url: str, echo: bool = False) -> Database:
    """Создаёт глобальный экземпляр Database."""
    global _db
    _db = Database(url, echo=echo)
    return _db


def get_database() -> Database:
    if _db is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_database().")
    return _db


__all__ = ["Database", "init_database", "get_database"]
