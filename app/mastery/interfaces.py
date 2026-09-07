"""Abstract interface for replaceable mastery evaluation policies (ADR-011)."""

from abc import ABC, abstractmethod

from app.contracts.understanding import AssessmentResult
from app.mastery.models import MasteryBand, MasteryEvaluationResult


class MasteryPolicy(ABC):
    """Abstract interface for skill mastery evaluation algorithms."""

    @abstractmethod
    def evaluate_mastery(
        self,
        child_id: str,
        skill_token: str,
        current_band: MasteryBand,
        current_practice_count: int,
        current_success_count: int,
        assessment: AssessmentResult,
    ) -> MasteryEvaluationResult:
        """Compute the updated mastery band and explanation code for an attempt."""
        pass
