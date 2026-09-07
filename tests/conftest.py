from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import app.persistence.models  # noqa: F401
from app.config.settings import (
    Environment,
    Profile,
    Settings,
    clear_settings_cache,
    get_settings,
)
from app.main import create_app
from app.persistence.database import Base


@pytest.fixture(autouse=True)
def clean_env() -> Generator[None, None, None]:
    """Ensure environment is isolated between tests."""
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def test_settings() -> Settings:
    """Default test profile settings."""
    return Settings(
        profile=Profile.TEST,
        env=Environment.TEST,
        database_url="sqlite+aiosqlite:///:memory:",
        asr_provider="fake",
        tts_provider="cached",
        semantic_enabled=False,
        llm_paraphrase_enabled=False,
        vision_enabled=False,
    )


@pytest.fixture
def test_client(test_settings: Settings) -> Generator[TestClient, None, None]:
    """Synchronous test client with test profile settings."""
    clear_settings_cache()
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Provide an in-memory SQLite async engine with all tables created."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an isolated async database session with automatic cleanup."""
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()
