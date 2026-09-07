"""Mastery progression contracts and evaluation outcome schemas (FR-015, ADR-011)."""

from enum import Enum

from pydantic import Field

from app.contracts.base import ContractModel


class MasteryBand(str, Enum):
    """Pedagogical mastery classification for a curriculum skill (ADR-011)."""

    INTRODUCED = "INTRODUCED"
    PRACTICING = "PRACTICING"
    ACQUIRED = "ACQUIRED"


class MasteryEvaluationResult(ContractModel):
    """Transparent and versioned evaluation outcome for skill mastery progression (FR-015)."""

    child_id: str = Field(description="Target child identifier")
    skill_token: str = Field(description="Skill being evaluated")
    previous_band: MasteryBand = Field(description="Skill band prior to attempt")
    new_band: MasteryBand = Field(description="Resulting skill band after evaluation")
    practice_count: int = Field(ge=0, description="Total eligible practice attempts")
    success_count: int = Field(ge=0, description="Total successful attempts")
    is_updated: bool = Field(description="True if mastery record was modified")
    policy_version: str = Field(
        default="MASTERY-RULE-1.0", description="Versioned mastery policy ruleset"
    )
    explanation_code: str = Field(description="Machine-readable decision explanation code")
    transition_reason: str = Field(description="Human-readable pedagogical explanation")
