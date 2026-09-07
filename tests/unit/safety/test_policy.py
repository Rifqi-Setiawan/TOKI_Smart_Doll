"""Unit tests for safety policy evaluator and trigger detection (SEC-005, SEC-006, SEC-009)."""

import pytest

from app.contracts.device import DeviceEvent, EventType
from app.safety.catalog import SafetyCategory
from app.safety.policy import SafetyPolicyEvaluator


@pytest.fixture
def evaluator() -> SafetyPolicyEvaluator:
    return SafetyPolicyEvaluator()


def test_benign_child_utterances(evaluator: SafetyPolicyEvaluator) -> None:
    for text in ["mata", "ini telinga toki", "halo toki", "hidung", "apa kabar"]:
        res = evaluator.evaluate_text(text)
        assert res.is_safe is True
        assert res.category is None
        assert res.canned_response is None


@pytest.mark.parametrize(
    "phrase,expected_category",
    [
        ("aduh sakit toki", SafetyCategory.DANGER),
        ("ada darah", SafetyCategory.DANGER),
        ("awas api", SafetyCategory.DANGER),
        ("ada pisau tajam", SafetyCategory.DANGER),
        ("tolong sakit", SafetyCategory.DANGER),
        ("aku takut seram", SafetyCategory.DISTRESS),
        ("mama tolong", SafetyCategory.DISTRESS),
        ("aku nangis", SafetyCategory.DISTRESS),
        ("stop main", SafetyCategory.EXPLICIT_STOP),
        ("berhenti dulu", SafetyCategory.EXPLICIT_STOP),
        ("aku gak mau lagi", SafetyCategory.EXPLICIT_STOP),
        ("jangan pukul", SafetyCategory.INAPPROPRIATE),
        ("mau tembak", SafetyCategory.INAPPROPRIATE),
    ],
)
def test_safety_triggers_detected(
    evaluator: SafetyPolicyEvaluator, phrase: str, expected_category: SafetyCategory
) -> None:
    res = evaluator.evaluate_text(phrase)
    assert res.is_safe is False
    assert res.category == expected_category
    assert res.canned_response is not None
    assert res.canned_response.approved_text
    assert res.canned_response.audio_asset_id


def test_button_pressed_event_triggers_explicit_stop(evaluator: SafetyPolicyEvaluator) -> None:
    """Hardware button press acts as physical guardian/child stop action (SEC-009, FR-022)."""
    event = DeviceEvent(
        event_type=EventType.BUTTON_PRESSED,
        button_id="emergency_stop",
        metadata={"press_type": "long_press"},
    )
    res = evaluator.evaluate_event(event)
    assert res.is_safe is False
    assert res.category == SafetyCategory.EXPLICIT_STOP
    assert res.canned_response is not None
    assert res.canned_response.requires_session_stop is True


def test_other_hardware_events_are_safe(evaluator: SafetyPolicyEvaluator) -> None:
    for evt_type in [EventType.AUDIO_START, EventType.AUDIO_END, EventType.WAKE_WORD_DETECTED]:
        event = DeviceEvent(event_type=evt_type)
        res = evaluator.evaluate_event(event)
        assert res.is_safe is True
