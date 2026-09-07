"""Triggered bounded computer vision contracts (FR-020, ADR-010, AI-009)."""

from enum import Enum

from pydantic import Field, field_validator

from app.contracts.base import CallbackCorrelation, ContractModel


class VisionStatus(str, Enum):
    """Normalized outcomes for object detection (AI-009, ADR-010)."""

    DETECTED = "DETECTED"
    UNKNOWN = "UNKNOWN"
    ABSTAIN = "ABSTAIN"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class DetectedObject(ContractModel):
    """Recognized object entity within curated activity vocabulary (ADR-010)."""

    label: str = Field(description="Curated vocabulary object label")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score from vision model")
    bounding_box: list[float] | None = Field(
        default=None,
        description="Optional [x_min, y_min, x_max, y_max] normalized coordinates [0.0 - 1.0]",
    )

    @field_validator("bounding_box")
    @classmethod
    def validate_bounding_box(cls, value: list[float] | None) -> list[float] | None:
        if value is not None:
            if len(value) != 4:
                raise ValueError("Bounding box must contain exactly 4 coordinates")
            if not all(0.0 <= coord <= 1.0 for coord in value):
                raise ValueError("Bounding box coordinates must be normalized between 0.0 and 1.0")
        return value


class VisionObservation(CallbackCorrelation):
    """Typed observation payload from triggered camera snapshot (AI-002, AI-009, API-006)."""

    status: VisionStatus = Field(description="Vision detection outcome status")
    detected_objects: list[DetectedObject] = Field(
        default_factory=list, description="List of recognized approved objects"
    )
    freshness_ms: int = Field(
        ge=0, description="Age of the camera snapshot in milliseconds (freshness window check)"
    )
    latency_ms: float = Field(ge=0.0, description="Vision adapter execution latency")
    provider: str = Field(description="Vision model provider name")
    model_version: str = Field(description="Pinned model version identifier")
    error_message: str | None = Field(
        default=None, description="Redacted error detail if status is ERROR/TIMEOUT"
    )
