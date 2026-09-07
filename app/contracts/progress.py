"""Parent-facing progress and session summary contracts (FR-016, SEC-010, DATA-008)."""

import re

from pydantic import Field, field_validator

from app.contracts.base import ContractModel
from app.contracts.mastery import MasteryBand

CLINICAL_TERMS_PATTERN = re.compile(
    r"\b(diagnosis|terapi|terapeutik|speech delay|gangguan|kelainan|abnormal|penyakit|clinical)\b",
    re.IGNORECASE,
)


class SkillProgressDTO(ContractModel):
    """Non-clinical overview of skill exploration progress (FR-016, SEC-010)."""

    skill_id: str = Field(description="Skill token")
    skill_name: str = Field(
        description="Child-friendly skill title (e.g. 'Mengenal Anggota Tubuh')"
    )
    mastery_band: MasteryBand = Field(description="Qualitative progression band")
    practice_count: int = Field(ge=0, description="Total turns practiced")
    recent_success_rate: float = Field(
        ge=0.0, le=1.0, description="Recent attempt success ratio [0.0 - 1.0]"
    )


class SessionSummaryDTO(ContractModel):
    """Encouraging parent summary of a completed learning session (FR-016)."""

    session_id: str = Field(description="Session identifier")
    duration_minutes: int = Field(ge=0, description="Session active duration in minutes")
    completed_activities: int = Field(ge=0, description="Count of successfully finished activities")
    skills_addressed: list[str] = Field(
        default_factory=list, description="List of skill names practiced"
    )
    parent_tip: str = Field(
        description="Non-clinical home encouragement recommendation for parents"
    )

    @field_validator("parent_tip")
    @classmethod
    def validate_non_clinical_copy(cls, value: str) -> str:
        # SEC-010: TOKI is not a diagnostic tool; copy must remain strictly educational
        if CLINICAL_TERMS_PATTERN.search(value):
            raise ValueError(
                "SEC-010 violation: Parent copy contains clinical or diagnostic terminology"
            )
        return value


class ChildProgressDTO(ContractModel):
    """Parent dashboard progress projection contract consumed by Flutter app (FR-016, DATA-008)."""

    child_id: str = Field(description="Pseudonymous child profile identifier (DATA-008)")
    display_name: str = Field(description="Pseudonymous first name or handle")
    age_band: str = Field(description="Developmental age band (e.g. '3-4 tahun')")
    total_sessions_count: int = Field(ge=0, description="Total learning sessions")
    total_activities_count: int = Field(ge=0, description="Total learning activities completed")
    skills: list[SkillProgressDTO] = Field(
        default_factory=list, description="Progress breakdown per skill"
    )
    recent_sessions: list[SessionSummaryDTO] = Field(
        default_factory=list, description="Chronological recent session summaries"
    )
