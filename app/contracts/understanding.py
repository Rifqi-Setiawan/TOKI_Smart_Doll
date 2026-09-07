"""Answer assessment and understanding contracts (FR-008, FR-009, ADR-006, AI-005)."""

from enum import Enum

from pydantic import Field, model_validator

from app.contracts.base import CallbackCorrelation


class AssessmentStatus(str, Enum):
    """Pedagogical evaluation outcome of child response (FR-008, FR-009)."""

    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    AMBIGUOUS = "AMBIGUOUS"
    UNCERTAIN = "UNCERTAIN"
    NO_RESPONSE = "NO_RESPONSE"


class AssessmentReasonCode(str, Enum):
    """Deterministic explanation codes for assessment (OBS-005)."""

    EXACT_MATCH = "EXACT_MATCH"
    SYNONYM_MATCH = "SYNONYM_MATCH"
    NORMALIZED_MATCH = "NORMALIZED_MATCH"
    PHONETIC_MATCH = "PHONETIC_MATCH"
    SEMANTIC_RESOLVED = "SEMANTIC_RESOLVED"
    EXPLICIT_MISMATCH = "EXPLICIT_MISMATCH"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    NO_SPEECH_DETECTED = "NO_SPEECH_DETECTED"
    AUDIO_CORRUPTED = "AUDIO_CORRUPTED"


class AssessmentResult(CallbackCorrelation):
    """Deterministic or bounded evaluation of a child response turn (FR-008, FR-009, ADR-006)."""

    status: AssessmentStatus = Field(description="Normalized assessment status")
    target_concept: str = Field(description="Target curriculum concept ID or token")
    matched_phrase: str | None = Field(
        default=None, description="Recognized phrase that satisfied the match"
    )
    is_correct: bool = Field(description="Whether the turn counts as a correct learning attempt")
    confidence: float = Field(ge=0.0, le=1.0, description="Assessment decision confidence")
    reason_code: AssessmentReasonCode = Field(description="Deterministic reason explanation")
    policy_version: str = Field(default="RULE-ASSESS-1.0", description="Assessment rule version")
    evaluation_latency_ms: float = Field(
        ge=0.0, description="Assessment evaluation time in milliseconds"
    )

    @model_validator(mode="after")
    def validate_uncertainty_invariants(self) -> "AssessmentResult":
        # FR-009 & ADR-006: UNCERTAIN, AMBIGUOUS, or NO_RESPONSE must NEVER be marked
        # is_correct=True and UNCERTAIN/NO_RESPONSE must NEVER be persisted as
        # INCORRECT child failure.
        if self.status in (AssessmentStatus.UNCERTAIN, AssessmentStatus.NO_RESPONSE):
            if self.is_correct:
                raise ValueError(
                    f"FR-009 violation: Status {self.status} cannot be marked is_correct=True"
                )
        if self.status == AssessmentStatus.CORRECT and not self.is_correct:
            raise ValueError("Inconsistent assessment: status is CORRECT but is_correct is False")
        if self.status == AssessmentStatus.INCORRECT and self.is_correct:
            raise ValueError("Inconsistent assessment: status is INCORRECT but is_correct is True")
        return self
