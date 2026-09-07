"""Evaluation metric calculator and test harness for deterministic assessment.

(FR-010, AI-005, OBS-005)
"""

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.contracts.speech import ASRResult, ASRStatus
from app.contracts.understanding import (
    AssessmentResult,
    AssessmentStatus,
)
from app.curriculum.models import AnswerSpec
from app.understanding.deterministic_assessor import DeterministicAssessor


@dataclass(frozen=True)
class AssessmentMetrics:
    """Aggregated evaluation metrics for deterministic understanding evaluation."""

    total_cases: int
    correct_predictions: int
    accuracy: float
    macro_f1: float
    precision_by_class: dict[str, float]
    recall_by_class: dict[str, float]
    f1_by_class: dict[str, float]
    false_incorrect_count: int
    false_incorrect_on_uncertain_count: int
    confusion_matrix: dict[str, dict[str, int]]
    reason_code_counts: dict[str, int]
    coverage_rate: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_labeled_cases(
    cases: list[dict[str, Any]],
    assessor: DeterministicAssessor | None = None,
) -> tuple[AssessmentMetrics, list[dict[str, Any]]]:
    """Run assessor across labeled test cases and compute evaluation metrics.

    Returns:
        tuple containing the calculated AssessmentMetrics and the detailed case results.
    """
    if assessor is None:
        assessor = DeterministicAssessor()

    all_statuses = [
        AssessmentStatus.CORRECT.value,
        AssessmentStatus.INCORRECT.value,
        AssessmentStatus.UNCERTAIN.value,
        AssessmentStatus.NO_RESPONSE.value,
    ]

    confusion_matrix: dict[str, dict[str, int]] = {
        s_true: {s_pred: 0 for s_pred in all_statuses} for s_true in all_statuses
    }
    reason_counts: Counter[str] = Counter()
    case_results: list[dict[str, Any]] = []

    correct_predictions = 0
    false_incorrect_count = 0
    false_incorrect_on_uncertain_count = 0

    for case in cases:
        case_id = case.get("id", "case_unknown")
        target_concept = case["target_concept"]
        expected_status = case["expected_status"]
        expected_reason = case.get("expected_reason_code")

        # Prepare AnswerSpec
        raw_spec = case.get("answer_spec", {})
        if isinstance(raw_spec, list):
            spec = AnswerSpec(exact_matches=raw_spec)
        elif isinstance(raw_spec, dict):
            spec = AnswerSpec(**raw_spec)
        else:
            spec = raw_spec

        # Prepare evidence
        evidence: ASRResult | str
        ev_data = case.get("evidence", {})
        if isinstance(ev_data, str):
            evidence = ev_data
        else:
            status_str = ev_data.get("status", "SUCCESS")
            evidence = ASRResult(
                session_id="eval-sess",
                turn_id="eval-turn",
                state_version=1,
                status=ASRStatus(status_str),
                transcript=ev_data.get("transcript", ""),
                confidence=ev_data.get("confidence", 1.0),
                duration_ms=ev_data.get("duration_ms", 1000),
                latency_ms=ev_data.get("latency_ms", 10.0),
                provider=ev_data.get("provider", "test-asr"),
                model_version=ev_data.get("model_version", "whisper-test-v1"),
            )

        # Run assessment
        result: AssessmentResult = assessor.assess(
            evidence=evidence,
            answer_spec=spec,
            target_concept=target_concept,
        )

        pred_status = result.status.value
        pred_reason = result.reason_code.value
        reason_counts[pred_reason] += 1

        if pred_status in confusion_matrix and expected_status in confusion_matrix:
            confusion_matrix[expected_status][pred_status] += 1

        is_match = (pred_status == expected_status) and (
            expected_reason is None or pred_reason == expected_reason
        )
        if is_match:
            correct_predictions += 1

        # False-incorrect check (child penalization)
        if pred_status == AssessmentStatus.INCORRECT.value:
            if expected_status != AssessmentStatus.INCORRECT.value:
                false_incorrect_count += 1
            # Specifically check if input was uncertain/silence/corrupted
            if expected_status in (
                AssessmentStatus.UNCERTAIN.value,
                AssessmentStatus.NO_RESPONSE.value,
            ):
                false_incorrect_on_uncertain_count += 1

        case_results.append(
            {
                "id": case_id,
                "target_concept": target_concept,
                "expected_status": expected_status,
                "expected_reason_code": expected_reason,
                "predicted_status": pred_status,
                "predicted_reason_code": pred_reason,
                "matched_phrase": result.matched_phrase,
                "confidence": result.confidence,
                "latency_ms": result.evaluation_latency_ms,
                "passed": is_match,
            }
        )

    total_cases = len(cases)
    accuracy = correct_predictions / total_cases if total_cases > 0 else 0.0

    # Compute Precision, Recall, F1 by class
    precision_by_class: dict[str, float] = {}
    recall_by_class: dict[str, float] = {}
    f1_by_class: dict[str, float] = {}

    present_classes = set()
    for case in cases:
        present_classes.add(case["expected_status"])

    f1_sum = 0.0
    for cls in all_statuses:
        tp = confusion_matrix[cls][cls]
        fp = sum(confusion_matrix[other][cls] for other in all_statuses if other != cls)
        fn = sum(confusion_matrix[cls][other] for other in all_statuses if other != cls)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        precision_by_class[cls] = round(prec, 4)
        recall_by_class[cls] = round(rec, 4)
        f1_by_class[cls] = round(f1, 4)

        if cls in present_classes:
            f1_sum += f1

    macro_f1 = f1_sum / len(present_classes) if present_classes else 0.0

    # Coverage: proportion not classified as UNCERTAIN
    non_uncertain_count = sum(
        1 for r in case_results if r["predicted_status"] != AssessmentStatus.UNCERTAIN.value
    )
    coverage_rate = non_uncertain_count / total_cases if total_cases > 0 else 0.0

    metrics = AssessmentMetrics(
        total_cases=total_cases,
        correct_predictions=correct_predictions,
        accuracy=round(accuracy, 4),
        macro_f1=round(macro_f1, 4),
        precision_by_class=precision_by_class,
        recall_by_class=recall_by_class,
        f1_by_class=f1_by_class,
        false_incorrect_count=false_incorrect_count,
        false_incorrect_on_uncertain_count=false_incorrect_on_uncertain_count,
        confusion_matrix=confusion_matrix,
        reason_code_counts=dict(reason_counts),
        coverage_rate=round(coverage_rate, 4),
    )

    return metrics, case_results


def load_and_evaluate_fixtures(
    fixture_path: Path | str,
    assessor: DeterministicAssessor | None = None,
) -> tuple[AssessmentMetrics, list[dict[str, Any]]]:
    """Load JSON fixture file and run deterministic evaluation."""
    path = Path(fixture_path)
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)
    return evaluate_labeled_cases(cases, assessor=assessor)
