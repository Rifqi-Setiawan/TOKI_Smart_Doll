"""Vendor-neutral interfaces for speech recognition
and synthesis (AI-001, AI-002, ADR-008, ADR-009).
"""

from abc import ABC, abstractmethod

from app.contracts.base import CallbackCorrelation
from app.contracts.device import AudioSpec
from app.contracts.speech import ASRResult, TTSResult


class ASRProvider(ABC):
    """Abstract vendor-neutral interface for Automatic Speech Recognition (AI-001, ADR-008)."""

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        audio_spec: AudioSpec,
        correlation: CallbackCorrelation | None = None,
        timeout_s: float | None = None,
    ) -> ASRResult:
        """Transcribe Indonesian audio bytes into a versioned ASRResult.

        Must return normalized typed contract with status, confidence, latency, and
        abstain semantics. SDK errors must not escape; raise ProviderError on failure.
        """
        pass


class TTSProvider(ABC):
    """Abstract vendor-neutral interface for Text-To-Speech audio rendering (AI-001, ADR-009)."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        audio_asset_id: str | None = None,
        timeout_s: float | None = None,
        correlation: CallbackCorrelation | None = None,
    ) -> TTSResult:
        """Synthesize spoken text or locate cached audio asset.

        Prefers cached audio assets where available; dynamic generation must respect timeout.
        """
        pass
