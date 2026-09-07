"""Read models and DTO builders for parent progress projections (FR-016, SEC-010)."""

from dataclasses import dataclass, field
from datetime import datetime

from app.contracts.mastery import MasteryBand
from app.contracts.progress import (
    ChildProgressDTO,
    SessionSummaryDTO,
    SkillProgressDTO,
)


def to_progress_mastery_band(band_value: str) -> MasteryBand:
    """Map domain or contract band strings to qualitative parent mastery bands."""
    mapping = {
        "INTRODUCED": MasteryBand.EXPLORING,
        "PRACTICING": MasteryBand.DEVELOPING,
        "ACQUIRED": MasteryBand.PROFICIENT,
        "EXPLORING": MasteryBand.EXPLORING,
        "DEVELOPING": MasteryBand.DEVELOPING,
        "PROFICIENT": MasteryBand.PROFICIENT,
    }
    return mapping.get(band_value.upper(), MasteryBand.EXPLORING)


EDUCATIONAL_PARENT_TIPS: dict[str, str] = {
    "colors": "Ajak ananda bermain mencari dan menyebutkan warna benda di sekitar rumah ya!",
    "body_parts": "Bermain tebak anggota tubuh sambil bercermin dapat melatih kosakata ananda.",
    "animals": "Ajak ananda menirukan suara hewan yang ramah untuk melatih pelafalan kata.",
    "default": "Beri senyuman dan apresiasi setiap kali ananda berani mencoba bersuara.",
}


@dataclass
class SkillProgressState:
    """Internal state tracking progress metrics for a single curriculum skill."""

    skill_id: str
    skill_name: str
    mastery_band: MasteryBand = MasteryBand.EXPLORING
    total_practices: int = 0
    correct_attempts: int = 0
    uncertain_attempts: int = 0  # OBS-005: distinct from incorrect

    @property
    def recent_success_rate(self) -> float:
        """Compute success rate over eligible attempts (excluding neutral uncertainty)."""
        eligible = self.total_practices - self.uncertain_attempts
        if eligible <= 0:
            return 0.0
        return round(self.correct_attempts / eligible, 2)

    def to_dto(self) -> SkillProgressDTO:
        return SkillProgressDTO(
            skill_id=self.skill_id,
            skill_name=self.skill_name,
            mastery_band=self.mastery_band,
            practice_count=self.total_practices,
            recent_success_rate=self.recent_success_rate,
        )


@dataclass
class SessionProgressState:
    """Internal state tracking progress metrics for a single session."""

    session_id: str
    start_time: datetime | None = None
    last_turn_time: datetime | None = None
    completed_activities: int = 0
    skills_addressed: set[str] = field(default_factory=set)

    @property
    def duration_minutes(self) -> int:
        if not self.start_time or not self.last_turn_time:
            return 1
        elapsed = (self.last_turn_time - self.start_time).total_seconds() / 60.0
        return max(1, int(round(elapsed)))

    def to_dto(self) -> SessionSummaryDTO:
        # Determine parent tip based on skills addressed
        tip = EDUCATIONAL_PARENT_TIPS["default"]
        for skill in sorted(self.skills_addressed):
            prefix = skill.split(".")[0]
            if prefix in EDUCATIONAL_PARENT_TIPS:
                tip = EDUCATIONAL_PARENT_TIPS[prefix]
                break

        return SessionSummaryDTO(
            session_id=self.session_id,
            duration_minutes=self.duration_minutes,
            completed_activities=self.completed_activities,
            skills_addressed=sorted(self.skills_addressed),
            parent_tip=tip,
        )


@dataclass
class ChildProgressState:
    """Aggregated child-level read model state."""

    child_id: str
    display_name: str = "Sahabat Toki"
    age_band: str = "3-4 tahun"
    sessions: dict[str, SessionProgressState] = field(default_factory=dict)
    skills: dict[str, SkillProgressState] = field(default_factory=dict)

    def to_dto(self) -> ChildProgressDTO:
        skill_dtos = [skill.to_dto() for skill in self.skills.values()]
        session_dtos = [sess.to_dto() for sess in self.sessions.values()]

        # Sort sessions chronologically if possible
        total_activities = sum(s.completed_activities for s in self.sessions.values())

        return ChildProgressDTO(
            child_id=self.child_id,
            display_name=self.display_name,
            age_band=self.age_band,
            total_sessions_count=len(self.sessions),
            total_activities_count=total_activities,
            skills=skill_dtos,
            recent_sessions=session_dtos,
        )
