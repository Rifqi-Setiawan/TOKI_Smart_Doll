"""Speech adapter contracts for ASR and TTS (AI-002, API-006, ADR-004, ADR-008, ADR-009)."""

from enum import Enum

from pydantic import Field, field_validator

from app.contracts.base import CallbackCorrelation


class ASRStatus(str, Enum):
    """Normalized outcomes for speech recognition (AI-002)."""

    SUCCESS = "SUCCESS"
    ABSTAIN = "ABSTAIN"
    UNCERTAIN = "UNCERTAIN"
    NO_SPEECH = "NO_SPEECH"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class TTSSource(str, Enum):
    """Origin of rendered audio asset (ADR-009)."""

    CACHED = "CACHED"
    DYNAMIC = "DYNAMIC"
    FALLBACK = "FALLBACK"


class ASRResult(CallbackCorrelation):
    """Typed probabilistic speech hypothesis from ASR adapter (AI-002, API-006)."""

    status: ASRStatus = Field(description="Normalized outcome status")
    transcript: str = Field(default="", description="Transcribed Indonesian text hypothesis")
    confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score [0.0 - 1.0] if provided by adapter",
    )
    language: str = Field(default="id-ID", description="Detected or pinned language code")
    duration_ms: int = Field(ge=0, description="Audio segment duration in milliseconds")
    latency_ms: float = Field(ge=0.0, description="Adapter execution latency in milliseconds")
    provider: str = Field(description="Name of provider adapter (e.g. 'fake', 'local', 'managed')")
    model_version: str = Field(description="Pinned model version identifier")
    is_final: bool = Field(default=True, description="Whether this is final turn hypothesis")
    error_message: str | None = Field(
        default=None, description="Redacted error description if status is ERROR/TIMEOUT"
    )

    @field_validator("transcript")
    @classmethod
    def normalize_transcript(cls, value: str) -> str:
        return value.strip()


class TTSResult(CallbackCorrelation):
    """Audio rendering result from TTS adapter (API-006, ADR-009)."""

    source: TTSSource = Field(description="Audio source: CACHED, DYNAMIC, or FALLBACK")
    audio_asset_id: str | None = Field(default=None, description="Pre-generated audio asset ID")
    audio_uri: str | None = Field(default=None, description="Ephemeral audio location or path")
    duration_ms: int = Field(ge=0, description="Audio playback duration in milliseconds")
    latency_ms: float = Field(ge=0.0, description="TTS generation latency in milliseconds")
    provider: str = Field(description="TTS provider name")
    voice_id: str = Field(description="Indonesian voice identifier")
    error_message: str | None = Field(default=None, description="Error detail if failed")
