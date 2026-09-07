"""Speech adapter module containing neutral interfaces and deterministic fakes."""

from app.speech.fakes import FakeASRProvider, FakeTTSProvider
from app.speech.interfaces import ASRProvider, TTSProvider

__all__ = [
    "ASRProvider",
    "FakeASRProvider",
    "FakeTTSProvider",
    "TTSProvider",
]
