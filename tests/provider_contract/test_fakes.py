"""Tests for provider interfaces, deterministic fakes, failure modes,
and feature flags (AI-001–003, DEV-004).
"""

import pytest

from app.config.settings import Environment, Profile, Settings
from app.contracts.base import CallbackCorrelation
from app.contracts.device import AudioSpec, CodecType
from app.contracts.response import PedagogicalAct
from app.contracts.speech import ASRStatus, TTSSource
from app.contracts.understanding import AssessmentReasonCode, AssessmentStatus
from app.contracts.vision import VisionStatus
from app.providers.exceptions import (
    ProviderMalformedResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.providers.registry import create_provider_registry
from app.response.fakes import FakeParaphraser
from app.speech.fakes import FakeASRProvider, FakeTTSProvider
from app.understanding.fakes import FakeSemanticResolver
from app.vision.fakes import FakeVisionProvider


@pytest.fixture
def correlation() -> CallbackCorrelation:
    return CallbackCorrelation(session_id="sess-sim-001", turn_id="turn-001", state_version=1)


@pytest.fixture
def audio_spec() -> AudioSpec:
    return AudioSpec(codec=CodecType.OPUS, sample_rate=16000, channels=1)


@pytest.mark.asyncio
async def test_fake_asr_provider_modes(
    audio_spec: AudioSpec,
    correlation: CallbackCorrelation,
) -> None:
    """Verify FakeASRProvider success, abstain, timeout, and error modes (AI-002, AI-006)."""
    asr = FakeASRProvider(default_transcript="mata", default_confidence=0.98)

    # 1. Success mode
    res = await asr.transcribe(b"dummy-audio", audio_spec, correlation)
    assert res.status == ASRStatus.SUCCESS
    assert res.transcript == "mata"
    assert res.confidence == 0.98
    assert res.session_id == correlation.session_id
    assert res.turn_id == correlation.turn_id

    # 2. Abstain mode
    asr.set_mode("abstain")
    res_abstain = await asr.transcribe(b"silence-audio", audio_spec, correlation)
    assert res_abstain.status == ASRStatus.ABSTAIN
    assert res_abstain.transcript == ""

    # 3. Timeout mode
    asr.set_mode("timeout")
    with pytest.raises(ProviderTimeoutError, match="exceeded deadline"):
        await asr.transcribe(b"audio", audio_spec, correlation, timeout_s=0.01)

    # 4. Outage mode
    asr.set_mode("error")
    with pytest.raises(ProviderUnavailableError, match="network disconnect"):
        await asr.transcribe(b"audio", audio_spec, correlation)

    # 5. Malformed response mode
    asr.set_mode("malformed")
    with pytest.raises(ProviderMalformedResponseError, match="corrupted payload"):
        await asr.transcribe(b"audio", audio_spec, correlation)


@pytest.mark.asyncio
async def test_fake_tts_provider_modes() -> None:
    """Verify FakeTTSProvider cached and dynamic synthesis modes (ADR-009)."""
    tts = FakeTTSProvider()

    # Cached asset lookup
    cached_res = await tts.synthesize("Coba lihat", audio_asset_id="audio_mata_001")
    assert cached_res.source == TTSSource.CACHED
    assert cached_res.audio_asset_id == "audio_mata_001"

    # Dynamic synthesis
    dyn_res = await tts.synthesize("Halo adik pintar apa kabar")
    assert dyn_res.source == TTSSource.DYNAMIC
    assert dyn_res.duration_ms > 0

    # Failure mode
    tts.set_mode("error")
    with pytest.raises(ProviderUnavailableError, match="engine failure"):
        await tts.synthesize("Halo")


@pytest.mark.asyncio
async def test_fake_semantic_resolver_modes(correlation: CallbackCorrelation) -> None:
    """Verify FakeSemanticResolver deterministic matches and uncertainty invariants.

    Enforces FR-009 and ADR-006 boundaries.
    """
    resolver = FakeSemanticResolver()

    # Exact match
    res_exact = await resolver.resolve_intent("mata", ["mata", "hidung"], correlation)
    assert res_exact.status == AssessmentStatus.CORRECT
    assert res_exact.is_correct is True
    assert res_exact.reason_code == AssessmentReasonCode.EXACT_MATCH
    assert res_exact.session_id == correlation.session_id

    # Substring / semantic match
    res_sub = await resolver.resolve_intent("ini mata saya", ["mata"], correlation)
    assert res_sub.status == AssessmentStatus.CORRECT
    assert res_sub.reason_code == AssessmentReasonCode.SEMANTIC_RESOLVED

    # Mismatch
    res_mismatch = await resolver.resolve_intent("kaki", ["mata"], correlation)
    assert res_mismatch.status == AssessmentStatus.INCORRECT
    assert res_mismatch.is_correct is False

    # Uncertain mode: FR-009 invariant must hold (never marked correct)
    resolver.set_mode("uncertain")
    res_uncertain = await resolver.resolve_intent("emm", ["mata"], correlation)
    assert res_uncertain.status == AssessmentStatus.UNCERTAIN
    assert res_uncertain.is_correct is False


@pytest.mark.asyncio
async def test_fake_paraphraser_modes() -> None:
    """Verify FakeParaphraser 25-word bound and passthrough behavior (AI-008, ADR-007)."""
    paraphraser = FakeParaphraser(mode="passthrough")

    # Passthrough mode
    base = "Bagian tubuh mana untuk melihat?"
    res = await paraphraser.paraphrase(base, PedagogicalAct.PROMPT)
    assert res == base

    # Paraphrase mode with short length
    paraphraser.set_mode("paraphrase")
    res_para = await paraphraser.paraphrase(base, PedagogicalAct.HINT)
    assert len(res_para.split()) <= 25

    # Timeout mode
    paraphraser.set_mode("timeout")
    with pytest.raises(ProviderTimeoutError):
        await paraphraser.paraphrase(base, PedagogicalAct.HINT, timeout_s=0.01)


@pytest.mark.asyncio
async def test_fake_vision_provider_modes(correlation: CallbackCorrelation) -> None:
    """Verify FakeVisionProvider bounding boxes and vocabulary filtering (AI-009, ADR-010)."""
    vision = FakeVisionProvider(default_label="kartu_mata")

    # Success mode
    res = await vision.detect_objects(
        b"frame", allowed_vocabulary=["kartu_mata"], correlation=correlation
    )
    assert res.status == VisionStatus.DETECTED
    assert len(res.detected_objects) == 1
    assert res.detected_objects[0].label == "kartu_mata"
    assert res.session_id == correlation.session_id

    # Filtered vocabulary maps to UNKNOWN
    res_filtered = await vision.detect_objects(
        b"frame", allowed_vocabulary=["kartu_kaki"], correlation=correlation
    )
    assert res_filtered.status == VisionStatus.UNKNOWN

    # Abstain mode
    vision.set_mode("abstain")
    res_abstain = await vision.detect_objects(b"frame", correlation=correlation)
    assert res_abstain.status == VisionStatus.ABSTAIN


def test_provider_registry_feature_flags() -> None:
    """Verify feature flag toggles construct corresponding providers or omit them (DEV-004)."""
    # Profile with optional AI disabled
    settings_no_ai = Settings(
        profile=Profile.TEST,
        env=Environment.TEST,
        semantic_enabled=False,
        llm_paraphrase_enabled=False,
        vision_enabled=False,
    )
    reg_no_ai = create_provider_registry(settings_no_ai)
    assert reg_no_ai.is_semantic_enabled is False
    assert reg_no_ai.is_paraphrase_enabled is False
    assert reg_no_ai.is_vision_enabled is False

    # Profile with optional AI enabled
    settings_with_ai = Settings(
        profile=Profile.LOCAL,
        env=Environment.DEVELOPMENT,
        semantic_enabled=True,
        llm_paraphrase_enabled=True,
        vision_enabled=True,
    )
    reg_with_ai = create_provider_registry(settings_with_ai)
    assert reg_with_ai.is_semantic_enabled is True
    assert reg_with_ai.is_paraphrase_enabled is True
    assert reg_with_ai.is_vision_enabled is True
