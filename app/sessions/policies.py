"""Policies, context, and guard predicates for session state transitions (FR-001, FR-010)."""

from dataclasses import dataclass

from app.sessions.states import SessionState


@dataclass(frozen=True)
class ActivityPolicy:
    """Activity execution policy parameters and deadlines (FR-010, REL-001)."""

    max_retries_per_turn: int = 1  # Exactly one child-friendly retry (FR-010)
    prompt_timeout_s: float = 4.0
    listening_timeout_s: float = 8.0
    interpreting_timeout_s: float = 1.3
    feedback_timeout_s: float = 0.7
    response_ack_timeout_s: float = 4.0
    session_start_timeout_s: float = 2.0


@dataclass
class SessionContext:
    """In-memory execution context for a session turn loop."""

    session_id: str
    device_id: str
    child_id: str
    curriculum_version_id: str
    state: SessionState = SessionState.IDLE
    state_version: int = 1
    current_turn_number: int = 0
    current_turn_id: str | None = None
    turn_retry_count: int = 0
    device_authenticated: bool = True
    consent_active: bool = True
    approved_curriculum_available: bool = True
    is_final_activity: bool = False
    last_durable_state: SessionState = SessionState.IDLE
    last_error: str | None = None


def can_start_session(ctx: SessionContext) -> bool:
    """Guard: Verify preconditions to start a new session (FR-003)."""
    return ctx.state == SessionState.IDLE and ctx.device_authenticated and ctx.consent_active


def can_retry_turn(ctx: SessionContext, policy: ActivityPolicy) -> bool:
    """Guard: Determine if another child-friendly retry is permitted (FR-010)."""
    return ctx.turn_retry_count < policy.max_retries_per_turn


def can_load_curriculum(ctx: SessionContext) -> bool:
    """Guard: Verify that approved curriculum version is available (FR-006)."""
    return ctx.approved_curriculum_available
