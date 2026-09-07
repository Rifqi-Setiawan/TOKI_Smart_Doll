"""Contract tests for response planning and provenance (FR-011, ADR-007, AI-008)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.response import (
    PedagogicalAct,
    ResponsePlan,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "contracts"


def test_response_plan_valid_fixture():
    """Valid response plan fixture parses cleanly with curriculum provenance."""
    with open(FIXTURES_DIR / "response_plan_valid.json", encoding="utf-8") as f:
        data = json.load(f)

    plan = ResponsePlan.model_validate(data)
    assert plan.pedagogical_act == PedagogicalAct.PRAISE
    assert plan.provenance.module_id == "animals"
    assert plan.provenance.template_id == "tpl_praise_correct"
    assert plan.audio_asset_id == "praise-kucing-01"


def test_response_plan_max_word_count_limit():
    """AI-008 invariant: Responses must not exceed 25 spoken words to avoid cognitive overload."""
    with open(FIXTURES_DIR / "response_plan_invalid.json", encoding="utf-8") as f:
        data = json.load(f)

    with pytest.raises(ValidationError, match="AI-008 violation"):
        ResponsePlan.model_validate(data)
