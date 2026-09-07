"""Unit tests for response plan validation rules (AI-008, SEC-010, ADR-007)."""

import pytest

from app.contracts.device import DisplayState, GestureType
from app.contracts.response import ContentProvenance, PedagogicalAct, ResponsePlan
from app.response.validators import ResponsePlanValidationError, validate_response_plan


@pytest.fixture
def valid_plan() -> ResponsePlan:
    return ResponsePlan(
        plan_id="plan-test-1",
        session_id="sess-1",
        turn_id="turn-1",
        pedagogical_act=PedagogicalAct.PRAISE,
        approved_text="Pintar sekali! Jawabanmu benar.",
        spoken_text="Pintar sekali! Jawabanmu benar.",
        audio_asset_id="audio-asset-praise-01",
        provenance=ContentProvenance(
            curriculum_version="curriculum-v1.0",
            module_id="body_parts",
            activity_id="body_parts_mata",
            template_id="tpl-praise-exact",
        ),
        display=DisplayState.HAPPY,
        gesture=GestureType.CELEBRATE,
        is_escalation=False,
        paraphrase_applied=False,
    )


def test_valid_plan_passes(valid_plan: ResponsePlan) -> None:
    validate_response_plan(valid_plan)


def test_spoken_text_exceeding_word_limit_rejected(valid_plan: ResponsePlan) -> None:
    long_text = "satu " * 26
    # Pydantic field_validator should catch this at model creation
    with pytest.raises(ValueError, match="AI-008 violation"):
        ResponsePlan(
            plan_id="plan-bad-words",
            session_id="sess-1",
            turn_id="turn-1",
            pedagogical_act=PedagogicalAct.PRAISE,
            approved_text="Singkat saja.",
            spoken_text=long_text,
            audio_asset_id="audio-1",
            provenance=valid_plan.provenance,
        )


def test_blank_audio_asset_id_rejected(valid_plan: ResponsePlan) -> None:
    bad_plan = valid_plan.model_copy(update={"audio_asset_id": "   "})
    with pytest.raises(ResponsePlanValidationError, match="audio_asset_id cannot be blank"):
        validate_response_plan(bad_plan)


def test_missing_provenance_rejected(valid_plan: ResponsePlan) -> None:
    bad_prov = ContentProvenance(
        curriculum_version="",
        module_id="body_parts",
        activity_id="act-1",
        template_id="tpl-1",
    )
    bad_plan = valid_plan.model_copy(update={"provenance": bad_prov})
    with pytest.raises(ResponsePlanValidationError, match="FR-011 violation"):
        validate_response_plan(bad_plan)


@pytest.mark.parametrize(
    "forbidden_word",
    ["terapi", "diagnosis", "autisme", "adhd", "depresi", "gangguan"],
)
def test_clinical_words_rejected(valid_plan: ResponsePlan, forbidden_word: str) -> None:
    bad_text = f"Anak ini membutuhkan {forbidden_word} segera."
    bad_plan = valid_plan.model_copy(update={"spoken_text": bad_text})
    with pytest.raises(ResponsePlanValidationError, match="SEC-010 violation"):
        validate_response_plan(bad_plan)


def test_inconsistent_escalation_flag_rejected(valid_plan: ResponsePlan) -> None:
    bad_plan = valid_plan.model_copy(
        update={
            "is_escalation": True,
            "pedagogical_act": PedagogicalAct.PRAISE,
        }
    )
    with pytest.raises(ResponsePlanValidationError, match="Inconsistent plan"):
        validate_response_plan(bad_plan)
