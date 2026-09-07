"""Pytest global fixtures for unit and integration testing."""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.config.settings import (
    Environment,
    Profile,
    Settings,
    clear_settings_cache,
    get_settings,
)
from app.main import create_app


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
