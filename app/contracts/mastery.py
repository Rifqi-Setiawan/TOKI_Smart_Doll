"""Learning evidence and rule-based mastery progression contracts (FR-014, FR-015, ADR-011)."""

from enum import Enum

from pydantic import Field

from app.contracts.base import ContractModel


class MasteryBand(str, Enum):
    """Pedagogical mastery tiers based on verified learning evidence (ADR-011)."""

    EXPLORING = "EXPLORING"
    DEVELOPING = "DEVELOPING"
    PROFICIENT = "PROFICIENT"


class AssistanceLevel(str, Enum):
    """Scaffolding tier utilized during the response turn."""

    INDEPENDENT = "INDEPENDENT"
    HINTED = "HINTED"
    ASSISTED = "ASSISTED"


class LearningEvidence(ContractModel):
    """Verified learning interaction evidence emitted from a resolved turn (FR-014)."""

    evidence_id: str = Field(description="Unique learning evidence identifier")
    session_id: str = Field(description="Associated session ID")
    turn_id: str = Field(description="Associated turn ID")
    child_id: str = Field(description="Pseudonymous child profile ID (DATA-008)")
    skill_id: str = Field(description="Curriculum skill token being exercised")
    activity_id: str = Field(description="Activity definition token")
    is_successful: bool = Field(description="Whether the attempt demonstrated target skill")
    assistance_level: AssistanceLevel = Field(description="Level of scaffolding provided")
    policy_version: str = Field(
        default="RULE-MASTERY-1.0", description="Mastery rule set version (FR-015)"
    )
    timestamp_ms: int = Field(description="Evidence creation timestamp")


class MasteryUpdate(ContractModel):
    """Transparent, deterministic mastery update record with explanation (FR-015, ADR-011)."""

    skill_id: str = Field(description="Skill token")
    child_id: str = Field(description="Pseudonymous child profile ID")
    previous_score: float = Field(ge=0.0, le=1.0, description="Score prior to update [0.0 - 1.0]")
    new_score: float = Field(ge=0.0, le=1.0, description="Updated score [0.0 - 1.0]")
    previous_band: MasteryBand = Field(description="Prior mastery band")
    new_band: MasteryBand = Field(description="Updated mastery band")
    explanation_code: str = Field(description="Deterministic reason code explaining calculation")
    policy_version: str = Field(
        default="RULE-MASTERY-1.0", description="Mastery scoring policy version"
    )
