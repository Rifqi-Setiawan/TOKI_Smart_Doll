"""Table-driven unit tests for pure session finite-state machine (FR-001, FR-010, FR-022)."""

import pytest

from app.sessions.policies import ActivityPolicy, SessionContext
from app.sessions.state_machine import compute_transition
from app.sessions.states import SessionEvent, SessionState


@pytest.fixture
def base_context() -> SessionContext:
    return SessionContext(
        session_id="sess-fsm-001",
        device_id="TOKI-DEV-001",
        child_id="child-001",
        curriculum_version_id="curriculum-v1.0",
        state=SessionState.IDLE,
        state_version=1,
        current_turn_number=0,
        device_authenticated=True,
        consent_active=True,
        approved_curriculum_available=True,
    )


def test_normal_lifecycle_progression(base_context: SessionContext) -> None:
    """Acceptance Criterion 1: Normal path lifecycle transitions are explicit and valid."""
    ctx = base_context

    # 1. IDLE -> SESSION_STARTING
    res = compute_transition(ctx.state, SessionEvent.START_REQUESTED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.SESSION_STARTING
    ctx.state = res.to_state

    # 2. SESSION_STARTING -> GREETING
    res = compute_transition(ctx.state, SessionEvent.LOAD_COMPLETED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.GREETING
    ctx.state = res.to_state

    # 3. GREETING -> ACTIVITY_SELECTING
    res = compute_transition(ctx.state, SessionEvent.GREETING_DELIVERED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.ACTIVITY_SELECTING
    ctx.state = res.to_state

    # 4. ACTIVITY_SELECTING -> PROMPTING
    res = compute_transition(ctx.state, SessionEvent.ACTIVITY_SELECTED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.PROMPTING
    assert res.increment_turn is True
    assert res.reset_turn_retry is True
    ctx.state = res.to_state
    ctx.current_turn_number += 1

    # 5. PROMPTING -> LISTENING
    res = compute_transition(ctx.state, SessionEvent.PROMPT_DELIVERED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.LISTENING
    ctx.state = res.to_state

    # 6. LISTENING -> INTERPRETING
    res = compute_transition(ctx.state, SessionEvent.AUDIO_RECEIVED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.INTERPRETING
    ctx.state = res.to_state

    # 7. INTERPRETING -> FEEDBACK_PLANNING
    res = compute_transition(ctx.state, SessionEvent.ATTEMPT_RESOLVED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.FEEDBACK_PLANNING
    ctx.state = res.to_state

    # 8. FEEDBACK_PLANNING -> RESPONDING
    res = compute_transition(ctx.state, SessionEvent.RESPONSE_VALIDATED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.RESPONDING
    ctx.state = res.to_state

    # 9. RESPONDING -> MASTERY_UPDATING
    res = compute_transition(ctx.state, SessionEvent.PLAYBACK_ACKNOWLEDGED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.MASTERY_UPDATING
    ctx.state = res.to_state

    # 10. MASTERY_UPDATING -> ACTIVITY_SELECTING (loop for next activity)
    ctx.is_final_activity = False
    res = compute_transition(ctx.state, SessionEvent.MASTERY_COMMITTED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.ACTIVITY_SELECTING

    # 11. MASTERY_UPDATING -> SESSION_ENDING (when final activity complete)
    ctx.is_final_activity = True
    res = compute_transition(ctx.state, SessionEvent.MASTERY_COMMITTED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.SESSION_ENDING
    ctx.state = res.to_state

    # 12. SESSION_ENDING -> COMPLETED
    res = compute_transition(ctx.state, SessionEvent.CLOSING_DELIVERED, ctx)
    assert res.success is True
    assert res.to_state == SessionState.COMPLETED
    assert res.to_state.is_terminal() is True


def test_bounded_retry_in_no_speech(base_context: SessionContext) -> None:
    """Acceptance Criterion 4: Exactly one child-friendly retry before fallback (FR-010)."""
    ctx = base_context
    ctx.state = SessionState.LISTENING
    ctx.turn_retry_count = 0
    policy = ActivityPolicy(max_retries_per_turn=1)

    # Silence detected moves to NO_SPEECH
    res = compute_transition(ctx.state, SessionEvent.SILENCE_DETECTED, ctx, policy)
    assert res.success is True
    assert res.to_state == SessionState.NO_SPEECH
    ctx.state = res.to_state

    # First retry attempt is allowed
    res_retry1 = compute_transition(ctx.state, SessionEvent.RETRY_REQUESTED, ctx, policy)
    assert res_retry1.success is True
    assert res_retry1.to_state == SessionState.PROMPTING
    assert res_retry1.increment_turn_retry is True
    assert res_retry1.is_retry is True
    ctx.turn_retry_count += 1
    ctx.state = res_retry1.to_state

    # Prompt delivered -> listening -> silence again
    ctx.state = SessionState.NO_SPEECH

    # Second retry attempt is REJECTED (exceeds policy limit)
    res_retry2 = compute_transition(ctx.state, SessionEvent.RETRY_REQUESTED, ctx, policy)
    assert res_retry2.success is False
    assert "retry limit" in (res_retry2.reason or "").lower()

    # Fallback must be used instead
    res_fallback = compute_transition(ctx.state, SessionEvent.FALLBACK_TRIGGERED, ctx, policy)
    assert res_fallback.success is True
    assert res_fallback.to_state == SessionState.FEEDBACK_PLANNING
    assert res_fallback.is_fallback is True


def test_bounded_retry_in_low_confidence(base_context: SessionContext) -> None:
    """Acceptance Criterion 4: Low understanding retry bounded to 1 (FR-009, FR-010)."""
    ctx = base_context
    ctx.state = SessionState.INTERPRETING
    ctx.turn_retry_count = 0
    policy = ActivityPolicy(max_retries_per_turn=1)

    res = compute_transition(ctx.state, SessionEvent.CONFIDENCE_TOO_LOW, ctx, policy)
    assert res.success is True
    assert res.to_state == SessionState.LOW_UNDERSTANDING_CONFIDENCE
    ctx.state = res.to_state

    # Retry 1 succeeds
    res_r1 = compute_transition(ctx.state, SessionEvent.RETRY_REQUESTED, ctx, policy)
    assert res_r1.success is True
    assert res_r1.to_state == SessionState.PROMPTING
    ctx.turn_retry_count += 1

    # Second attempt fails
    ctx.state = SessionState.LOW_UNDERSTANDING_CONFIDENCE
    res_r2 = compute_transition(ctx.state, SessionEvent.RETRY_REQUESTED, ctx, policy)
    assert res_r2.success is False

    # Fallback to feedback planning succeeds
    res_fb = compute_transition(ctx.state, SessionEvent.FALLBACK_TRIGGERED, ctx, policy)
    assert res_fb.success is True
    assert res_fb.to_state == SessionState.FEEDBACK_PLANNING


def test_universal_stop_interrupt_from_any_active_state(base_context: SessionContext) -> None:
    """Acceptance Criterion 3: Stop action exits safely from all active states (FR-022, SEC-009)."""
    active_states = [
        SessionState.SESSION_STARTING,
        SessionState.GREETING,
        SessionState.ACTIVITY_SELECTING,
        SessionState.PROMPTING,
        SessionState.LISTENING,
        SessionState.INTERPRETING,
        SessionState.FEEDBACK_PLANNING,
        SessionState.RESPONDING,
        SessionState.MASTERY_UPDATING,
        SessionState.NO_SPEECH,
        SessionState.LOW_UNDERSTANDING_CONFIDENCE,
        SessionState.CONTENT_ERROR,
        SessionState.SAFETY_ESCALATION,
        SessionState.DEVICE_DISCONNECTED,
        SessionState.DEPENDENCY_DEGRADED,
    ]

    for state in active_states:
        ctx = SessionContext(
            session_id="sess-stop",
            device_id="d1",
            child_id="c1",
            curriculum_version_id="cv1",
            state=state,
        )
        res = compute_transition(state, SessionEvent.STOP_REQUESTED, ctx)
        assert res.success is True, f"Failed to stop from active state {state}"
        assert res.to_state == SessionState.SESSION_ENDING


def test_safety_escalation_interrupt_from_any_active_state(base_context: SessionContext) -> None:
    """Acceptance Criterion 3: Safety escalation immediately overrides any active state (FR-012)."""
    active_states = [
        SessionState.PROMPTING,
        SessionState.LISTENING,
        SessionState.INTERPRETING,
        SessionState.FEEDBACK_PLANNING,
        SessionState.RESPONDING,
        SessionState.MASTERY_UPDATING,
    ]

    for state in active_states:
        ctx = SessionContext(
            session_id="sess-safety",
            device_id="d1",
            child_id="c1",
            curriculum_version_id="cv1",
            state=state,
        )
        res = compute_transition(state, SessionEvent.SAFETY_TRIGGERED, ctx)
        assert res.success is True
        assert res.to_state == SessionState.SAFETY_ESCALATION


def test_device_reconnection_resumes_durable_state(base_context: SessionContext) -> None:
    """Verify device disconnect and resume to last durable state (FR-005)."""
    ctx = base_context
    ctx.state = SessionState.LISTENING
    ctx.last_durable_state = SessionState.PROMPTING

    # Disconnect
    res_disc = compute_transition(ctx.state, SessionEvent.DEVICE_DISCONNECTED, ctx)
    assert res_disc.success is True
    assert res_disc.to_state == SessionState.DEVICE_DISCONNECTED
    ctx.state = res_disc.to_state

    # Reconnect resumes last durable state
    res_recon = compute_transition(ctx.state, SessionEvent.DEVICE_RECONNECTED, ctx)
    assert res_recon.success is True
    assert res_recon.to_state == SessionState.PROMPTING

    # Reconnect timeout aborts session
    res_abort = compute_transition(ctx.state, SessionEvent.TIMEOUT_EXPIRED, ctx)
    assert res_abort.success is True
    assert res_abort.to_state == SessionState.SESSION_ABORTED


def test_terminal_states_reject_all_subsequent_events(base_context: SessionContext) -> None:
    """Terminal states (COMPLETED, SESSION_ABORTED) reject any further transitions."""
    for term_state in (SessionState.COMPLETED, SessionState.SESSION_ABORTED):
        ctx = base_context
        ctx.state = term_state
        for evt in SessionEvent:
            res = compute_transition(term_state, evt, ctx)
            assert res.success is False
            assert "terminal state" in (res.reason or "").lower()


def test_start_session_requires_consent_and_device(base_context: SessionContext) -> None:
    """Acceptance Criterion 2: Preconditions for session initiation (FR-003, DATA-010)."""
    # 1. Missing device authentication
    ctx1 = SessionContext(
        session_id="s1",
        device_id="",
        child_id="c1",
        curriculum_version_id="cv1",
        device_authenticated=False,
    )
    res1 = compute_transition(SessionState.IDLE, SessionEvent.START_REQUESTED, ctx1)
    assert res1.success is False
    assert "authentication" in (res1.reason or "").lower()

    # 2. Revoked consent
    ctx2 = SessionContext(
        session_id="s2",
        device_id="d1",
        child_id="c2",
        curriculum_version_id="cv1",
        consent_active=False,
    )
    res2 = compute_transition(SessionState.IDLE, SessionEvent.START_REQUESTED, ctx2)
    assert res2.success is False
    assert "consent" in (res2.reason or "").lower()
