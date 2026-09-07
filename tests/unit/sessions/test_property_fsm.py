"""Property-based invariant and reachability tests for the session FSM (REL-001, FR-010, FR-022)."""

from collections import deque

from app.sessions.policies import ActivityPolicy, SessionContext
from app.sessions.state_machine import compute_transition
from app.sessions.states import SessionEvent, SessionState


def test_property_every_state_has_bounded_exit_to_terminal() -> None:
    """Property test: No deadlock or terminal hang exists in the state graph (REL-001).

    Using BFS from every state, verify that a path to a terminal state
    (COMPLETED or SESSION_ABORTED) is reachable within a finite number of transitions.
    """
    terminal_states = {SessionState.COMPLETED, SessionState.SESSION_ABORTED}
    all_states = list(SessionState)
    all_events = list(SessionEvent)

    for start_state in all_states:
        if start_state in terminal_states:
            continue

        # BFS search for terminal state
        visited = {start_state}
        queue = deque([(start_state, 0)])
        found_terminal = False

        while queue:
            curr_state, depth = queue.popleft()
            if curr_state in terminal_states:
                found_terminal = True
                break

            if depth > 15:  # Bound exploration depth
                continue

            ctx = SessionContext(
                session_id="prop-test",
                device_id="d1",
                child_id="c1",
                curriculum_version_id="cv1",
                state=curr_state,
                is_final_activity=True,
            )

            for evt in all_events:
                res = compute_transition(curr_state, evt, ctx)
                if res.success and res.to_state not in visited:
                    visited.add(res.to_state)
                    queue.append((res.to_state, depth + 1))

        assert (
            found_terminal
        ), f"State '{start_state}' cannot reach a terminal state! Potential deadlock."


def test_property_universal_stop_from_all_active_states() -> None:
    """Property test: STOP_REQUESTED must always succeed from every non-terminal state (FR-022)."""
    for state in SessionState:
        if state.is_terminal():
            continue

        ctx = SessionContext(
            session_id="prop-stop",
            device_id="d1",
            child_id="c1",
            curriculum_version_id="cv1",
            state=state,
        )
        res = compute_transition(state, SessionEvent.STOP_REQUESTED, ctx)
        assert res.success is True, f"STOP_REQUESTED failed from non-terminal state {state}"
        assert res.to_state in (
            SessionState.SESSION_ENDING,
            SessionState.COMPLETED,
        )


def test_property_universal_safety_from_all_active_states() -> None:
    """Property test: SAFETY_TRIGGERED succeeds from every non-terminal state (FR-012)."""
    for state in SessionState:
        if state.is_terminal():
            continue

        ctx = SessionContext(
            session_id="prop-safety",
            device_id="d1",
            child_id="c1",
            curriculum_version_id="cv1",
            state=state,
        )
        res = compute_transition(state, SessionEvent.SAFETY_TRIGGERED, ctx)
        assert res.success is True, f"SAFETY_TRIGGERED failed from non-terminal state {state}"
        assert res.to_state == SessionState.SAFETY_ESCALATION


def test_property_retry_bound_strict_enforcement() -> None:
    """Property test: Retries are bounded to max_retries_per_turn across varied limits (FR-010)."""
    for max_retries in [1, 2, 3]:
        policy = ActivityPolicy(max_retries_per_turn=max_retries)

        for exception_state in (
            SessionState.NO_SPEECH,
            SessionState.LOW_UNDERSTANDING_CONFIDENCE,
        ):
            ctx = SessionContext(
                session_id="prop-retry",
                device_id="d1",
                child_id="c1",
                curriculum_version_id="cv1",
                state=exception_state,
                turn_retry_count=0,
            )

            # Exactly max_retries must succeed
            for i in range(max_retries):
                res = compute_transition(exception_state, SessionEvent.RETRY_REQUESTED, ctx, policy)
                assert (
                    res.success is True
                ), f"Retry #{i+1} failed unexpectedly for limit {max_retries}"
                assert res.to_state == SessionState.PROMPTING
                ctx.turn_retry_count += 1

            # (max_retries + 1)-th attempt MUST fail
            res_fail = compute_transition(
                exception_state, SessionEvent.RETRY_REQUESTED, ctx, policy
            )
            assert (
                res_fail.success is False
            ), f"Retry was allowed past limit {max_retries} on state {exception_state}"
            assert "retry limit" in (res_fail.reason or "").lower()


def test_property_terminal_states_accept_zero_events() -> None:
    """Property test: In terminal states, all possible events are rejected."""
    terminal_states = [s for s in SessionState if s.is_terminal()]
    assert len(terminal_states) == 2  # COMPLETED, SESSION_ABORTED

    for term_state in terminal_states:
        ctx = SessionContext(
            session_id="prop-term",
            device_id="d1",
            child_id="c1",
            curriculum_version_id="cv1",
            state=term_state,
        )
        for evt in SessionEvent:
            res = compute_transition(term_state, evt, ctx)
            assert res.success is False, f"Event {evt} was accepted in terminal state {term_state}"
