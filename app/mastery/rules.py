"""Transparent, versioned rule-based skill mastery policy (FR-014, FR-015, ADR-011)."""

from app.contracts.understanding import AssessmentResult, AssessmentStatus
from app.mastery.interfaces import MasteryPolicy
from app.mastery.models import MasteryBand, MasteryEvaluationResult


class RuleBasedMasteryPolicy(MasteryPolicy):
    """Pure, deterministic rule-based mastery progression evaluator.

    Invariants (FR-009, FR-015, ADR-011):
    - System uncertainty (UNCERTAIN or NO_RESPONSE) is ineligible for mastery change.
    - Decisions are pure functions of (previous state, evidence, policy version).
    - Explanation codes provide transparent auditability without opaque models.
    """

    def __init__(self, policy_version: str = "MASTERY-RULE-1.0") -> None:
        self.policy_version = policy_version

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
        # 1. Uncertainty Guard (FR-009, FR-015): Uncertain evidence is ineligible
        if assessment.status in (AssessmentStatus.UNCERTAIN, AssessmentStatus.NO_RESPONSE):
            return MasteryEvaluationResult(
                child_id=child_id,
                skill_token=skill_token,
                previous_band=current_band,
                new_band=current_band,
                practice_count=current_practice_count,
                success_count=current_success_count,
                is_updated=False,
                policy_version=self.policy_version,
                explanation_code="SKIPPED_UNCERTAIN",
                transition_reason=(
                    "System uncertainty or silence is ineligible for mastery changes (FR-009)"
                ),
            )

        # 2. Increment practice counts for eligible attempts
        new_practice_count = current_practice_count + 1
        new_success_count = current_success_count + (1 if assessment.is_correct else 0)

        # 3. Transparent Band Progression Logic (ADR-011)
        if current_band == MasteryBand.INTRODUCED:
            if new_success_count >= 1:
                return MasteryEvaluationResult(
                    child_id=child_id,
                    skill_token=skill_token,
                    previous_band=current_band,
                    new_band=MasteryBand.PRACTICING,
                    practice_count=new_practice_count,
                    success_count=new_success_count,
                    is_updated=True,
                    policy_version=self.policy_version,
                    explanation_code="PROMOTED_PRACTICING",
                    transition_reason="First successful attempt demonstrates emerging proficiency",
                )
            return MasteryEvaluationResult(
                child_id=child_id,
                skill_token=skill_token,
                previous_band=current_band,
                new_band=current_band,
                practice_count=new_practice_count,
                success_count=new_success_count,
                is_updated=True,
                policy_version=self.policy_version,
                explanation_code="MAINTAINED_BAND",
                transition_reason="Additional practice required to advance from INTRODUCED",
            )

        if current_band == MasteryBand.PRACTICING:
            # Promote to ACQUIRED if >= 3 successes and success ratio >= 75%
            success_ratio = new_success_count / new_practice_count if new_practice_count > 0 else 0
            if new_success_count >= 3 and success_ratio >= 0.75:
                return MasteryEvaluationResult(
                    child_id=child_id,
                    skill_token=skill_token,
                    previous_band=current_band,
                    new_band=MasteryBand.ACQUIRED,
                    practice_count=new_practice_count,
                    success_count=new_success_count,
                    is_updated=True,
                    policy_version=self.policy_version,
                    explanation_code="PROMOTED_ACQUIRED",
                    transition_reason=(
                        "Mastery consistency reached >= 75% accuracy with >= 3 successes"
                    ),
                )
            return MasteryEvaluationResult(
                child_id=child_id,
                skill_token=skill_token,
                previous_band=current_band,
                new_band=current_band,
                practice_count=new_practice_count,
                success_count=new_success_count,
                is_updated=True,
                policy_version=self.policy_version,
                explanation_code="MAINTAINED_BAND",
                transition_reason=(
                    "Practice count or accuracy ratio insufficient for ACQUIRED promotion"
                ),
            )

        # current_band == MasteryBand.ACQUIRED
        return MasteryEvaluationResult(
            child_id=child_id,
            skill_token=skill_token,
            previous_band=current_band,
            new_band=MasteryBand.ACQUIRED,
            practice_count=new_practice_count,
            success_count=new_success_count,
            is_updated=True,
            policy_version=self.policy_version,
            explanation_code="MAINTAINED_BAND",
            transition_reason="Skill already in ACQUIRED band",
        )
