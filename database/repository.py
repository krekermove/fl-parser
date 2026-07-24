"""Слой доступа к данным. Инкапсулирует все запросы к БД."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.models import Keyword, SentProject, Source, StopWord, User


@dataclass(slots=True)
class UserSettings:
    """Снимок настроек пользователя, безопасный для передачи между слоями."""

    user_id: int
    monitoring_active: bool = False
    min_budget: int | None = None
    max_budget: int | None = None
    check_interval_minutes: int | None = None
    last_check_at: datetime | None = None
    keywords: list[str] = field(default_factory=list)
    stopwords: list[str] = field(default_factory=list)
    enabled_sources: list[str] = field(default_factory=list)


class Repository:
    """Асинхронный репозиторий поверх фабрики сессий SQLAlchemy."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory

    # ------------------------------------------------------------------ users
    async def get_or_create_user(
        self, user_id: int, default_sources: tuple[str, ...] = ()
    ) -> None:
        async with self._sf() as session, session.begin():
            user = await session.get(User, user_id)
            if user is None:
                user = User(id=user_id, monitoring_active=False)
                session.add(user)
                await session.flush()
                for name in default_sources:
                    session.add(Source(user_id=user_id, name=name, enabled=True))

    async def get_settings(self, user_id: int) -> UserSettings | None:
        async with self._sf() as session:
            user = await session.get(User, user_id)
            if user is None:
                return None
            return UserSettings(
                user_id=user.id,
                monitoring_active=user.monitoring_active,
                min_budget=user.min_budget,
                max_budget=user.max_budget,
                check_interval_minutes=user.check_interval_minutes,
                last_check_at=user.last_check_at,
                keywords=[k.word for k in user.keywords],
                stopwords=[s.word for s in user.stopwords],
                enabled_sources=[s.name for s in user.sources if s.enabled],
            )

    async def get_active_users(self) -> list[int]:
        async with self._sf() as session:
            result = await session.execute(
                select(User.id).where(User.monitoring_active.is_(True))
            )
            return [row[0] for row in result.all()]

    async def set_monitoring(self, user_id: int, active: bool) -> None:
        async with self._sf() as session, session.begin():
            await session.execute(
                update(User).where(User.id == user_id).values(monitoring_active=active)
            )

    async def update_last_check(self, user_id: int) -> None:
        async with self._sf() as session, session.begin():
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(last_check_at=datetime.now(timezone.utc))
            )

    async def set_budget(
        self, user_id: int, min_budget: int | None, max_budget: int | None
    ) -> None:
        async with self._sf() as session, session.begin():
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(min_budget=min_budget, max_budget=max_budget)
            )

    # --------------------------------------------------------------- keywords
    async def add_keyword(self, user_id: int, word: str) -> bool:
        return await self._add_word(Keyword, user_id, word)

    async def remove_keyword(self, user_id: int, word: str) -> bool:
        return await self._remove_word(Keyword, user_id, word)

    async def clear_keywords(self, user_id: int) -> None:
        await self._clear_words(Keyword, user_id)

    async def list_keywords(self, user_id: int) -> list[str]:
        return await self._list_words(Keyword, user_id)

    # -------------------------------------------------------------- stopwords
    async def add_stopword(self, user_id: int, word: str) -> bool:
        return await self._add_word(StopWord, user_id, word)

    async def remove_stopword(self, user_id: int, word: str) -> bool:
        return await self._remove_word(StopWord, user_id, word)

    async def clear_stopwords(self, user_id: int) -> None:
        await self._clear_words(StopWord, user_id)

    async def list_stopwords(self, user_id: int) -> list[str]:
        return await self._list_words(StopWord, user_id)

    # ----------------------------------------------------------------- shared
    async def _add_word(self, model: type, user_id: int, word: str) -> bool:
        word = word.strip().lower()
        if not word:
            return False
        async with self._sf() as session, session.begin():
            exists = await session.execute(
                select(model.id).where(model.user_id == user_id, model.word == word)
            )
            if exists.first() is not None:
                return False
            session.add(model(user_id=user_id, word=word))
            return True

    async def _remove_word(self, model: type, user_id: int, word: str) -> bool:
        word = word.strip().lower()
        async with self._sf() as session, session.begin():
            result = await session.execute(
                delete(model).where(model.user_id == user_id, model.word == word)
            )
            return result.rowcount > 0

    async def _clear_words(self, model: type, user_id: int) -> None:
        async with self._sf() as session, session.begin():
            await session.execute(delete(model).where(model.user_id == user_id))

    async def _list_words(self, model: type, user_id: int) -> list[str]:
        async with self._sf() as session:
            result = await session.execute(
                select(model.word).where(model.user_id == user_id).order_by(model.word)
            )
            return [row[0] for row in result.all()]

    # ----------------------------------------------------------------- sources
    async def get_sources(self, user_id: int) -> dict[str, bool]:
        async with self._sf() as session:
            result = await session.execute(
                select(Source.name, Source.enabled).where(Source.user_id == user_id)
            )
            return {name: enabled for name, enabled in result.all()}

    async def toggle_source(self, user_id: int, name: str) -> bool:
        """Переключает биржу и возвращает её новое состояние (enabled)."""
        async with self._sf() as session, session.begin():
            source = await session.execute(
                select(Source).where(Source.user_id == user_id, Source.name == name)
            )
            obj = source.scalar_one_or_none()
            if obj is None:
                obj = Source(user_id=user_id, name=name, enabled=True)
                session.add(obj)
                return True
            obj.enabled = not obj.enabled
            return obj.enabled

    # ------------------------------------------------------------ deduplication
    async def is_sent(self, user_id: int, project_hash: str) -> bool:
        async with self._sf() as session:
            result = await session.execute(
                select(SentProject.id).where(
                    SentProject.user_id == user_id,
                    SentProject.project_hash == project_hash,
                )
            )
            return result.first() is not None

    async def mark_sent(
        self, user_id: int, project_hash: str, source: str, url: str
    ) -> None:
        async with self._sf() as session, session.begin():
            session.add(
                SentProject(
                    user_id=user_id,
                    project_hash=project_hash,
                    source=source,
                    url=url,
                )
            )


__all__ = ["Repository", "UserSettings"]
