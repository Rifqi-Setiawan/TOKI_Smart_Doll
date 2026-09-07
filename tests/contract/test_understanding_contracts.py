"""Contract tests for answer assessment and understanding (FR-008, FR-009, ADR-006)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.understanding import (
    AssessmentReasonCode,
    AssessmentResult,
    AssessmentStatus,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "contracts"


def test_assessment_result_valid_fixture():
    """Valid assessment fixture parses cleanly."""
    with open(FIXTURES_DIR / "assessment_result_valid.json", encoding="utf-8") as f:
        data = json.load(f)

    result = AssessmentResult.model_validate(data)
    assert result.status == AssessmentStatus.CORRECT
    assert result.is_correct is True
    assert result.target_concept == "hewan_kucing"
    assert result.reason_code == AssessmentReasonCode.EXACT_MATCH
    assert result.session_id == "sess-987fcdeb-51a2-43f7-9876-543210987654"


def test_assessment_fr009_uncertainty_not_incorrect():
    """FR-009 invariant: UNCERTAIN cannot count as child correctness
    and must not be marked correct.
    """
    with open(FIXTURES_DIR / "assessment_result_invalid.json", encoding="utf-8") as f:
        data = json.load(f)

    with pytest.raises(ValidationError, match="FR-009 violation"):
        AssessmentResult.model_validate(data)


def test_assessment_status_consistency():
    """Inconsistent status and is_correct flags fail validation."""
    with pytest.raises(ValidationError, match="Inconsistent assessment"):
        AssessmentResult(
            session_id="sess-1",
            turn_id="turn-1",
            state_version=1,
            status=AssessmentStatus.CORRECT,
            target_concept="apel",
            is_correct=False,
            confidence=0.9,
            reason_code=AssessmentReasonCode.EXACT_MATCH,
            evaluation_latency_ms=5.0,
        )
