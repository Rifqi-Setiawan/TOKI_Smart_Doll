"""Unit tests for progress projector, rebuild equivalence, and uncertainty separation.

Requirements: FR-016, FR-017, OBS-005.
"""

from datetime import UTC, datetime
from uuid import uuid4

from app.analytics.projector import EventProjector
from app.persistence.models import DomainEvent


def make_turn_event(
    session_id: str,
    turn_number: int,
    skill_token: str,
    is_correct: bool,
    reason_code: str,
    mastery_band: str | None = None,
    created_at: datetime | None = None,
) -> DomainEvent:
    now = created_at or datetime.now(UTC)
    payload = {
        "turn_number": turn_number,
        "skill_token": skill_token,
        "item_token": f"item.{skill_token}",
        "message_id": f"msg-{uuid4()}",
        "is_correct": is_correct,
        "reason_code": reason_code,
        "state_version": turn_number + 1,
        "session_state": "IN_PROGRESS",
    }
    if mastery_band:
        payload["mastery"] = {
            "previous_band": "INTRODUCED",
            "new_band": mastery_band,
            "practice_count": turn_number,
            "success_count": 1 if is_correct else 0,
            "explanation_code": "EVAL_OK",
        }

    return DomainEvent(
        id=str(uuid4()),
        session_id=session_id,
        event_sequence=turn_number,
        event_type="session.turn_resolved",
        payload=payload,
        privacy_class="OPERATIONAL",
        created_at=now,
    )


def test_rebuild_produces_identical_projection_from_event_stream() -> None:
    """FR-017: Rebuilding from raw events produces identical output to incremental processing."""
    projector_live = EventProjector()
    projector_rebuild = EventProjector()

    child_id = "child-demo-100"
    session_id = "sess-100"
    child_map = {session_id: child_id}

    events = [
        make_turn_event(session_id, 1, "colors.red", True, "EXACT_MATCH", "PRACTICING"),
        make_turn_event(session_id, 2, "colors.red", False, "EXPLICIT_MISMATCH"),
        make_turn_event(session_id, 3, "body_parts.mata", True, "EXACT_MATCH", "PRACTICING"),
    ]

    # Live processing
    for ev in events:
        projector_live.process_event(
            event_id=ev.id,
            session_id=session_id,
            event_sequence=ev.event_sequence,
            event_type=ev.event_type,
            payload=ev.payload,
            created_at=ev.created_at,
            child_id=child_id,
        )

    live_dto = projector_live.get_child_progress(child_id)

    # Rebuild from event list
    rebuild_dtos = projector_rebuild.rebuild(events, child_map)
    rebuilt_dto = rebuild_dtos[child_id]

    assert live_dto.model_dump() == rebuilt_dto.model_dump()
    assert live_dto.total_sessions_count == 1
    assert live_dto.total_activities_count == 2  # 2 correct answers


def test_duplicate_event_delivery_is_idempotent() -> None:
    """DATA-004, FR-017: Processing the same event twice does not double counts."""
    projector = EventProjector()
    child_id = "child-1"
    session_id = "sess-1"

    ev = make_turn_event(session_id, 1, "colors.red", True, "EXACT_MATCH")

    first_result = projector.process_event(
        event_id=ev.id,
        session_id=session_id,
        event_sequence=ev.event_sequence,
        event_type=ev.event_type,
        payload=ev.payload,
        created_at=ev.created_at,
        child_id=child_id,
    )
    assert first_result is True

    # Replay same event
    replay_result = projector.process_event(
        event_id=ev.id,
        session_id=session_id,
        event_sequence=ev.event_sequence,
        event_type=ev.event_type,
        payload=ev.payload,
        created_at=ev.created_at,
        child_id=child_id,
    )
    assert replay_result is False

    dto = projector.get_child_progress(child_id)
    assert len(dto.skills) == 1
    assert dto.skills[0].practice_count == 1


def test_system_uncertainty_is_distinct_from_child_incorrectness() -> None:
    """OBS-005, FR-009: Low confidence / silence is tracked as neutral uncertainty, not failure."""
    projector = EventProjector()
    child_id = "child-2"
    session_id = "sess-2"

    # Turn 1: Low confidence ASR (neutral uncertainty)
    ev1 = make_turn_event(session_id, 1, "colors.blue", False, "LOW_CONFIDENCE")
    # Turn 2: Silence / no response (neutral uncertainty)
    ev2 = make_turn_event(session_id, 2, "colors.blue", False, "NO_SPEECH_DETECTED")
    # Turn 3: Explicit child incorrectness (child answered 'red' instead of 'blue')
    ev3 = make_turn_event(session_id, 3, "colors.blue", False, "EXPLICIT_MISMATCH")
    # Turn 4: Child correct answer
    ev4 = make_turn_event(session_id, 4, "colors.blue", True, "EXACT_MATCH")

    for ev in [ev1, ev2, ev3, ev4]:
        projector.process_event(
            event_id=ev.id,
            session_id=session_id,
            event_sequence=ev.event_sequence,
            event_type=ev.event_type,
            payload=ev.payload,
            created_at=ev.created_at,
            child_id=child_id,
        )

    dto = projector.get_child_progress(child_id)
    skill_progress = dto.skills[0]

    # Total turns: 4
    assert skill_progress.practice_count == 4

    # Out of 4 practices, 2 were neutral uncertainty (Turn 1 and Turn 2).
    # Eligible attempts for child scoring = 4 - 2 = 2 (Turn 3 incorrect, Turn 4 correct).
    # Child success rate = 1 correct / 2 eligible = 0.50 (50%).
    # If uncertainty had been penalized as incorrect, success rate would be 1/4 = 0.25 (25%).
    assert skill_progress.recent_success_rate == 0.50


def test_parent_tip_and_copy_are_strictly_non_clinical() -> None:
    """SEC-010, FR-016: Parent progress summaries must remain educational and non-clinical."""
    projector = EventProjector()
    child_id = "child-3"
    session_id = "sess-3"

    ev = make_turn_event(session_id, 1, "body_parts.telinga", True, "EXACT_MATCH")
    projector.process_event(
        event_id=ev.id,
        session_id=session_id,
        event_sequence=ev.event_sequence,
        event_type=ev.event_type,
        payload=ev.payload,
        created_at=ev.created_at,
        child_id=child_id,
    )

    dto = projector.get_child_progress(child_id)
    assert len(dto.recent_sessions) == 1
    session_summary = dto.recent_sessions[0]

    # Validates parent tip does not contain clinical words
    assert "bercermin" in session_summary.parent_tip or "senyuman" in session_summary.parent_tip
    assert not any(
        w in session_summary.parent_tip.lower()
        for w in ["diagnosis", "terapi", "gangguan", "kelainan", "speech delay"]
    )


def test_projection_lag_is_measured() -> None:
    """Requirement: Measure projector lag for eventual consistency observability."""
    projector = EventProjector()
    child_id = "child-4"
    session_id = "sess-4"

    ev = make_turn_event(session_id, 1, "colors.kuning", True, "EXACT_MATCH")
    projector.process_event(
        event_id=ev.id,
        session_id=session_id,
        event_sequence=ev.event_sequence,
        event_type=ev.event_type,
        payload=ev.payload,
        created_at=ev.created_at,
        child_id=child_id,
    )

    assert len(projector.lag_measurements_ms) == 1
    assert projector.lag_measurements_ms[0] >= 0.0
