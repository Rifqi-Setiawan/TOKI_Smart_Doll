"""Unit tests for turn tracer, trace completeness, and telemetry failure isolation.

Requirements: OBS-001, OBS-002, OBS-004, FR-021.
"""

from app.telemetry.models import TurnTrace
from app.telemetry.tracer import TurnTracer


def test_turn_trace_captures_complete_evidence() -> None:
    """OBS-001, OBS-002, FR-021: Sample turn is completely traceable across all stages."""
    tracer = TurnTracer()

    trace = TurnTracer.create_trace(
        session_id="sess-trace-01",
        turn_id="turn-trace-01",
        turn_number=1,
        message_id="msg-trace-01",
        state_before="INITIALIZING",
        state_after="IN_PROGRESS",
        state_version=2,
        curriculum_version="curriculum-v1.0",
        module_id="colors",
        activity_id="color_naming",
        template_id="tpl_color_red_01",
        item_token="item.colors.red",
        assessment_status="CORRECT",
        is_correct=True,
        confidence=0.96,
        reason_code="EXACT_MATCH",
        pedagogical_act="PRAISE",
        spoken_text="Hebat sekali, itu warna merah!",
        audio_asset_id="audio-asset-praise-01",
        is_escalation=False,
        paraphrase_applied=False,
        fallback_used=False,
        previous_mastery_band="INTRODUCED",
        new_mastery_band="PRACTICING",
        mastery_explanation_code="PROMOTED_PRACTICING",
        mastery_transition_reason="First successful attempt demonstrates emerging proficiency",
        assessment_latency_ms=14.5,
        total_turn_latency_ms=85.0,
    )

    tracer.record_trace(trace)

    retrieved = tracer.get_trace(trace.trace_id)
    assert retrieved is not None
    assert retrieved.session_id == "sess-trace-01"
    assert retrieved.state_before == "INITIALIZING"
    assert retrieved.state_after == "IN_PROGRESS"
    assert retrieved.curriculum_version == "curriculum-v1.0"
    assert retrieved.item_token == "item.colors.red"
    assert retrieved.assessment_status == "CORRECT"
    assert retrieved.reason_code == "EXACT_MATCH"
    assert retrieved.pedagogical_act == "PRAISE"
    assert retrieved.previous_mastery_band == "INTRODUCED"
    assert retrieved.new_mastery_band == "PRACTICING"
    assert retrieved.mastery_explanation_code == "PROMOTED_PRACTICING"
    assert retrieved.assessment_latency_ms == 14.5
    assert retrieved.total_turn_latency_ms == 85.0


def test_telemetry_outage_does_not_fail_turn_execution() -> None:
    """OBS-004: Telemetry exporter crashes/outages are safely caught and swallowed."""

    def broken_exporter(trace: TurnTrace) -> None:
        raise ConnectionRefusedError("Simulated remote OpenTelemetry exporter crash")

    tracer = TurnTracer(exporter=broken_exporter)

    trace = TurnTracer.create_trace(
        session_id="sess-fail-01",
        turn_id="turn-fail-01",
        turn_number=1,
        message_id="msg-fail-01",
        state_before="IN_PROGRESS",
        state_after="IN_PROGRESS",
        state_version=3,
        curriculum_version="curriculum-v1.0",
        module_id="colors",
        activity_id="color_naming",
        template_id="tpl_color_red_01",
        item_token="item.colors.red",
        assessment_status="CORRECT",
        is_correct=True,
        confidence=0.92,
        reason_code="EXACT_MATCH",
        pedagogical_act="PRAISE",
        spoken_text="Bagus!",
        audio_asset_id="audio-asset-praise-01",
        assessment_latency_ms=12.0,
        total_turn_latency_ms=50.0,
    )

    # Invariant: Must NOT raise ConnectionRefusedError or any other exception
    tracer.record_trace(trace)

    # Verify failure was tracked internally
    assert tracer.exporter_failures_count == 1
    # Verify trace is still retained locally
    assert tracer.get_trace(trace.trace_id) is not None


def test_get_traces_for_session() -> None:
    """Test session trace filtering."""
    tracer = TurnTracer()

    t1 = TurnTracer.create_trace(
        session_id="sess-batch",
        turn_id="t1",
        turn_number=1,
        message_id="m1",
        state_before="INITIALIZING",
        state_after="IN_PROGRESS",
        state_version=2,
        curriculum_version="c1",
        module_id="colors",
        activity_id="a1",
        template_id="tmp1",
        item_token="i1",
        assessment_status="CORRECT",
        is_correct=True,
        confidence=0.9,
        reason_code="EXACT_MATCH",
        pedagogical_act="PRAISE",
        spoken_text="Bagus!",
        audio_asset_id="aud1",
        assessment_latency_ms=10.0,
        total_turn_latency_ms=40.0,
    )
    t2 = TurnTracer.create_trace(
        session_id="sess-batch",
        turn_id="t2",
        turn_number=2,
        message_id="m2",
        state_before="IN_PROGRESS",
        state_after="IN_PROGRESS",
        state_version=3,
        curriculum_version="c1",
        module_id="colors",
        activity_id="a1",
        template_id="tmp1",
        item_token="i1",
        assessment_status="INCORRECT",
        is_correct=False,
        confidence=0.85,
        reason_code="EXPLICIT_MISMATCH",
        pedagogical_act="RETRY_PROMPT",
        spoken_text="Ayo coba lagi ya!",
        audio_asset_id="aud2",
        assessment_latency_ms=11.0,
        total_turn_latency_ms=45.0,
    )

    tracer.record_trace(t1)
    tracer.record_trace(t2)

    session_traces = tracer.get_traces_for_session("sess-batch")
    assert len(session_traces) == 2
    assert session_traces[0].turn_id == "t1"
    assert session_traces[1].turn_id == "t2"
