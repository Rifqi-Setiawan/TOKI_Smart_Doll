"""Unit tests for the understanding evaluation metric calculator (FR-010, AI-005)."""

from pathlib import Path

from app.understanding.evaluator import (
    evaluate_labeled_cases,
    load_and_evaluate_fixtures,
)


def test_evaluator_on_in_memory_cases() -> None:
    cases = [
        {
            "id": "c1",
            "target_concept": "mata",
            "answer_spec": {"exact_matches": ["mata"]},
            "evidence": {"transcript": "mata", "confidence": 0.95},
            "expected_status": "CORRECT",
            "expected_reason_code": "EXACT_MATCH",
        },
        {
            "id": "c2",
            "target_concept": "mata",
            "answer_spec": {"exact_matches": ["mata"]},
            "evidence": {"transcript": "kaki", "confidence": 0.90},
            "expected_status": "INCORRECT",
            "expected_reason_code": "EXPLICIT_MISMATCH",
        },
        {
            "id": "c3",
            "target_concept": "mata",
            "answer_spec": {"exact_matches": ["mata"]},
            "evidence": {"transcript": "mata", "confidence": 0.40},
            "expected_status": "UNCERTAIN",
            "expected_reason_code": "LOW_CONFIDENCE",
        },
        {
            "id": "c4",
            "target_concept": "mata",
            "answer_spec": {"exact_matches": ["mata"]},
            "evidence": {"transcript": "", "confidence": 1.0},
            "expected_status": "NO_RESPONSE",
            "expected_reason_code": "NO_SPEECH_DETECTED",
        },
    ]

    metrics, results = evaluate_labeled_cases(cases)

    assert metrics.total_cases == 4
    assert metrics.correct_predictions == 4
    assert metrics.accuracy == 1.0
    assert metrics.macro_f1 == 1.0
    assert metrics.false_incorrect_count == 0
    assert metrics.false_incorrect_on_uncertain_count == 0
    assert len(results) == 4
    for r in results:
        assert r["passed"] is True


def test_evaluator_on_frozen_fixture() -> None:
    fixture_path = (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "understanding"
        / "labeled_assessment_cases.json"
    )
    assert fixture_path.exists(), f"Fixture file missing: {fixture_path}"

    metrics, results = load_and_evaluate_fixtures(fixture_path)

    # All 20 frozen test cases must pass completely
    assert metrics.total_cases == 20
    assert metrics.correct_predictions == 20
    assert metrics.accuracy == 1.0
    assert metrics.macro_f1 == 1.0
    assert metrics.false_incorrect_count == 0
    assert metrics.false_incorrect_on_uncertain_count == 0

    # Ensure all 4 pedagogical outcome classes are covered
    assert "CORRECT" in metrics.precision_by_class
    assert "INCORRECT" in metrics.precision_by_class
    assert "UNCERTAIN" in metrics.precision_by_class
    assert "NO_RESPONSE" in metrics.precision_by_class

    # Ensure confusion matrix is populated
    assert metrics.confusion_matrix["CORRECT"]["CORRECT"] > 0
    assert metrics.confusion_matrix["INCORRECT"]["INCORRECT"] > 0
    assert metrics.confusion_matrix["UNCERTAIN"]["UNCERTAIN"] > 0
    assert metrics.confusion_matrix["NO_RESPONSE"]["NO_RESPONSE"] > 0

    # Ensure zero off-diagonal predictions for low confidence/uncertain
    assert metrics.confusion_matrix["UNCERTAIN"]["INCORRECT"] == 0
    assert metrics.confusion_matrix["NO_RESPONSE"]["INCORRECT"] == 0
