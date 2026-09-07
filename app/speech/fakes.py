"""Deterministic speech fakes for offline tests and competition demo twin (DEV-004, ADR-014)."""

import asyncio
from typing import Literal

from app.contracts.base import CallbackCorrelation
from app.contracts.device import AudioSpec
from app.contracts.speech import ASRResult, ASRStatus, TTSResult, TTSSource
from app.providers.exceptions import (
    ProviderMalformedResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.speech.interfaces import ASRProvider, TTSProvider

ASRMode = Literal["success", "abstain", "timeout", "malformed", "error"]
TTSMode = Literal["success", "cached_only", "dynamic_only", "timeout", "error"]


class FakeASRProvider(ASRProvider):
    """Deterministic, configurable fake ASR provider for testing and offline twin."""

    def __init__(
        self,
        default_transcript: str = "mata",
        default_confidence: float = 0.95,
        latency_ms: float = 120.0,
        mode: ASRMode = "success",
        model_version: str = "fake-whisper-id-v1",
    ) -> None:
        self.default_transcript = default_transcript
        self.default_confidence = default_confidence
        self.latency_ms = latency_ms
        self.mode: ASRMode = mode
        self.model_version = model_version
        self.call_count: int = 0
        self.last_audio_spec: AudioSpec | None = None

    def set_mode(self, mode: ASRMode) -> None:
        """Switch simulation mode for test scenarios."""
        self.mode = mode

    async def transcribe(
        self,
        audio_bytes: bytes,
        audio_spec: AudioSpec,
        correlation: CallbackCorrelation | None = None,
        timeout_s: float | None = None,
    ) -> ASRResult:
        self.call_count += 1
        self.last_audio_spec = audio_spec

        session_id = correlation.session_id if correlation else "sess-default-fake"
        turn_id = correlation.turn_id if correlation else "turn-001"
        state_version = correlation.state_version if correlation else 1

        # Simulate timeout failure mode (AI-006)
        if self.mode == "timeout":
            if timeout_s is not None and timeout_s > 0:
                await asyncio.sleep(timeout_s + 0.05)
            raise ProviderTimeoutError(
                f"ASR transcription exceeded deadline of {timeout_s}s",
                provider_name="fake_asr",
            )

        # Simulate provider outage
        if self.mode == "error":
            raise ProviderUnavailableError(
                "Simulated ASR provider network disconnect",
                provider_name="fake_asr",
            )

        # Simulate malformed response
        if self.mode == "malformed":
            raise ProviderMalformedResponseError(
                "Simulated corrupted payload from ASR provider",
                provider_name="fake_asr",
            )

        # Simulate intentional abstention on low quality/silence (AI-002)
        if self.mode == "abstain":
            return ASRResult(
                session_id=session_id,
                turn_id=turn_id,
                state_version=state_version,
                status=ASRStatus.ABSTAIN,
                transcript="",
                confidence=0.0,
                duration_ms=500,
                latency_ms=self.latency_ms,
                provider="fake",
                model_version=self.model_version,
            )

        # Default: deterministic success
        duration_ms = max(100, int(len(audio_bytes) * 0.1))
        return ASRResult(
            session_id=session_id,
            turn_id=turn_id,
            state_version=state_version,
            status=ASRStatus.SUCCESS,
            transcript=self.default_transcript,
            confidence=self.default_confidence,
            duration_ms=duration_ms,
            latency_ms=self.latency_ms,
            provider="fake",
            model_version=self.model_version,
        )


class FakeTTSProvider(TTSProvider):
    """Deterministic, configurable fake TTS provider supporting cached and dynamic modes."""

    def __init__(
        self,
        mode: TTSMode = "success",
        default_asset_id: str = "audio_asset_cached_001",
        latency_ms: float = 80.0,
    ) -> None:
        self.mode: TTSMode = mode
        self.default_asset_id = default_asset_id
        self.latency_ms = latency_ms
        self.call_count: int = 0

    def set_mode(self, mode: TTSMode) -> None:
        """Switch simulation mode."""
        self.mode = mode

    async def synthesize(
        self,
        text: str,
        audio_asset_id: str | None = None,
        timeout_s: float | None = None,
        correlation: CallbackCorrelation | None = None,
    ) -> TTSResult:
        self.call_count += 1

        session_id = correlation.session_id if correlation else "sess-default-fake"
        turn_id = correlation.turn_id if correlation else "turn-001"
        state_version = correlation.state_version if correlation else 1

        if self.mode == "timeout":
            if timeout_s is not None and timeout_s > 0:
                await asyncio.sleep(timeout_s + 0.05)
            raise ProviderTimeoutError(
                f"TTS synthesis exceeded deadline of {timeout_s}s",
                provider_name="fake_tts",
            )

        if self.mode == "error":
            raise ProviderUnavailableError(
                "Simulated TTS provider engine failure",
                provider_name="fake_tts",
            )

        # If cached asset ID is specified or mode is cached_only, return CACHED
        if audio_asset_id is not None or self.mode == "cached_only":
            return TTSResult(
                session_id=session_id,
                turn_id=turn_id,
                state_version=state_version,
                source=TTSSource.CACHED,
                audio_asset_id=audio_asset_id or self.default_asset_id,
                duration_ms=1800,
                latency_ms=10.0,
                provider="fake_tts",
                voice_id="id-id-wavenet-a",
            )

        # Dynamic synthesis fallback
        word_count = len(text.split())
        estimated_duration = max(800, word_count * 250)
        return TTSResult(
            session_id=session_id,
            turn_id=turn_id,
            state_version=state_version,
            source=TTSSource.DYNAMIC,
            audio_asset_id=None,
            duration_ms=estimated_duration,
            latency_ms=self.latency_ms,
            provider="fake_tts",
            voice_id="id-id-wavenet-a",
        )
