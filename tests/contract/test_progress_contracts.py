"""Contract tests for parent progress projections and non-clinical constraints (FR-016, SEC-010)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.progress import ChildProgressDTO, SessionSummaryDTO

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "contracts"


def test_child_progress_valid_fixture():
    """Valid child progress fixture parses cleanly with non-clinical content."""
    with open(FIXTURES_DIR / "child_progress_valid.json", encoding="utf-8") as f:
        data = json.load(f)

    dto = ChildProgressDTO.model_validate(data)
    assert dto.child_id == "child-c9f2"
    assert dto.display_name == "Budi"
    assert len(dto.skills) == 1
    assert dto.skills[0].skill_name == "Pengenalan Anggota Tubuh"
    assert len(dto.recent_sessions) == 1


def test_child_progress_clinical_claim_rejection():
    """SEC-010 invariant: Parent copy containing diagnostic or clinical claims is rejected."""
    with open(FIXTURES_DIR / "child_progress_invalid.json", encoding="utf-8") as f:
        data = json.load(f)

    with pytest.raises(ValidationError, match="SEC-010 violation"):
        ChildProgressDTO.model_validate(data)


def test_session_summary_clinical_terms_rejection():
    """Ensure specific clinical terms (diagnosis, speech delay, terapi) fail validation."""
    for forbidden in [
        "Hasil diagnosis baik",
        "Anak butuh terapi",
        "Terdapat indikasi speech delay",
    ]:
        with pytest.raises(ValidationError, match="SEC-010 violation"):
            SessionSummaryDTO(
                session_id="sess-1",
                duration_minutes=5,
                completed_activities=1,
                parent_tip=forbidden,
            )
