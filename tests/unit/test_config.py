"""Unit tests for configuration profiles and validation rules."""

import pytest

from app.config.settings import (
    ConfigurationError,
    Environment,
    Profile,
    Settings,
)


def test_profile_test_defaults():
    """Test profile initializes with deterministic test defaults."""
    settings = Settings(profile=Profile.TEST, env=Environment.TEST)
    assert settings.profile == Profile.TEST
    assert settings.env == Environment.TEST
    assert settings.asr_provider == "fake"
    assert settings.tts_provider == "cached"
    assert not settings.semantic_enabled
    assert not settings.llm_paraphrase_enabled
    assert not settings.vision_enabled


def test_profile_local_defaults():
    """Local profile initializes for workstation development."""
    settings = Settings(profile=Profile.LOCAL, env=Environment.DEVELOPMENT)
    assert settings.profile == Profile.LOCAL
    assert settings.app_port == 8000
    assert not settings.require_tls


def test_profile_cloud_tls_requirement():
    """Production cloud profile requires TLS enforcement (API-003)."""
    # Without TLS in production cloud -> must raise ConfigurationError
    with pytest.raises(
        (ConfigurationError, ValueError), match="Production cloud profile requires require_tls=True"
    ):
        Settings(
            profile=Profile.CLOUD,
            env=Environment.PRODUCTION,
            require_tls=False,
        )

    # With TLS in production cloud -> validates cleanly
    valid_cloud = Settings(
        profile=Profile.CLOUD,
        env=Environment.PRODUCTION,
        require_tls=True,
    )
    assert valid_cloud.require_tls is True


def test_profile_cloud_managed_asr_optional_degrades_without_key():
    """Cloud profile allows booting even if optional provider key is absent."""
    settings = Settings(
        profile=Profile.CLOUD,
        asr_provider="managed",
        cloud_asr_api_key=None,
    )
    assert settings.asr_provider == "managed"
    assert settings.cloud_asr_api_key is None


def test_profile_demo_offline_boots_without_credentials():
    """Offline profile must boot cleanly with zero cloud credentials (ADR-014)."""
    settings = Settings(
        profile=Profile.DEMO_OFFLINE,
        env=Environment.DEVELOPMENT,
        cloud_asr_api_key=None,
        cloud_llm_api_key=None,
        cloud_tts_api_key=None,
    )
    assert settings.profile == Profile.DEMO_OFFLINE
    assert settings.cloud_asr_api_key is None
    assert settings.cloud_llm_api_key is None
    assert settings.cloud_tts_api_key is None
    assert settings.asr_provider in ("fake", "local", "cached")
    assert settings.tts_provider in ("cached", "local", "fake")


def test_profile_demo_offline_rejects_external_ai():
    """Offline demo rejects external AI enablement at boot."""
    with pytest.raises((ConfigurationError, ValueError), match="external semantic resolver"):
        Settings(
            profile=Profile.DEMO_OFFLINE,
            semantic_enabled=True,
        )

    with pytest.raises((ConfigurationError, ValueError), match="external LLM paraphraser"):
        Settings(
            profile=Profile.DEMO_OFFLINE,
            llm_paraphrase_enabled=True,
        )

    with pytest.raises((ConfigurationError, ValueError), match="cloud vision"):
        Settings(
            profile=Profile.DEMO_OFFLINE,
            vision_enabled=True,
        )


def test_profile_explicit_differences():
    """Verify all four profiles have explicit, distinguishable behaviors."""
    s_test = Settings(profile=Profile.TEST, env=Environment.TEST)
    s_local = Settings(profile=Profile.LOCAL, env=Environment.DEVELOPMENT)
    s_cloud = Settings(profile=Profile.CLOUD, env=Environment.DEVELOPMENT, require_tls=True)
    s_offline = Settings(profile=Profile.DEMO_OFFLINE, env=Environment.DEVELOPMENT)

    # 1. Profiles differ in identity
    assert len({s_test.profile, s_local.profile, s_cloud.profile, s_offline.profile}) == 4

    # 2. TLS requirements differ
    assert s_cloud.require_tls is True
    assert s_local.require_tls is False
    assert s_offline.require_tls is False

    # 3. Environment tier defaults differ
    assert s_test.env == Environment.TEST
    assert s_local.env == Environment.DEVELOPMENT


def test_secret_redaction():
    """Ensure secrets and database passwords are redacted in sanitized output."""
    settings = Settings(
        profile=Profile.LOCAL,
        database_url="postgresql+asyncpg://toki_user:supersecretpass@db.example.com:5432/toki_db",
        cloud_asr_api_key="sensitive_asr_key_value",
        cloud_llm_api_key="sensitive_llm_key_value",
        cloud_tts_api_key="sensitive_tts_key_value",
    )
    sanitized = settings.sanitized_dict()

    assert sanitized["cloud_asr_api_key"] == "[REDACTED]"
    assert sanitized["cloud_llm_api_key"] == "[REDACTED]"
    assert sanitized["cloud_tts_api_key"] == "[REDACTED]"
    assert "supersecretpass" not in sanitized["database_url"]
    assert "[REDACTED]" in sanitized["database_url"]


def test_raw_media_retention_rejection():
    """ADR-013: Raw child media retention must be rejected at boot."""
    with pytest.raises(
        (ConfigurationError, ValueError), match="raw_media_retention cannot be enabled"
    ):
        Settings(
            profile=Profile.LOCAL,
            raw_media_retention=True,
        )
