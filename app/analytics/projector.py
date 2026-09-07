"""Idempotent domain event projector for progress read models (FR-016, FR-017, OBS-005)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.projections import (
    ChildProgressState,
    SessionProgressState,
    SkillProgressState,
    to_progress_mastery_band,
)
from app.contracts.progress import ChildProgressDTO
from app.persistence.models import DomainEvent, OutboxEvent, Session, utc_now

UNCERTAIN_REASON_CODES = {
    "LOW_CONFIDENCE",
    "NO_SPEECH_DETECTED",
    "AUDIO_CORRUPTED",
    "UNRESOLVED_AMBIGUOUS",
}


def humanize_skill_name(skill_token: str) -> str:
    """Format skill token into non-clinical, encouraging Indonesian skill title."""
    parts = skill_token.split(".")
    core = parts[-1].replace("_", " ").title()
    prefix = parts[0].lower()
    if prefix == "colors":
        return f"Mengenal Warna: {core}"
    if prefix == "body_parts":
        return f"Mengenal Bagian Tubuh: {core}"
    if prefix == "animals":
        return f"Mengenal Suara & Hewan: {core}"
    return f"Eksplorasi {core}"


class EventProjector:
    """In-memory and transactional outbox event projector for parent summaries."""

    def __init__(self) -> None:
        self.projections: dict[str, ChildProgressState] = {}
        self.processed_event_ids: set[str] = set()
        self.lag_measurements_ms: list[float] = []

    def get_or_create_child_state(self, child_id: str) -> ChildProgressState:
        if child_id not in self.projections:
            self.projections[child_id] = ChildProgressState(child_id=child_id)
        return self.projections[child_id]

    def process_event(
        self,
        event_id: str,
        session_id: str,
        event_sequence: int,
        event_type: str,
        payload: dict[str, Any],
        created_at: datetime,
        child_id: str,
    ) -> bool:
        """Process a domain event into the child progress read model idempotently.

        Invariants:
        - Duplicate event_id has no effect (FR-017, DATA-004).
        - System uncertainty (OBS-005) is tracked separately from incorrect child answers.
        - Measured lag is logged for performance and eventual consistency tracking.
        """
        # 1. Idempotency Guard (FR-017)
        if event_id in self.processed_event_ids:
            return False

        # Only process turn resolution events
        if event_type != "session.turn_resolved":
            self.processed_event_ids.add(event_id)
            return False

        child_state = self.get_or_create_child_state(child_id)

        # 2. Extract Event Data
        skill_token = payload.get("skill_token", "general")
        is_correct = bool(payload.get("is_correct", False))
        reason_code = payload.get("reason_code", "")
        mastery_data = payload.get("mastery")

        # 3. Update Skill State
        if skill_token not in child_state.skills:
            child_state.skills[skill_token] = SkillProgressState(
                skill_id=skill_token,
                skill_name=humanize_skill_name(skill_token),
            )
        skill_state = child_state.skills[skill_token]
        skill_state.total_practices += 1

        # OBS-005: System uncertainty must NOT count as incorrect answer
        if reason_code in UNCERTAIN_REASON_CODES:
            skill_state.uncertain_attempts += 1
        elif is_correct:
            skill_state.correct_attempts += 1

        # Update mastery band if present
        if mastery_data and isinstance(mastery_data, dict):
            new_band_str = mastery_data.get("new_band", "")
            if new_band_str:
                skill_state.mastery_band = to_progress_mastery_band(new_band_str)

        # 4. Update Session Summary State
        if session_id not in child_state.sessions:
            child_state.sessions[session_id] = SessionProgressState(
                session_id=session_id,
                start_time=created_at,
            )
        sess_state = child_state.sessions[session_id]
        sess_state.last_turn_time = created_at
        sess_state.skills_addressed.add(skill_token)
        if is_correct:
            sess_state.completed_activities += 1

        # 5. Measure Projection Lag
        now = datetime.now(UTC)
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)
        lag_ms = max(0.0, (now - created_at).total_seconds() * 1000.0)
        self.lag_measurements_ms.append(lag_ms)

        self.processed_event_ids.add(event_id)
        return True

    def get_child_progress(self, child_id: str) -> ChildProgressDTO:
        """Return the current non-clinical progress projection for a child."""
        child_state = self.get_or_create_child_state(child_id)
        return child_state.to_dto()

    def rebuild(
        self,
        events: list[DomainEvent],
        session_to_child_map: dict[str, str],
    ) -> dict[str, ChildProgressDTO]:
        """Rebuild all read models deterministically from raw domain events (FR-017)."""
        self.projections.clear()
        self.processed_event_ids.clear()
        self.lag_measurements_ms.clear()

        # Sort events by session, sequence, created_at for deterministic replay
        sorted_events = sorted(
            events,
            key=lambda e: (e.session_id or "", e.event_sequence, e.created_at),
        )

        for event in sorted_events:
            session_id = event.session_id or ""
            child_id = session_to_child_map.get(session_id, "child-unknown")
            self.process_event(
                event_id=event.id,
                session_id=session_id,
                event_sequence=event.event_sequence,
                event_type=event.event_type,
                payload=event.payload,
                created_at=event.created_at,
                child_id=child_id,
            )

        return {child_id: state.to_dto() for child_id, state in self.projections.items()}

    async def consume_pending_outbox(self, session: AsyncSession) -> int:
        """Consume pending outbox records and advance their status to PUBLISHED."""
        stmt = (
            select(OutboxEvent, DomainEvent)
            .join(DomainEvent, OutboxEvent.event_id == DomainEvent.id)
            .where(OutboxEvent.status == "PENDING")
            .order_by(OutboxEvent.created_at.asc())
        )
        rows = (await session.execute(stmt)).all()

        if not rows:
            return 0

        # Pre-load session to child mappings
        sess_ids = {dom.session_id for _, dom in rows if dom.session_id}
        child_map: dict[str, str] = {}
        if sess_ids:
            sess_stmt = select(Session.id, Session.child_id).where(Session.id.in_(sess_ids))
            sess_rows = (await session.execute(sess_stmt)).all()
            child_map = {r[0]: r[1] for r in sess_rows}

        processed_count = 0
        now = utc_now()
        for outbox, domain_event in rows:
            sess_id = domain_event.session_id or outbox.payload.get("session_id", "")
            child_id = child_map.get(sess_id, "child-demo-001")

            self.process_event(
                event_id=outbox.event_id,
                session_id=sess_id,
                event_sequence=domain_event.event_sequence,
                event_type=outbox.topic,
                payload=outbox.payload,
                created_at=outbox.created_at,
                child_id=child_id,
            )

            outbox.status = "PUBLISHED"
            outbox.published_at = now
            processed_count += 1

        await session.commit()
        return processed_count
