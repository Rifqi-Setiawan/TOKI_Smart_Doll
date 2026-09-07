"""Atomic unit-of-work coordinator for resolved turns.

Requirements: FR-014, FR-015, DATA-004, DATA-005, ADR-012.
"""

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.response import ResponsePlan
from app.contracts.understanding import AssessmentResult, AssessmentStatus
from app.mastery.interfaces import MasteryPolicy
from app.mastery.models import MasteryBand, MasteryEvaluationResult
from app.mastery.rules import RuleBasedMasteryPolicy
from app.persistence.models import (
    Attempt,
    ChildMastery,
    DomainEvent,
    MasteryHistory,
    OutboxEvent,
    Session,
    Turn,
    utc_now,
)
from app.persistence.repositories import (
    NotFoundError,
    OptimisticLockError,
    PersistenceError,
)


class InjectedFailureError(PersistenceError):
    """Raised during testing when an artificial failure boundary is triggered."""

    pass


@dataclass(frozen=True)
class ResolvedTurnOutcome:
    """Immutable audit outcome of the atomic unit-of-work transaction."""

    turn_id: str
    attempt_id: str
    session_id: str
    state_version: int
    session_state: str
    domain_event_id: str
    outbox_event_id: str
    is_replay: bool
    mastery_result: MasteryEvaluationResult | None = None


class ResolvedTurnUnitOfWork:
    """Coordinates atomic write of turn, attempt, mastery, session, domain event, and outbox."""

    def __init__(
        self,
        session: AsyncSession,
        mastery_policy: MasteryPolicy | None = None,
    ) -> None:
        self.session = session
        self.mastery_policy = mastery_policy or RuleBasedMasteryPolicy()

    async def execute(
        self,
        session_id: str,
        turn_number: int,
        message_id: str,
        item_token: str,
        skill_token: str,
        expected_state_version: int,
        new_session_state: str,
        assessment: AssessmentResult,
        response_plan: ResponsePlan,
        failure_injection_point: str | None = None,
    ) -> ResolvedTurnOutcome:
        """Execute the atomic resolved-turn transaction adhering to ADR-012.

        Enforces:
        - Replay idempotency: duplicate message_id returns prior durable outcome (DATA-004).
        - Optimistic concurrency: state_version mismatch raises OptimisticLockError (DATA-002).
        - All-or-nothing atomicity across all six records (FR-014).
        - Uncertainty ineligibility for mastery penalty (FR-009, FR-015).
        - Append-only domain events and outbox equality (DATA-005).
        """
        # 1. Idempotency Check (DATA-004)
        stmt = select(Attempt).where(Attempt.message_id == message_id)
        existing_attempt = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing_attempt is not None:
            # Query existing turn and session to return prior durable state
            turn_stmt = select(Turn).where(Turn.id == existing_attempt.turn_id)
            prior_turn = (await self.session.execute(turn_stmt)).scalar_one()

            sess_stmt = select(Session).where(Session.id == session_id)
            current_sess = (await self.session.execute(sess_stmt)).scalar_one()

            # Find matching domain event if present
            event_stmt = (
                select(DomainEvent)
                .where(
                    DomainEvent.session_id == session_id,
                    DomainEvent.event_sequence == turn_number,
                )
                .limit(1)
            )
            prior_event = (await self.session.execute(event_stmt)).scalar_one_or_none()
            event_id = prior_event.id if prior_event else "prior-event"

            return ResolvedTurnOutcome(
                turn_id=prior_turn.id,
                attempt_id=existing_attempt.id,
                session_id=session_id,
                state_version=current_sess.state_version,
                session_state=current_sess.state,
                domain_event_id=event_id,
                outbox_event_id="prior-outbox",
                is_replay=True,
                mastery_result=None,
            )

        # 2. Optimistic Concurrency Check (DATA-002)
        sess_stmt = select(Session).where(Session.id == session_id)
        session_record = (await self.session.execute(sess_stmt)).scalar_one_or_none()
        if session_record is None:
            raise NotFoundError(f"Session '{session_id}' not found")

        if session_record.state_version != expected_state_version:
            raise OptimisticLockError(
                f"DATA-002 violation: Stale state_version on session '{session_id}'. "
                f"Expected {expected_state_version}, actual {session_record.state_version}"
            )

        # 3. Atomic Unit of Work Execution
        try:
            async with self.session.begin_nested():
                # 3.1 Turn Resolution Record
                turn_stmt = select(Turn).where(
                    Turn.session_id == session_id,
                    Turn.turn_number == turn_number,
                )
                turn_record = (await self.session.execute(turn_stmt)).scalar_one_or_none()

                new_state_version = expected_state_version + 1
                now = utc_now()

                if turn_record is None:
                    turn_record = Turn(
                        id=str(uuid4()),
                        session_id=session_id,
                        turn_number=turn_number,
                        item_token=item_token,
                        state_version=new_state_version,
                        status="RESOLVED",
                        created_at=now,
                        resolved_at=now,
                    )
                    self.session.add(turn_record)
                else:
                    turn_record.item_token = item_token
                    turn_record.state_version = new_state_version
                    turn_record.status = "RESOLVED"
                    turn_record.resolved_at = now

                await self.session.flush()
                if failure_injection_point == "after_turn":
                    raise InjectedFailureError("Simulated failure after turn write")

                # 3.2 Attempt / Learning Evidence Record
                attempt_record = Attempt(
                    id=str(uuid4()),
                    turn_id=turn_record.id,
                    message_id=message_id,
                    is_correct=assessment.is_correct,
                    reason_code=assessment.reason_code.value,
                    confidence=assessment.confidence,
                    spoken_text=response_plan.spoken_text,
                    assistance_level="NONE",
                    created_at=now,
                )
                self.session.add(attempt_record)
                await self.session.flush()
                if failure_injection_point == "after_attempt":
                    raise InjectedFailureError("Simulated failure after attempt write")

                # 3.3 Mastery Update & History Record (ADR-011, FR-015)
                mastery_result: MasteryEvaluationResult | None = None
                # FR-009, FR-015: Uncertain evidence is ineligible for mastery
                if assessment.status not in (
                    AssessmentStatus.UNCERTAIN,
                    AssessmentStatus.NO_RESPONSE,
                ):
                    mastery_stmt = select(ChildMastery).where(
                        ChildMastery.child_id == session_record.child_id,
                        ChildMastery.skill_token == skill_token,
                    )
                    mastery_record = (await self.session.execute(mastery_stmt)).scalar_one_or_none()

                    if mastery_record is None:
                        current_band = MasteryBand.INTRODUCED
                        current_practice = 0
                        current_success = 0
                        mastery_record = ChildMastery(
                            id=str(uuid4()),
                            child_id=session_record.child_id,
                            skill_token=skill_token,
                            mastery_band=current_band.value,
                            practice_count=0,
                            success_count=0,
                            last_attempt_at=now,
                            updated_at=now,
                        )
                        self.session.add(mastery_record)
                    else:
                        current_band = MasteryBand(mastery_record.mastery_band)
                        current_practice = mastery_record.practice_count
                        current_success = mastery_record.success_count

                    mastery_result = self.mastery_policy.evaluate_mastery(
                        child_id=session_record.child_id,
                        skill_token=skill_token,
                        current_band=current_band,
                        current_practice_count=current_practice,
                        current_success_count=current_success,
                        assessment=assessment,
                    )

                    mastery_record.mastery_band = mastery_result.new_band.value
                    mastery_record.practice_count = mastery_result.practice_count
                    mastery_record.success_count = mastery_result.success_count
                    mastery_record.last_attempt_at = now
                    mastery_record.updated_at = now

                    # Audit trail history
                    history_record = MasteryHistory(
                        id=str(uuid4()),
                        child_id=session_record.child_id,
                        skill_token=skill_token,
                        attempt_id=attempt_record.id,
                        previous_band=mastery_result.previous_band.value,
                        new_band=mastery_result.new_band.value,
                        transition_reason=mastery_result.explanation_code,
                        created_at=now,
                    )
                    self.session.add(history_record)
                    await self.session.flush()

                if failure_injection_point == "after_mastery":
                    raise InjectedFailureError("Simulated failure after mastery write")

                # 3.4 Session Snapshot Update (Optimistic Concurrency DATA-002)
                session_record.state = new_session_state
                session_record.state_version = new_state_version
                session_record.current_turn_number = turn_number
                session_record.updated_at = now
                await self.session.flush()

                if failure_injection_point == "after_session":
                    raise InjectedFailureError("Simulated failure after session write")

                # 3.5 Append-Only Domain Event (DATA-005)
                event_payload: dict[str, Any] = {
                    "session_id": session_id,
                    "turn_id": turn_record.id,
                    "turn_number": turn_number,
                    "item_token": item_token,
                    "skill_token": skill_token,
                    "message_id": message_id,
                    "is_correct": assessment.is_correct,
                    "reason_code": assessment.reason_code.value,
                    "pedagogical_act": response_plan.pedagogical_act.value,
                    "spoken_text": response_plan.spoken_text,
                    "audio_asset_id": response_plan.audio_asset_id,
                    "state_version": new_state_version,
                    "session_state": new_session_state,
                }
                if mastery_result:
                    event_payload["mastery"] = {
                        "previous_band": mastery_result.previous_band.value,
                        "new_band": mastery_result.new_band.value,
                        "practice_count": mastery_result.practice_count,
                        "success_count": mastery_result.success_count,
                        "explanation_code": mastery_result.explanation_code,
                    }

                domain_event = DomainEvent(
                    id=str(uuid4()),
                    session_id=session_id,
                    event_sequence=turn_number,
                    event_type="session.turn_resolved",
                    payload=event_payload,
                    privacy_class="OPERATIONAL",
                    created_at=now,
                )
                self.session.add(domain_event)
                await self.session.flush()

                if failure_injection_point == "after_event":
                    raise InjectedFailureError("Simulated failure after domain event write")

                # 3.6 Transactional Outbox Event (DATA-005, ADR-012)
                outbox_event = OutboxEvent(
                    id=str(uuid4()),
                    event_id=domain_event.id,
                    topic="session.turn_resolved",
                    payload=event_payload,
                    status="PENDING",
                    retry_count=0,
                    created_at=now,
                )
                self.session.add(outbox_event)
                await self.session.flush()

                if failure_injection_point == "after_outbox":
                    raise InjectedFailureError("Simulated failure after outbox write")

            # Outer session commit
            await self.session.commit()

            return ResolvedTurnOutcome(
                turn_id=turn_record.id,
                attempt_id=attempt_record.id,
                session_id=session_id,
                state_version=new_state_version,
                session_state=new_session_state,
                domain_event_id=domain_event.id,
                outbox_event_id=outbox_event.id,
                is_replay=False,
                mastery_result=mastery_result,
            )

        except Exception:
            await self.session.rollback()
            raise
