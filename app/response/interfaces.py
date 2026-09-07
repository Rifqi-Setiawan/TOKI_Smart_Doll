"""Vendor-neutral interfaces for bounded paraphrasing
and response planning (AI-001, AI-008, ADR-007).
"""

from abc import ABC, abstractmethod

from app.contracts.response import PedagogicalAct


class Paraphraser(ABC):
    """Abstract interface for bounded natural language paraphrasing (ADR-007, AI-008)."""

    @abstractmethod
    async def paraphrase(
        self,
        baseline_text: str,
        pedagogical_act: PedagogicalAct,
        timeout_s: float | None = None,
    ) -> str:
        """Paraphrase approved baseline text for variety while strictly preserving meaning.

        Must never exceed 25 spoken words for children 4-8 (AI-008).
        """
        pass
