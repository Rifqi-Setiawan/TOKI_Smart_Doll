"""Unit tests for curriculum domain models, contracts, and schema validation (FR-007)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.curriculum.models import (
    ActivityAudioReferences,
    ActivityDifficulty,
    AnswerSpec,
    CurriculumActivity,
    CurriculumManifest,
    ReviewStatus,
)


def test_activity_schema_round_trip_and_validation() -> None:
    """Acceptance Criterion 1: One complete reviewed activity validates and round-trips."""
    answer_spec = AnswerSpec(
        exact_matches=["mata"],
        synonyms=["kedua mata", "netra"],
        phonetic_variations=["matak", "matah"],
        case_sensitive=False,
    )
    audio_refs = ActivityAudioReferences(
        prompt_audio_id="audio_mata_prompt_001",
        fallback_audio_id="audio_mata_fallback_001",
        hint_audio_ids=["audio_hint_mata_001", "audio_hint_mata_002"],
    )
    activity = CurriculumActivity(
        activity_token="body_parts_mata",
        module="body_parts",
        skill_token="body_parts",
        difficulty=ActivityDifficulty.BEGINNER,
        prompt_text="Coba sebutkan, bagian tubuh apa yang kita gunakan untuk melihat?",
        answer_spec=answer_spec,
        hints=[
            "Posisinya ada di wajah kita!",
            "Ada dua, kanan dan kiri, untuk melihat pemandangan indah.",
        ],
        retry_prompt="Ayo diingat lagi, yang kita pakai untuk melihat namanya apa ya?",
        audio_refs=audio_refs,
        review_notes="PAUD speech-stimulation certified.",
    )

    # Serialize to JSON and deserialize back
    dumped = activity.model_dump()
    reconstructed = CurriculumActivity.model_validate(dumped)

    assert reconstructed.activity_token == "body_parts_mata"
    assert reconstructed.difficulty == ActivityDifficulty.BEGINNER
    assert reconstructed.answer_spec.exact_matches == ["mata"]
    assert "kedua mata" in reconstructed.answer_spec.synonyms
    assert reconstructed.audio_refs.fallback_audio_id == "audio_mata_fallback_001"
    assert len(reconstructed.hints) == 2


def test_answer_spec_token_expansion_and_validation() -> None:
    """AnswerSpec expands all accepted tokens and validates non-empty entries."""
    spec = AnswerSpec(
        exact_matches=["Telinga"],
        synonyms=["kuping"],
        phonetic_variations=["telingah"],
        case_sensitive=False,
    )
    tokens = spec.all_accepted_tokens()
    assert "telinga" in tokens
    assert "kuping" in tokens
    assert "telingah" in tokens

    # Validation: empty exact_matches rejected
    with pytest.raises(ValidationError):
        AnswerSpec(exact_matches=[])


def test_curriculum_manifest_loads_pilot_pack() -> None:
    """Verify that the official reviewed pilot fixture validates cleanly against schema."""
    fixture_path = (
        Path(__file__).parent.parent.parent
        / "fixtures"
        / "curriculum"
        / "pilot_body_parts_pack.json"
    )
    assert fixture_path.exists(), f"Missing fixture at {fixture_path}"

    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)

    manifest = CurriculumManifest.model_validate(data)
    assert manifest.version_token == "curriculum-pilot-v1.0"
    assert manifest.status == ReviewStatus.APPROVED
    assert manifest.reviewed_by == "dr_susanti_sp_a_paud_expert@toki.id"
    assert len(manifest.activities) == 4

    tokens = [act.activity_token for act in manifest.activities]
    assert "body_parts_mata" in tokens
    assert "body_parts_hidung" in tokens
    assert "body_parts_telinga" in tokens
    assert "body_parts_mulut" in tokens
