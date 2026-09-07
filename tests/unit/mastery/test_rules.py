"""Unit tests for transparent rule-based mastery progression policy (FR-009, FR-015, ADR-011)."""

import pytest

from app.contracts.understanding import AssessmentReasonCode, AssessmentResult, AssessmentStatus
from app.mastery.models import MasteryBand
from app.mastery.rules import RuleBasedMasteryPolicy


@pytest.fixture
def policy() -> RuleBasedMasteryPolicy:
    return RuleBasedMasteryPolicy(policy_version="MASTERY-RULE-1.0")


def create_assessment(
    status: AssessmentStatus,
    is_correct: bool,
    confidence: float,
    reason_code: AssessmentReasonCode,
    matched_phrase: str | None = None,
) -> AssessmentResult:
    return AssessmentResult(
        session_id="sess-1",
        turn_id="turn-1",
        state_version=1,
        target_concept="colors.red",
        status=status,
        is_correct=is_correct,
        confidence=confidence,
        reason_code=reason_code,
        matched_phrase=matched_phrase,
        evaluation_latency_ms=12.5,
    )


def test_uncertain_assessment_is_ineligible_for_mastery_update(
    policy: RuleBasedMasteryPolicy,
) -> None:
    """FR-009, FR-015: Uncertain evidence must not update mastery or counts."""
    assessment = create_assessment(
        status=AssessmentStatus.UNCERTAIN,
        is_correct=False,
        confidence=0.35,
        reason_code=AssessmentReasonCode.LOW_CONFIDENCE,
    )

    result = policy.evaluate_mastery(
        child_id="child-123",
        skill_token="colors.red",
        current_band=MasteryBand.INTRODUCED,
        current_practice_count=2,
        current_success_count=1,
        assessment=assessment,
    )

    assert result.is_updated is False
    assert result.previous_band == MasteryBand.INTRODUCED
    assert result.new_band == MasteryBand.INTRODUCED
    assert result.practice_count == 2
    assert result.success_count == 1
    assert result.explanation_code == "SKIPPED_UNCERTAIN"


def test_no_response_assessment_is_ineligible_for_mastery_update(
    policy: RuleBasedMasteryPolicy,
) -> None:
    """FR-009, FR-015: Silence / no response must not penalize child mastery."""
    assessment = create_assessment(
        status=AssessmentStatus.NO_RESPONSE,
        is_correct=False,
        confidence=0.0,
        reason_code=AssessmentReasonCode.NO_SPEECH_DETECTED,
    )

    result = policy.evaluate_mastery(
        child_id="child-123",
        skill_token="colors.red",
        current_band=MasteryBand.PRACTICING,
        current_practice_count=3,
        current_success_count=2,
        assessment=assessment,
    )

    assert result.is_updated is False
    assert result.new_band == MasteryBand.PRACTICING
    assert result.practice_count == 3
    assert result.success_count == 2
    assert result.explanation_code == "SKIPPED_UNCERTAIN"


def test_introduced_first_success_promotes_to_practicing(
    policy: RuleBasedMasteryPolicy,
) -> None:
    """ADR-011: First successful attempt promotes INTRODUCED to PRACTICING."""
    assessment = create_assessment(
        status=AssessmentStatus.CORRECT,
        is_correct=True,
        confidence=0.92,
        reason_code=AssessmentReasonCode.EXACT_MATCH,
        matched_phrase="red",
    )

    result = policy.evaluate_mastery(
        child_id="child-123",
        skill_token="colors.red",
        current_band=MasteryBand.INTRODUCED,
        current_practice_count=0,
        current_success_count=0,
        assessment=assessment,
    )

    assert result.is_updated is True
    assert result.previous_band == MasteryBand.INTRODUCED
    assert result.new_band == MasteryBand.PRACTICING
    assert result.practice_count == 1
    assert result.success_count == 1
    assert result.explanation_code == "PROMOTED_PRACTICING"


def test_introduced_failure_maintains_introduced_band(
    policy: RuleBasedMasteryPolicy,
) -> None:
    """ADR-011: Unsuccessful attempt maintains INTRODUCED band and increments practice count."""
    assessment = create_assessment(
        status=AssessmentStatus.INCORRECT,
        is_correct=False,
        confidence=0.88,
        reason_code=AssessmentReasonCode.EXPLICIT_MISMATCH,
        matched_phrase="blue",
    )

    result = policy.evaluate_mastery(
        child_id="child-123",
        skill_token="colors.red",
        current_band=MasteryBand.INTRODUCED,
        current_practice_count=0,
        current_success_count=0,
        assessment=assessment,
    )

    assert result.is_updated is True
    assert result.previous_band == MasteryBand.INTRODUCED
    assert result.new_band == MasteryBand.INTRODUCED
    assert result.practice_count == 1
    assert result.success_count == 0
    assert result.explanation_code == "MAINTAINED_BAND"


def test_practicing_promotes_to_acquired_when_thresholds_met(
    policy: RuleBasedMasteryPolicy,
) -> None:
    """ADR-011: PRACTICING promotes to ACQUIRED on >=3 successes and >=75% accuracy."""
    assessment = create_assessment(
        status=AssessmentStatus.CORRECT,
        is_correct=True,
        confidence=0.95,
        reason_code=AssessmentReasonCode.EXACT_MATCH,
        matched_phrase="red",
    )

    # Prior state: 3 practices, 2 successes. New state: 4 practices, 3 successes (75%)
    result = policy.evaluate_mastery(
        child_id="child-123",
        skill_token="colors.red",
        current_band=MasteryBand.PRACTICING,
        current_practice_count=3,
        current_success_count=2,
        assessment=assessment,
    )

    assert result.is_updated is True
    assert result.previous_band == MasteryBand.PRACTICING
    assert result.new_band == MasteryBand.ACQUIRED
    assert result.practice_count == 4
    assert result.success_count == 3
    assert result.explanation_code == "PROMOTED_ACQUIRED"


def test_practicing_maintains_band_when_success_count_under_three(
    policy: RuleBasedMasteryPolicy,
) -> None:
    """PRACTICING remains if success count is less than 3 even with 100% accuracy."""
    assessment = create_assessment(
        status=AssessmentStatus.CORRECT,
        is_correct=True,
        confidence=0.90,
        reason_code=AssessmentReasonCode.EXACT_MATCH,
        matched_phrase="red",
    )

    # Prior state: 1 practice, 1 success.
    # New state: 2 practices, 2 successes (100%, but <3 successes)
    result = policy.evaluate_mastery(
        child_id="child-123",
        skill_token="colors.red",
        current_band=MasteryBand.PRACTICING,
        current_practice_count=1,
        current_success_count=1,
        assessment=assessment,
    )

    assert result.is_updated is True
    assert result.new_band == MasteryBand.PRACTICING
    assert result.practice_count == 2
    assert result.success_count == 2
    assert result.explanation_code == "MAINTAINED_BAND"


def test_practicing_maintains_band_when_accuracy_under_75_percent(
    policy: RuleBasedMasteryPolicy,
) -> None:
    """PRACTICING remains if accuracy is below 75% even with >=3 successes."""
    assessment = create_assessment(
        status=AssessmentStatus.CORRECT,
        is_correct=True,
        confidence=0.90,
        reason_code=AssessmentReasonCode.EXACT_MATCH,
        matched_phrase="red",
    )

    # Prior state: 4 practices, 2 successes. New state: 5 practices, 3 successes (3/5 = 60% < 75%)
    result = policy.evaluate_mastery(
        child_id="child-123",
        skill_token="colors.red",
        current_band=MasteryBand.PRACTICING,
        current_practice_count=4,
        current_success_count=2,
        assessment=assessment,
    )

    assert result.is_updated is True
    assert result.new_band == MasteryBand.PRACTICING
    assert result.practice_count == 5
    assert result.success_count == 3
    assert result.explanation_code == "MAINTAINED_BAND"


def test_acquired_band_maintains_acquired(
    policy: RuleBasedMasteryPolicy,
) -> None:
    """ACQUIRED remains ACQUIRED on further practice."""
    assessment = create_assessment(
        status=AssessmentStatus.CORRECT,
        is_correct=True,
        confidence=0.96,
        reason_code=AssessmentReasonCode.EXACT_MATCH,
        matched_phrase="red",
    )

    result = policy.evaluate_mastery(
        child_id="child-123",
        skill_token="colors.red",
        current_band=MasteryBand.ACQUIRED,
        current_practice_count=5,
        current_success_count=4,
        assessment=assessment,
    )

    assert result.is_updated is True
    assert result.previous_band == MasteryBand.ACQUIRED
    assert result.new_band == MasteryBand.ACQUIRED
    assert result.practice_count == 6
    assert result.success_count == 5
    assert result.explanation_code == "MAINTAINED_BAND"
