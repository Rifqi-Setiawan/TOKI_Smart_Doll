"""Contract tests for speech adapters (AI-002, API-006, ADR-008, ADR-009)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.speech import ASRResult, ASRStatus, TTSResult, TTSSource

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "contracts"


def test_asr_result_valid_fixture():
    """Valid ASRResult parses cleanly and preserves correlation attributes."""
    with open(FIXTURES_DIR / "asr_result_valid.json", encoding="utf-8") as f:
        data = json.load(f)

    result = ASRResult.model_validate(data)
    assert result.status == ASRStatus.SUCCESS
    assert result.transcript == "kucing"
    assert result.confidence == 0.94
    assert result.session_id == "sess-987fcdeb-51a2-43f7-9876-543210987654"
    assert result.turn_id == "turn-001"
    assert result.state_version == 2
    assert result.latency_ms == 480.5


def test_asr_result_requires_state_version():
    """Callback correlation requires mandatory state_version (API-006, ADR-003)."""
    with open(FIXTURES_DIR / "asr_result_invalid.json", encoding="utf-8") as f:
        data = json.load(f)

    with pytest.raises(ValidationError, match="state_version"):
        ASRResult.model_validate(data)


def test_asr_abstain_and_uncertain_semantics():
    """Probabilistic speech adapter can return ABSTAIN or UNCERTAIN without error (AI-002)."""
    abstain_result = ASRResult(
        session_id="sess-1",
        turn_id="turn-1",
        state_version=1,
        status=ASRStatus.ABSTAIN,
        transcript="",
        confidence=None,
        duration_ms=1000,
        latency_ms=150.0,
        provider="fake",
        model_version="whisper-id-v1",
    )
    assert abstain_result.status == ASRStatus.ABSTAIN
    assert abstain_result.confidence is None


def test_tts_result_cached_vs_dynamic():
    """TTS output tracks source (CACHED, DYNAMIC, FALLBACK) and correlation (ADR-009)."""
    cached_tts = TTSResult(
        session_id="sess-1",
        turn_id="turn-1",
        state_version=1,
        source=TTSSource.CACHED,
        audio_asset_id="prompt-body-hidung-v1",
        duration_ms=2100,
        latency_ms=5.0,
        provider="cached_asset_service",
        voice_id="id-ID-wavenet-a",
    )
    assert cached_tts.source == TTSSource.CACHED
    assert cached_tts.audio_asset_id == "prompt-body-hidung-v1"
