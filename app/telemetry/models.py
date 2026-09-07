"""Per-turn root trace and telemetry data models (OBS-001, OBS-002, FR-021)."""

from datetime import datetime
from uuid import uuid4

from pydantic import Field

from app.contracts.base import ContractModel


class TurnTrace(ContractModel):
    """Complete, privacy-redacted operator evidence trace for one turn (OBS-001, OBS-002, FR-021).

    Invariants:
    - Never contains raw media, direct child names, unredacted secrets, or clinical terms.
    - Captures state transitions, curriculum provenance, evaluation reasons, fallback, and latency.
    """

    trace_id: str = Field(default_factory=lambda: str(uuid4()), description="Root trace identifier")
    session_id: str = Field(description="Pseudonymous session identifier")
    turn_id: str = Field(description="Turn identifier")
    turn_number: int = Field(ge=0, description="Sequential turn sequence within session")
    message_id: str = Field(description="Correlation inbound message identifier")

    # State Transition
    state_before: str = Field(description="Session state before turn execution")
    state_after: str = Field(description="Session state after turn execution")
    state_version: int = Field(ge=1, description="Durable state version number")

    # Content & Provenance (FR-011, ADR-007)
    curriculum_version: str = Field(description="Approved curriculum version token")
    module_id: str = Field(description="Curriculum module identifier")
    activity_id: str = Field(description="Curriculum activity identifier")
    template_id: str = Field(description="Approved prompt template identifier")
    item_token: str = Field(description="Target item token being exercised")

    # Assessment & Understanding (FR-008, FR-009, OBS-005)
    assessment_status: str = Field(description="Normalized assessment status (CORRECT, UNCERTAIN)")
    is_correct: bool = Field(description="Whether attempt counted as successful")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    reason_code: str = Field(description="Deterministic explanation reason code")
    is_uncertain: bool = Field(description="True if outcome is neutral uncertainty (OBS-005)")

    # Response & Fallbacks (FR-011, FR-012, REL-003)
    pedagogical_act: str = Field(description="Communicative feedback intent")
    spoken_text: str = Field(description="Child-facing spoken response (verified <= 25 words)")
    audio_asset_id: str = Field(description="Audio asset referenced for speech output")
    is_escalation: bool = Field(default=False, description="True if safety escalation triggered")
    paraphrase_applied: bool = Field(default=False, description="True if bounded paraphrase used")
    fallback_used: bool = Field(default=False, description="True if activity fallback invoked")

    # Transparent Mastery Progression (FR-015, ADR-011)
    previous_mastery_band: str | None = Field(default=None, description="Prior mastery band")
    new_mastery_band: str | None = Field(default=None, description="Resulting mastery band")
    mastery_explanation_code: str | None = Field(
        default=None, description="Mastery explanation code"
    )
    mastery_transition_reason: str | None = Field(default=None, description="Pedagogical reason")

    # Latency & Timestamps (OBS-002, REL-008)
    assessment_latency_ms: float = Field(ge=0.0, description="Time spent in assessment in ms")
    total_turn_latency_ms: float = Field(ge=0.0, description="Total turn handling time in ms")
    created_at: datetime = Field(description="Trace timestamp")
