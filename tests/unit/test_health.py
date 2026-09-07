"""Unit tests for health endpoints and semantic distinctions (API-007)."""

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Environment, Profile, Settings, get_settings


def test_health_live(test_client: TestClient):
    """GET /health/live returns 200 and LIVE status."""
    response = test_client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "LIVE"
    assert data["profile"] == "test"
    assert "version" in data


def test_health_ready_success(test_client: TestClient):
    """GET /health/ready returns 200 and READY status under test profile."""
    response = test_client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert data["database"] == "READY"
    assert data["reason"] is None


@pytest.mark.asyncio
async def test_health_ready_db_failure(monkeypatch):
    """GET /health/ready returns 503 and NOT_READY when core database is unreachable."""
    from app.main import create_app

    # Force database readiness check to fail
    async def mock_db_check(settings):
        return False, "Database connection refused"

    monkeypatch.setattr("app.api.health.check_database_readiness", mock_db_check)

    app = create_app()
    with TestClient(app) as client:
        response = client.get("/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "NOT_READY"
        assert data["database"] == "NOT_READY"
        assert "Database connection refused" in data["reason"]


def test_health_demo_healthy_under_test(test_client: TestClient):
    """GET /health/demo returns HEALTHY when using fake/cached adapters."""
    response = test_client.get("/health/demo")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["core_ready"] is True
    assert data["providers"]["asr"] == "fake"
    assert data["providers"]["tts"] == "cached"
    assert len(data["degraded_reasons"]) == 0


def test_health_demo_degraded_when_optional_provider_missing_key(monkeypatch):
    """GET /health/demo returns DEGRADED when optional provider is enabled without credentials,

    while core readiness and process liveness remain intact.
    """
    from app.main import create_app

    # Cloud profile with managed ASR without key during runtime (e.g. key expired)
    degraded_settings = Settings(
        profile=Profile.CLOUD,
        env=Environment.DEVELOPMENT,
        asr_provider="managed",
        cloud_asr_api_key=None,
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: degraded_settings
    with TestClient(app) as client:
        # Liveness remains LIVE
        live_res = client.get("/health/live")
        assert live_res.status_code == 200
        assert live_res.json()["status"] == "LIVE"

        # Demo health reports DEGRADED
        demo_res = client.get("/health/demo")
        assert demo_res.status_code == 200
        data = demo_res.json()
        assert data["status"] == "DEGRADED"
        assert data["core_ready"] is True
        assert data["providers"]["asr"] == "degraded"
        assert len(data["degraded_reasons"]) > 0
