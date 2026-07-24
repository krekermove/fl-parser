"""ORM-модели SQLAlchemy 2.0."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Базовый декларативный класс."""


class User(Base):
    """Пользователь бота и его глобальные настройки мониторинга."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    monitoring_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    min_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    check_interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_utcnow
    )

    keywords: Mapped[list["Keyword"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    stopwords: Mapped[list["StopWord"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    sources: Mapped[list["Source"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )


class Keyword(Base):
    """Ключевое слово пользователя (искать)."""

    __tablename__ = "keywords"
    __table_args__ = (UniqueConstraint("user_id", "word", name="uq_keyword_user_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    word: Mapped[str] = mapped_column(String(128), nullable=False)

    user: Mapped[User] = relationship(back_populates="keywords")


class StopWord(Base):
    """Стоп-слово пользователя (игнорировать)."""

    __tablename__ = "stopwords"
    __table_args__ = (UniqueConstraint("user_id", "word", name="uq_stopword_user_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    word: Mapped[str] = mapped_column(String(128), nullable=False)

    user: Mapped[User] = relationship(back_populates="stopwords")


class Source(Base):
    """Подключённая биржа пользователя."""

    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_source_user_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False)  # kwork / youdo / flru
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="sources")


class SentProject(Base):
    """Уже отправленное пользователю задание (для дедупликации)."""

    __tablename__ = "sent_projects"
    __table_args__ = (
        UniqueConstraint("user_id", "project_hash", name="uq_sent_user_hash"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=_utcnow
    )


__all__ = ["Base", "User", "Keyword", "StopWord", "Source", "SentProject"]
