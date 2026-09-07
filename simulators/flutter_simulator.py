"""Flutter guardian client simulator validating progress DTO contracts (FR-016, SEC-010)."""

from typing import Any

from app.contracts.progress import ChildProgressDTO, SessionSummaryDTO, SkillProgressDTO


class FlutterSimulator:
    """Simulates mobile client consuming parent progress projections and session summaries."""

    def __init__(self, guardian_id: str = "guard-sim-001") -> None:
        self.guardian_id = guardian_id
        self.validated_progress_dtos: list[ChildProgressDTO] = []
        self.validated_session_summaries: list[SessionSummaryDTO] = []

    def consume_child_progress(self, progress_data: dict[str, Any]) -> ChildProgressDTO:
        """Validate and consume child progress projection."""
        dto = ChildProgressDTO.model_validate(progress_data)
        self.validated_progress_dtos.append(dto)
        return dto

    def consume_session_summary(self, summary_data: dict[str, Any]) -> SessionSummaryDTO:
        """Validate and consume session summary projection, verifying non-clinical claims."""
        summary = SessionSummaryDTO.model_validate(summary_data)
        self.validated_session_summaries.append(summary)
        return summary

    def consume_skill_progress(self, skill_data: dict[str, Any]) -> SkillProgressDTO:
        """Validate individual skill progress entry."""
        return SkillProgressDTO.model_validate(skill_data)
