"""Vendor-neutral interfaces for bounded answer understanding
and semantic resolution (AI-001, ADR-006).
"""

from abc import ABC, abstractmethod

from app.contracts.base import CallbackCorrelation
from app.contracts.understanding import AssessmentResult


class SemanticResolver(ABC):
    """Abstract interface for bounded pedagogical answer assessment (ADR-004, ADR-006)."""

    @abstractmethod
    async def resolve_intent(
        self,
        transcript: str,
        expected_answers: list[str],
        correlation: CallbackCorrelation | None = None,
        timeout_s: float | None = None,
    ) -> AssessmentResult:
        """Evaluate child transcript against approved expected answers.

        Returns AssessmentResult with status (CORRECT, INCORRECT, UNCERTAIN, ABSTAIN).
        In accordance with FR-009, uncertain answers must never be marked correct.
        """
        pass
