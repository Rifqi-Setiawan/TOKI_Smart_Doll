"""Typed error response contracts with strict redaction guarantees (API-005)."""

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from app.contracts.base import ContractModel

SENSITIVE_KEY_SUBSTRINGS = (
    "key",
    "secret",
    "password",
    "token",
    "prompt",
    "stack",
    "traceback",
    "payload",
    "credential",
)


class ErrorCode(str, Enum):
    """Standardized machine-readable error codes (API-005)."""

    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    UNKNOWN_SCHEMA_VERSION = "UNKNOWN_SCHEMA_VERSION"
    STALE_STATE_VERSION = "STALE_STATE_VERSION"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    DEVICE_UNAUTHORIZED = "DEVICE_UNAUTHORIZED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorResponse(ContractModel):
    """Typed error envelope safe for external delivery (API-005)."""

    error_code: ErrorCode = Field(description="Categorized error identifier")
    message: str = Field(description="Safe user-facing or client diagnostic message")
    correlation_id: str = Field(description="Trace or session correlation identifier")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Redacted contextual diagnostic key-values"
    )

    @field_validator("details")
    @classmethod
    def redact_sensitive_details(cls, value: dict[str, Any]) -> dict[str, Any]:
        # API-005: Never leak stack traces, secrets, prompts, or provider payloads
        cleaned: dict[str, Any] = {}
        for k, v in value.items():
            lower_k = k.lower()
            if any(s in lower_k for s in SENSITIVE_KEY_SUBSTRINGS):
                cleaned[k] = "[REDACTED]"
            elif isinstance(v, dict):
                cleaned[k] = cls.redact_sensitive_details(v)
            else:
                cleaned[k] = v
        return cleaned
