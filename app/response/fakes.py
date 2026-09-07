"""Deterministic paraphraser fakes for offline tests and evaluation (AI-008, DEV-004)."""

import asyncio
from typing import Literal

from app.contracts.response import PedagogicalAct
from app.providers.exceptions import (
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.response.interfaces import Paraphraser

ParaphraseMode = Literal["passthrough", "paraphrase", "timeout", "error", "oversized"]


class FakeParaphraser(Paraphraser):
    """Deterministic paraphraser adhering to the 25-word child limit (AI-008)."""

    def __init__(
        self,
        mode: ParaphraseMode = "passthrough",
    ) -> None:
        self.mode: ParaphraseMode = mode
        self.call_count: int = 0

    def set_mode(self, mode: ParaphraseMode) -> None:
        """Switch simulation mode."""
        self.mode = mode

    async def paraphrase(
        self,
        baseline_text: str,
        pedagogical_act: PedagogicalAct,
        timeout_s: float | None = None,
    ) -> str:
        self.call_count += 1

        if self.mode == "timeout":
            if timeout_s is not None and timeout_s > 0:
                await asyncio.sleep(timeout_s + 0.05)
            raise ProviderTimeoutError(
                f"Paraphraser exceeded deadline of {timeout_s}s",
                provider_name="fake_paraphraser",
            )

        if self.mode == "error":
            raise ProviderUnavailableError(
                "Simulated paraphraser failure",
                provider_name="fake_paraphraser",
            )

        if self.mode == "oversized":
            # For testing downstream contract validator rejection (> 25 words)
            return (
                "Ini adalah respon yang sengaja dibuat sangat panjang sekali agar melebihi "
                "batas maksimal dua puluh lima kata yang telah ditentukan dalam aturan keselamatan "
                "anak usia dini untuk menguji penolakan sistem."
            )

        if self.mode == "paraphrase":
            if pedagogical_act == PedagogicalAct.PRAISE:
                return f"Hebat sekali! {baseline_text}"
            if pedagogical_act == PedagogicalAct.HINT:
                return f"Coba ingat-ingat lagi yuk! {baseline_text}"
            return f"Ayo, {baseline_text}"

        # Default: passthrough approved template unchanged
        return baseline_text
