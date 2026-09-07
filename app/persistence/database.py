"""Authoritative PostgreSQL and async database session management (DATA-001, ADR-012)."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings


class Base(DeclarativeBase):
    """Declarative base for all authoritative persistence entities."""

    pass


def get_engine(database_url: str | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine based on configuration or explicit URL."""
    if database_url is None:
        database_url = get_settings().database_url

    # Normalize sqlite URLs for async if needed
    if database_url.startswith("sqlite:///"):
        database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    elif database_url == "sqlite:///:memory:":
        database_url = "sqlite+aiosqlite:///:memory:"

    is_sqlite = database_url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}

    return create_async_engine(
        database_url,
        echo=False,
        connect_args=connect_args,
        future=True,
    )


def get_session_maker(engine: AsyncEngine | None = None) -> async_sessionmaker[AsyncSession]:
    """Create a session factory bound to an async engine."""
    if engine is None:
        engine = get_engine()
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@asynccontextmanager
async def get_db_session(
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session context with automatic rollback on error."""
    if session_maker is None:
        session_maker = get_session_maker()

    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
