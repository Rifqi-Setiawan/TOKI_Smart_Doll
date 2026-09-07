"""Runtime configuration and typed profile management for TOKI Backend.

Supports four operational profiles:
- 'test': In-memory/mock fixtures, fast timeouts, fake providers, strict determinism.
- 'local': Native developer workstation with local PostgreSQL and local/fake adapters.
- 'cloud': Cloud deployment expecting edge TLS, remote database, and external providers.
- 'demo_offline': Standalone competition demo twin; strictly zero external cloud dependencies.
"""

from enum import Enum
from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Profile(str, Enum):
    """Operational runtime profile."""

    TEST = "test"
    LOCAL = "local"
    CLOUD = "cloud"
    DEMO_OFFLINE = "demo_offline"


class Environment(str, Enum):
    """Deployment environment tier."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class ConfigurationError(ValueError):
    """Raised when runtime settings fail validation for the selected profile."""

    def __init__(self, message: str, field_name: str | None = None):
        self.field_name = field_name
        super().__init__(message)


class Settings(BaseSettings):
    """Application configuration with profile-aware validation."""

    model_config = SettingsConfigDict(
        env_prefix="TOKI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core profile and environment
    profile: Profile = Field(default=Profile.LOCAL, description="Runtime operational profile")
    env: Environment = Field(default=Environment.DEVELOPMENT, description="Environment tier")
    log_level: str = Field(default="INFO", description="Standard logging level")

    # Network and server
    app_host: str = Field(default="0.0.0.0", description="API bind host")
    app_port: int = Field(default=8000, description="API bind port")
    require_tls: bool = Field(default=False, description="Whether TLS is required at network edge")

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://toki:toki@localhost:5432/toki",
        description="Async SQLAlchemy database connection string",
    )
    database_pool_size: int = Field(default=10, description="Connection pool size")
    database_max_overflow: int = Field(default=5, description="Max overflow connections")

    # Speech and understanding adapters
    asr_provider: str = Field(default="fake", description="ASR provider: 'fake', 'managed', etc.")
    asr_model: str = Field(default="pinned-model", description="Pinned ASR model identifier")
    asr_deadline_ms: int = Field(default=1200, description="ASR deadline in ms")

    tts_provider: str = Field(default="cached", description="TTS provider: 'cached', 'managed'")
    tts_voice: str = Field(default="pinned-id-ID", description="Pinned Indonesian voice identifier")

    # Optional AI capabilities (ADR-004, ADR-006, ADR-007, ADR-010, ADR-016)
    semantic_enabled: bool = Field(default=False, description="Enable bounded semantic resolver")
    semantic_model: str = Field(
        default="pinned-model", description="Pinned semantic resolver model"
    )

    llm_paraphrase_enabled: bool = Field(
        default=False, description="Enable constrained LLM paraphrasing"
    )
    llm_model: str = Field(default="pinned-model", description="Pinned LLM model")

    vision_enabled: bool = Field(
        default=False, description="Enable triggered camera snapshot vision"
    )

    # Optional provider credentials (secrets loaded strictly from external environment)
    cloud_asr_api_key: str | None = Field(default=None, description="External ASR API key")
    cloud_llm_api_key: str | None = Field(default=None, description="External LLM API key")
    cloud_tts_api_key: str | None = Field(default=None, description="External TTS API key")

    # Governance, curriculum, and policies
    curriculum_version: str = Field(default="dev", description="Curriculum schema version")
    safety_policy_version: str = Field(
        default="CHILD-SAFETY-1.0", description="Child safety policy version"
    )
    mastery_policy_version: str = Field(
        default="RULE-MASTERY-1.0", description="Mastery scoring policy version"
    )
    raw_media_retention: bool = Field(default=False, description="Ephemeral media retention")

    @field_validator("raw_media_retention")
    @classmethod
    def validate_raw_media_retention(cls, value: bool) -> bool:
        # ADR-013: Raw child media must be ephemeral by default
        if value:
            raise ConfigurationError(
                "ADR-013 violation: raw_media_retention cannot be enabled in standard profile",
                field_name="raw_media_retention",
            )
        return value

    def check_startup_invariants(self) -> None:
        """Enforce architectural invariants per runtime profile."""
        profile = self.profile

        if profile == Profile.DEMO_OFFLINE:
            # ADR-014: demo_offline MUST boot without external AI credentials or cloud dependencies
            if self.cloud_asr_api_key or self.cloud_llm_api_key or self.cloud_tts_api_key:
                pass
            if self.semantic_enabled:
                raise ConfigurationError(
                    "demo_offline profile must not enable external semantic resolver",
                    field_name="semantic_enabled",
                )
            if self.llm_paraphrase_enabled:
                raise ConfigurationError(
                    "demo_offline profile must not enable external LLM paraphraser",
                    field_name="llm_paraphrase_enabled",
                )
            if self.vision_enabled:
                raise ConfigurationError(
                    "demo_offline profile must not enable cloud vision in standalone demo",
                    field_name="vision_enabled",
                )
            if self.asr_provider not in ("fake", "local", "cached"):
                raise ConfigurationError(
                    f"demo_offline cannot use external ASR provider '{self.asr_provider}'; "
                    "must be 'fake' or 'local'",
                    field_name="asr_provider",
                )
            if self.tts_provider not in ("cached", "local", "fake"):
                raise ConfigurationError(
                    f"demo_offline cannot use remote TTS provider '{self.tts_provider}'; "
                    "must be 'cached' or 'local'",
                    field_name="tts_provider",
                )

        elif profile == Profile.CLOUD:
            # API-003: External production cloud deployment requires TLS
            if not self.require_tls and self.env == Environment.PRODUCTION:
                raise ConfigurationError(
                    "Production cloud profile requires require_tls=True (API-003)",
                    field_name="require_tls",
                )
            # Note: Missing optional provider keys do NOT crash the boot (per API-007 and ADR-004).
            # Instead, the process boots into LIVE state and /health/demo reports DEGRADED.

        elif profile == Profile.TEST:
            # Fast, deterministic in-memory/fake settings
            pass

    @model_validator(mode="after")
    def validate_profile_invariants(self) -> "Settings":
        """Model validator running at instantiation time."""
        self.check_startup_invariants()
        return self

    def sanitized_dict(self) -> dict[str, Any]:
        """Return configuration dictionary with all secret fields redacted."""
        data = self.model_dump()
        secret_keys = {"cloud_asr_api_key", "cloud_llm_api_key", "cloud_tts_api_key"}
        for k in secret_keys:
            if data.get(k):
                data[k] = "[REDACTED]"
        # Redact password in database_url if present
        if "@" in data.get("database_url", ""):
            prefix, rest = data["database_url"].split("@", 1)
            if ":" in prefix:
                scheme_user = prefix.rsplit(":", 1)[0]
                data["database_url"] = f"{scheme_user}:[REDACTED]@{rest}"
        return data


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings for testing."""
    get_settings.cache_clear()
