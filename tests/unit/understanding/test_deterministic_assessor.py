"""Unit and invariant tests for DeterministicAssessor (FR-008, FR-009, ADR-006)."""

import pytest

from app.contracts.speech import ASRResult, ASRStatus
from app.contracts.understanding import (
    AssessmentReasonCode,
    AssessmentStatus,
)
from app.curriculum.models import AnswerSpec
from app.understanding.deterministic_assessor import DeterministicAssessor


@pytest.fixture
def assessor() -> DeterministicAssessor:
    return DeterministicAssessor(min_confidence=0.65, policy_version="RULE-ASSESS-1.0")


@pytest.fixture
def body_part_spec() -> AnswerSpec:
    return AnswerSpec(
        exact_matches=["mata"],
        synonyms=["netra"],
        phonetic_variations=["matak", "matah"],
    )


def test_exact_match(assessor: DeterministicAssessor, body_part_spec: AnswerSpec) -> None:
    res = assessor.assess(
        evidence="mata",
        answer_spec=body_part_spec,
        target_concept="mata",
    )
    assert res.status == AssessmentStatus.CORRECT
    assert res.is_correct is True
    assert res.reason_code == AssessmentReasonCode.EXACT_MATCH
    assert res.confidence == 1.0
    assert res.policy_version == "RULE-ASSESS-1.0"
    assert res.evaluation_latency_ms >= 0.0


def test_exact_match_with_fillers_and_casing(
    assessor: DeterministicAssessor, body_part_spec: AnswerSpec
) -> None:
    res = assessor.assess(
        evidence="Eh anu, MATA!",
        answer_spec=body_part_spec,
        target_concept="mata",
    )
    assert res.status == AssessmentStatus.CORRECT
    assert res.is_correct is True
    assert res.reason_code == AssessmentReasonCode.EXACT_MATCH


def test_synonym_match(assessor: DeterministicAssessor, body_part_spec: AnswerSpec) -> None:
    res = assessor.assess(
        evidence="netra",
        answer_spec=body_part_spec,
        target_concept="mata",
    )
    assert res.status == AssessmentStatus.CORRECT
    assert res.is_correct is True
    assert res.reason_code == AssessmentReasonCode.SYNONYM_MATCH
    assert res.confidence == 0.95


def test_phonetic_variation_match(
    assessor: DeterministicAssessor, body_part_spec: AnswerSpec
) -> None:
    res = assessor.assess(
        evidence="matak",
        answer_spec=body_part_spec,
        target_concept="mata",
    )
    assert res.status == AssessmentStatus.CORRECT
    assert res.is_correct is True
    assert res.reason_code == AssessmentReasonCode.PHONETIC_MATCH
    assert res.confidence == 0.90


def test_fuzzy_normalized_match(assessor: DeterministicAssessor) -> None:
    spec = AnswerSpec(exact_matches=["telinga"])
    res = assessor.assess(
        evidence="teliga",
        answer_spec=spec,
        target_concept="telinga",
    )
    assert res.status == AssessmentStatus.CORRECT
    assert res.is_correct is True
    assert res.reason_code == AssessmentReasonCode.NORMALIZED_MATCH
    assert res.confidence == 0.85


def test_low_confidence_guard_invariant(
    assessor: DeterministicAssessor, body_part_spec: AnswerSpec
) -> None:
    """FR-009 Invariant: Low confidence is system uncertainty, never child incorrectness."""
    evidence = ASRResult(
        session_id="s1",
        turn_id="t1",
        state_version=1,
        status=ASRStatus.SUCCESS,
        transcript="mata",
        confidence=0.55,  # Below 0.65 threshold
        duration_ms=1000,
        latency_ms=10.0,
        provider="fake",
        model_version="whisper-tiny",
    )
    res = assessor.assess(
        evidence=evidence,
        answer_spec=body_part_spec,
        target_concept="mata",
    )
    assert res.status == AssessmentStatus.UNCERTAIN
    assert res.is_correct is False
    assert res.reason_code == AssessmentReasonCode.LOW_CONFIDENCE
    assert res.confidence == 0.55


def test_silence_guard_invariant(
    assessor: DeterministicAssessor, body_part_spec: AnswerSpec
) -> None:
    """FR-009 Invariant: Silence or empty utterance must be NO_RESPONSE, never INCORRECT."""
    for empty_val in ["", "   ", "...", "eh", "em anu"]:
        res = assessor.assess(
            evidence=empty_val,
            answer_spec=body_part_spec,
            target_concept="mata",
        )
        assert res.status == AssessmentStatus.NO_RESPONSE
        assert res.is_correct is False
        assert res.reason_code == AssessmentReasonCode.NO_SPEECH_DETECTED


def test_asr_no_speech_status_invariant(
    assessor: DeterministicAssessor, body_part_spec: AnswerSpec
) -> None:
    evidence = ASRResult(
        session_id="s1",
        turn_id="t1",
        state_version=1,
        status=ASRStatus.NO_SPEECH,
        transcript="",
        confidence=1.0,
        duration_ms=1000,
        latency_ms=10.0,
        provider="fake",
        model_version="whisper-tiny",
    )
    res = assessor.assess(
        evidence=evidence,
        answer_spec=body_part_spec,
        target_concept="mata",
    )
    assert res.status == AssessmentStatus.NO_RESPONSE
    assert res.is_correct is False
    assert res.reason_code == AssessmentReasonCode.NO_SPEECH_DETECTED


def test_audio_corrupted_error_invariant(
    assessor: DeterministicAssessor, body_part_spec: AnswerSpec
) -> None:
    for err_status in [ASRStatus.ERROR, ASRStatus.TIMEOUT]:
        evidence = ASRResult(
            session_id="s1",
            turn_id="t1",
            state_version=1,
            status=err_status,
            transcript="",
            confidence=0.0,
            duration_ms=1000,
            latency_ms=10.0,
            provider="fake",
            model_version="whisper-tiny",
        )
        res = assessor.assess(
            evidence=evidence,
            answer_spec=body_part_spec,
            target_concept="mata",
        )
        assert res.status == AssessmentStatus.UNCERTAIN
        assert res.is_correct is False
        assert res.reason_code == AssessmentReasonCode.AUDIO_CORRUPTED


def test_explicit_mismatch(assessor: DeterministicAssessor, body_part_spec: AnswerSpec) -> None:
    res = assessor.assess(
        evidence="kaki",
        answer_spec=body_part_spec,
        target_concept="mata",
    )
    assert res.status == AssessmentStatus.INCORRECT
    assert res.is_correct is False
    assert res.reason_code == AssessmentReasonCode.EXPLICIT_MISMATCH


@pytest.mark.parametrize(
    "bad_confidence,bad_transcript,bad_status",
    [
        (0.2, "mata", ASRStatus.SUCCESS),
        (0.0, "", ASRStatus.ERROR),
        (0.0, "", ASRStatus.TIMEOUT),
        (1.0, "", ASRStatus.NO_SPEECH),
        (0.64, "kaki", ASRStatus.SUCCESS),
        (0.1, "something random", ASRStatus.SUCCESS),
    ],
)
def test_zero_false_incorrect_property_invariant(
    assessor: DeterministicAssessor,
    body_part_spec: AnswerSpec,
    bad_confidence: float,
    bad_transcript: str,
    bad_status: ASRStatus,
) -> None:
    """Rigorous property test: low confidence or malformed audio cannot be INCORRECT."""
    evidence = ASRResult(
        session_id="s_prop",
        turn_id="t_prop",
        state_version=1,
        status=bad_status,
        transcript=bad_transcript,
        confidence=bad_confidence,
        duration_ms=1000,
        latency_ms=10.0,
        provider="fake",
        model_version="whisper-tiny",
    )
    res = assessor.assess(
        evidence=evidence,
        answer_spec=body_part_spec,
        target_concept="mata",
    )
    assert res.status != AssessmentStatus.INCORRECT
    assert res.is_correct is False
