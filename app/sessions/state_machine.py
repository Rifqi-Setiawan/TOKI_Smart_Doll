"""Pure, deterministic finite-state machine for TOKI session control plane (FR-001, ADR-003)."""

from dataclasses import dataclass

from app.sessions.policies import ActivityPolicy, SessionContext, can_retry_turn, can_start_session
from app.sessions.states import SessionEvent, SessionState


@dataclass(frozen=True)
class TransitionResult:
    """Outcome of a state transition computation."""

    success: bool
    from_state: SessionState
    to_state: SessionState
    event: SessionEvent
    reason: str | None = None
    increment_version: bool = True
    increment_turn: bool = False
    reset_turn_retry: bool = False
    increment_turn_retry: bool = False
    is_retry: bool = False
    is_fallback: bool = False


def compute_transition(
    current_state: SessionState,
    event: SessionEvent,
    context: SessionContext,
    policy: ActivityPolicy = ActivityPolicy(),
) -> TransitionResult:
    """Pure, side-effect-free transition decision function for one session turn cycle.

    Enforces:
    - Rejection of transitions out of terminal states (COMPLETED, SESSION_ABORTED).
    - Immediate stop/safety escalation interrupt from any active state (FR-012, FR-022, SEC-009).
    - Device disconnect handling and reconnection to last durable state (FR-005).
    - Bounded single retry before activity fallback (FR-010).
    - Bounded exit paths for all active states (REL-001).
    """
    # 1. Terminal states reject all subsequent events
    if current_state.is_terminal():
        return TransitionResult(
            success=False,
            from_state=current_state,
            to_state=current_state,
            event=event,
            reason=f"Session is in terminal state '{current_state.value}' and cannot accept events",
            increment_version=False,
        )

    # 2. Universal interrupts valid from any non-terminal active state
    if event == SessionEvent.STOP_REQUESTED:
        target = (
            SessionState.COMPLETED
            if current_state == SessionState.SESSION_ENDING
            else SessionState.SESSION_ENDING
        )
        return TransitionResult(
            success=True,
            from_state=current_state,
            to_state=target,
            event=event,
            reason="User or guardian requested stop (FR-022, SEC-009)",
        )

    if event == SessionEvent.SAFETY_TRIGGERED:
        return TransitionResult(
            success=True,
            from_state=current_state,
            to_state=SessionState.SAFETY_ESCALATION,
            event=event,
            reason="High-severity safety trigger override (FR-012, SEC-005)",
        )

    if event == SessionEvent.DEVICE_DISCONNECTED:
        return TransitionResult(
            success=True,
            from_state=current_state,
            to_state=SessionState.DEVICE_DISCONNECTED,
            event=event,
            reason="Physical device disconnected (FR-005)",
        )

    if event == SessionEvent.INTERNAL_ERROR:
        return TransitionResult(
            success=True,
            from_state=current_state,
            to_state=SessionState.CONTENT_ERROR,
            event=event,
            reason="Internal unrecoverable error encountered",
        )

    # 3. State-specific transition table
    if current_state == SessionState.IDLE:
        if event == SessionEvent.START_REQUESTED:
            if not context.device_authenticated:
                return TransitionResult(
                    success=False,
                    from_state=current_state,
                    to_state=current_state,
                    event=event,
                    reason="Device authentication required to start session (FR-003, SEC-002)",
                    increment_version=False,
                )
            if not context.consent_active:
                return TransitionResult(
                    success=False,
                    from_state=current_state,
                    to_state=current_state,
                    event=event,
                    reason="Active guardian consent required to start session (FR-003, DATA-010)",
                    increment_version=False,
                )
            if can_start_session(context):
                return TransitionResult(
                    success=True,
                    from_state=current_state,
                    to_state=SessionState.SESSION_STARTING,
                    event=event,
                )

    elif current_state == SessionState.SESSION_STARTING:
        if event == SessionEvent.LOAD_COMPLETED:
            if context.approved_curriculum_available:
                return TransitionResult(
                    success=True,
                    from_state=current_state,
                    to_state=SessionState.GREETING,
                    event=event,
                )
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.CONTENT_ERROR,
                event=event,
                reason="No approved curriculum found (FR-006)",
            )
        if event == SessionEvent.TIMEOUT_EXPIRED:
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.CONTENT_ERROR,
                event=event,
                reason="Session initialization timed out",
            )

    elif current_state == SessionState.GREETING:
        if event in (SessionEvent.GREETING_DELIVERED, SessionEvent.TIMEOUT_EXPIRED):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.ACTIVITY_SELECTING,
                event=event,
            )

    elif current_state == SessionState.ACTIVITY_SELECTING:
        if event in (SessionEvent.ACTIVITY_SELECTED, SessionEvent.TIMEOUT_EXPIRED):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.PROMPTING,
                event=event,
                increment_turn=True,
                reset_turn_retry=True,
            )
        if event == SessionEvent.SESSION_FINISHED:
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.SESSION_ENDING,
                event=event,
            )

    elif current_state == SessionState.PROMPTING:
        if event in (SessionEvent.PROMPT_DELIVERED, SessionEvent.TIMEOUT_EXPIRED):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.LISTENING,
                event=event,
            )

    elif current_state == SessionState.LISTENING:
        if event == SessionEvent.AUDIO_RECEIVED:
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.INTERPRETING,
                event=event,
            )
        if event in (SessionEvent.SILENCE_DETECTED, SessionEvent.TIMEOUT_EXPIRED):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.NO_SPEECH,
                event=event,
            )

    elif current_state == SessionState.INTERPRETING:
        if event == SessionEvent.ATTEMPT_RESOLVED:
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.FEEDBACK_PLANNING,
                event=event,
            )
        if event in (SessionEvent.CONFIDENCE_TOO_LOW, SessionEvent.TIMEOUT_EXPIRED):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.LOW_UNDERSTANDING_CONFIDENCE,
                event=event,
            )

    elif current_state == SessionState.FEEDBACK_PLANNING:
        if event in (SessionEvent.RESPONSE_VALIDATED, SessionEvent.TIMEOUT_EXPIRED):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.RESPONDING,
                event=event,
            )

    elif current_state == SessionState.RESPONDING:
        if event in (SessionEvent.PLAYBACK_ACKNOWLEDGED, SessionEvent.TIMEOUT_EXPIRED):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.MASTERY_UPDATING,
                event=event,
            )

    elif current_state == SessionState.MASTERY_UPDATING:
        if event in (
            SessionEvent.MASTERY_COMMITTED,
            SessionEvent.TIMEOUT_EXPIRED,
            SessionEvent.FALLBACK_TRIGGERED,
        ):
            target = (
                SessionState.SESSION_ENDING
                if context.is_final_activity
                else SessionState.ACTIVITY_SELECTING
            )
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=target,
                event=event,
            )

    elif current_state == SessionState.SESSION_ENDING:
        if event in (
            SessionEvent.CLOSING_DELIVERED,
            SessionEvent.TIMEOUT_EXPIRED,
            SessionEvent.STOP_REQUESTED,
        ):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.COMPLETED,
                event=event,
            )

    # 4. Exceptional states and bounded retry / fallback logic
    elif current_state in (
        SessionState.NO_SPEECH,
        SessionState.LOW_UNDERSTANDING_CONFIDENCE,
    ):
        if event == SessionEvent.RETRY_REQUESTED:
            if can_retry_turn(context, policy):
                return TransitionResult(
                    success=True,
                    from_state=current_state,
                    to_state=SessionState.PROMPTING,
                    event=event,
                    increment_turn_retry=True,
                    is_retry=True,
                )
            return TransitionResult(
                success=False,
                from_state=current_state,
                to_state=current_state,
                event=event,
                reason="Max child-friendly retry limit reached; fallback required (FR-010)",
                increment_version=False,
            )
        if event in (SessionEvent.FALLBACK_TRIGGERED, SessionEvent.TIMEOUT_EXPIRED):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.FEEDBACK_PLANNING,
                event=event,
                is_fallback=True,
            )

    elif current_state == SessionState.SAFETY_ESCALATION:
        if event in (
            SessionEvent.CLOSING_DELIVERED,
            SessionEvent.FALLBACK_TRIGGERED,
            SessionEvent.TIMEOUT_EXPIRED,
        ):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.SESSION_ENDING,
                event=event,
            )

    elif current_state == SessionState.DEVICE_DISCONNECTED:
        if event == SessionEvent.DEVICE_RECONNECTED:
            # Resume from last durable acknowledged state
            resume_target = (
                context.last_durable_state
                if context.last_durable_state != SessionState.IDLE
                else SessionState.PROMPTING
            )
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=resume_target,
                event=event,
                reason="Device reconnected, resuming last durable state (FR-005)",
            )
        if event == SessionEvent.TIMEOUT_EXPIRED:
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.SESSION_ABORTED,
                event=event,
                reason="Reconnect window expired, session aborted (FR-005)",
            )

    elif current_state == SessionState.CONTENT_ERROR:
        if event in (SessionEvent.FALLBACK_TRIGGERED, SessionEvent.TIMEOUT_EXPIRED):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.SESSION_ENDING,
                event=event,
            )

    elif current_state == SessionState.DEPENDENCY_DEGRADED:
        if event in (SessionEvent.FALLBACK_TRIGGERED, SessionEvent.TIMEOUT_EXPIRED):
            return TransitionResult(
                success=True,
                from_state=current_state,
                to_state=SessionState.PROMPTING,
                event=event,
                reason="Resuming with deterministic offline fallback (REL-005)",
            )

    # 5. Fallback for illegal event on current state
    return TransitionResult(
        success=False,
        from_state=current_state,
        to_state=current_state,
        event=event,
        reason=f"Event '{event.value}' is not valid from state '{current_state.value}'",
        increment_version=False,
    )
