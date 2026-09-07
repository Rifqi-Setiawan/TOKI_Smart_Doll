"""Unit tests for ResponsePlanner outcome dispatch and safety overrides.

(FR-010, FR-011, FR-012, FR-013, SEC-005, SEC-009, ADR-007, ADR-009)
"""

import pytest

from app.contracts.device import DisplayState, GestureType
from app.contracts.response import PedagogicalAct
from app.contracts.understanding import (
    AssessmentReasonCode,
    AssessmentResult,
    AssessmentStatus,
)
from app.curriculum.models import (
    ActivityAudioReferences,
    ActivityDifficulty,
    AnswerSpec,
    CurriculumActivity,
)
from app.response.planner import ResponsePlanner


@pytest.fixture
def sample_activity() -> CurriculumActivity:
    return CurriculumActivity(
        activity_token="body_parts_mata",
        module="body_parts",
        skill_token="body_parts",
        difficulty=ActivityDifficulty.BEGINNER,
        prompt_text="Tunjukkan mana matamu?",
        answer_spec=AnswerSpec(
            exact_matches=["mata"],
            synonyms=["netra"],
            phonetic_variations=["matak"],
        ),
        hints=["Yang kita pakai untuk melihat, lho!"],
        retry_prompt="Coba pegang bagian wajah untuk melihat ya.",
        audio_refs=ActivityAudioReferences(
            prompt_audio_id="audio-prompt-mata-01",
            fallback_audio_id="audio-fallback-mata-01",
            hint_audio_ids=["audio-hint-mata-01"],
        ),
    )


@pytest.fixture
def planner() -> ResponsePlanner:
    return ResponsePlanner()


def make_assessment(
    status: AssessmentStatus,
    reason: AssessmentReasonCode,
    matched: str | None = None,
) -> AssessmentResult:
    return AssessmentResult(
        session_id="sess-test",
        turn_id="turn-1",
        state_version=1,
        status=status,
        target_concept="mata",
        matched_phrase=matched,
        is_correct=(status == AssessmentStatus.CORRECT),
        confidence=1.0 if status == AssessmentStatus.CORRECT else 0.5,
        reason_code=reason,
        policy_version="RULE-ASSESS-1.0",
        evaluation_latency_ms=5.0,
    )


def test_correct_assessment_produces_praise(
    planner: ResponsePlanner, sample_activity: CurriculumActivity
) -> None:
    assessment = make_assessment(
        AssessmentStatus.CORRECT, AssessmentReasonCode.EXACT_MATCH, matched="mata"
    )
    plan = planner.plan_response(
        session_id="sess-1",
        turn_id="turn-1",
        assessment=assessment,
        activity=sample_activity,
        turn_retry_count=0,
    )

    assert plan.pedagogical_act == PedagogicalAct.PRAISE
    assert plan.display == DisplayState.HAPPY
    assert plan.gesture == GestureType.CELEBRATE
    assert plan.audio_asset_id == "audio-prompt-mata-01"
    assert "mata" in plan.spoken_text
    assert plan.is_escalation is False


def test_incorrect_first_turn_produces_bounded_retry(
    planner: ResponsePlanner, sample_activity: CurriculumActivity
) -> None:
    assessment = make_assessment(AssessmentStatus.INCORRECT, AssessmentReasonCode.EXPLICIT_MISMATCH)
    plan = planner.plan_response(
        session_id="sess-1",
        turn_id="turn-1",
        assessment=assessment,
        activity=sample_activity,
        turn_retry_count=0,  # First failure
    )

    assert plan.pedagogical_act == PedagogicalAct.RETRY_PROMPT
    assert plan.display == DisplayState.ENCOURAGING
    assert plan.gesture == GestureType.TILT_HEAD
    assert plan.audio_asset_id == "audio-fallback-mata-01"
    assert plan.spoken_text == sample_activity.retry_prompt


def test_incorrect_exhausted_retry_produces_hint(
    planner: ResponsePlanner, sample_activity: CurriculumActivity
) -> None:
    assessment = make_assessment(AssessmentStatus.INCORRECT, AssessmentReasonCode.EXPLICIT_MISMATCH)
    plan = planner.plan_response(
        session_id="sess-1",
        turn_id="turn-1",
        assessment=assessment,
        activity=sample_activity,
        turn_retry_count=1,  # Retry exhausted
    )

    assert plan.pedagogical_act == PedagogicalAct.HINT
    assert plan.display == DisplayState.CURIOUS
    assert plan.gesture == GestureType.NOD
    assert plan.audio_asset_id == "audio-hint-mata-01"
    assert plan.spoken_text == sample_activity.hints[0]


def test_uncertain_first_turn_produces_retry(
    planner: ResponsePlanner, sample_activity: CurriculumActivity
) -> None:
    assessment = make_assessment(AssessmentStatus.UNCERTAIN, AssessmentReasonCode.LOW_CONFIDENCE)
    plan = planner.plan_response(
        session_id="sess-1",
        turn_id="turn-1",
        assessment=assessment,
        activity=sample_activity,
        turn_retry_count=0,
    )

    assert plan.pedagogical_act == PedagogicalAct.RETRY_PROMPT
    assert plan.display == DisplayState.ENCOURAGING


def test_no_response_first_turn_produces_retry(
    planner: ResponsePlanner, sample_activity: CurriculumActivity
) -> None:
    assessment = make_assessment(
        AssessmentStatus.NO_RESPONSE, AssessmentReasonCode.NO_SPEECH_DETECTED
    )
    plan = planner.plan_response(
        session_id="sess-1",
        turn_id="turn-1",
        assessment=assessment,
        activity=sample_activity,
        turn_retry_count=0,
    )

    assert plan.pedagogical_act == PedagogicalAct.RETRY_PROMPT
    assert plan.display == DisplayState.ENCOURAGING


def test_high_severity_transcript_immediately_overrides_curriculum(
    planner: ResponsePlanner, sample_activity: CurriculumActivity
) -> None:
    """FR-012, SEC-005: Danger or distress overrides curriculum even if assessment is present."""
    assessment = make_assessment(
        AssessmentStatus.CORRECT, AssessmentReasonCode.EXACT_MATCH, matched="mata"
    )
    plan = planner.plan_response(
        session_id="sess-1",
        turn_id="turn-1",
        assessment=assessment,
        activity=sample_activity,
        turn_retry_count=0,
        raw_transcript="aduh sakit toki berdarah",
    )

    assert plan.is_escalation is True
    assert plan.pedagogical_act == PedagogicalAct.ESCALATION
    assert plan.provenance.module_id == "safety"
    assert plan.audio_asset_id == "audio-canned-safe-danger-01"


def test_plan_safe_stop_produces_canned_closing_without_providers(
    planner: ResponsePlanner,
) -> None:
    """SEC-009, FR-022: Physical/guardian stop works without dynamic ASR/TTS/LLM."""
    plan = planner.plan_safe_stop(session_id="sess-stop", turn_id="turn-99")

    assert plan.pedagogical_act == PedagogicalAct.CLOSING
    assert plan.display == DisplayState.HAPPY
    assert plan.gesture == GestureType.WAVE
    assert plan.audio_asset_id == "audio-canned-safe-stop-01"
    assert plan.is_escalation is False


def test_missing_activity_fails_closed_to_reviewed_generic_fallback(
    planner: ResponsePlanner,
) -> None:
    """ADR-007: Missing template uses reviewed generic fallback, never hallucinated LLM."""
    assessment = make_assessment(AssessmentStatus.CORRECT, AssessmentReasonCode.EXACT_MATCH)
    plan = planner.plan_response(
        session_id="sess-1",
        turn_id="turn-1",
        assessment=assessment,
        activity=None,  # Missing activity
    )

    assert plan.pedagogical_act == PedagogicalAct.CORRECTIVE_FEEDBACK
    assert plan.provenance.module_id == "fallback"
    assert plan.audio_asset_id == "audio-canned-generic-fallback-01"
    assert plan.is_escalation is False


def test_decision_table_fixture_evaluation(
    planner: ResponsePlanner, sample_activity: CurriculumActivity
) -> None:
    import json
    from pathlib import Path

    fixture_path = (
        Path(__file__).parent.parent.parent / "fixtures" / "response" / "decision_table_cases.json"
    )
    assert fixture_path.exists(), f"Missing fixture file: {fixture_path}"

    with open(fixture_path, encoding="utf-8") as f:
        cases = json.load(f)

    for case in cases:
        status = AssessmentStatus(case["assessment_status"])
        reason = AssessmentReasonCode(case["assessment_reason"])
        assessment = make_assessment(status, reason, matched="mata")

        plan = planner.plan_response(
            session_id="sess-fixture",
            turn_id=case["id"],
            assessment=assessment,
            activity=sample_activity,
            turn_retry_count=case["turn_retry_count"],
            raw_transcript=case["raw_transcript"],
        )

        assert plan.pedagogical_act.value == case["expected_act"]
        assert plan.is_escalation == case["expected_is_escalation"]
        assert plan.display.value == case["expected_display"]
        assert plan.gesture.value == case["expected_gesture"]
