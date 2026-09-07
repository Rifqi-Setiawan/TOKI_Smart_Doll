"""Integration tests for atomic resolved-turn unit of work.

Requirements: FR-014, FR-015, DATA-004, DATA-005, ADR-012.
"""

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.contracts.device import DisplayState, GestureType
from app.contracts.response import ContentProvenance, PedagogicalAct, ResponsePlan
from app.contracts.understanding import AssessmentReasonCode, AssessmentResult, AssessmentStatus
from app.mastery.models import MasteryBand
from app.mastery.rules import RuleBasedMasteryPolicy
from app.persistence.database import Base, get_engine, get_session_maker
from app.persistence.models import (
    Attempt,
    ChildMastery,
    DomainEvent,
    MasteryHistory,
    OutboxEvent,
    Session,
    Turn,
)
from app.persistence.repositories import (
    OptimisticLockError,
    SessionRepository,
)
from app.persistence.seed import seed_minimal_database
from app.persistence.unit_of_work import (
    InjectedFailureError,
    ResolvedTurnUnitOfWork,
)


@pytest.fixture
async def shared_db() -> AsyncGenerator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]], None]:
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = get_session_maker(engine)
    async with session_maker() as session:
        await seed_minimal_database(session)
        await session.commit()

    yield engine, session_maker
    await engine.dispose()


def make_assessment(
    session_id: str,
    turn_id: str,
    status: AssessmentStatus = AssessmentStatus.CORRECT,
    is_correct: bool = True,
    confidence: float = 0.95,
    reason_code: AssessmentReasonCode = AssessmentReasonCode.EXACT_MATCH,
    matched_phrase: str | None = "red",
) -> AssessmentResult:
    return AssessmentResult(
        session_id=session_id,
        turn_id=turn_id,
        state_version=1,
        target_concept="colors.red",
        status=status,
        is_correct=is_correct,
        confidence=confidence,
        reason_code=reason_code,
        matched_phrase=matched_phrase,
        evaluation_latency_ms=15.0,
    )


def make_response_plan(session_id: str, turn_id: str) -> ResponsePlan:
    return ResponsePlan(
        plan_id=str(uuid4()),
        session_id=session_id,
        turn_id=turn_id,
        pedagogical_act=PedagogicalAct.PRAISE,
        approved_text="Great job, that is red!",
        spoken_text="Great job, that is red!",
        audio_asset_id="audio-asset-praise-01",
        provenance=ContentProvenance(
            curriculum_version="curriculum-v1.0",
            module_id="colors",
            activity_id="color_naming",
            template_id="tpl_praise_01",
        ),
        display=DisplayState.HAPPY,
        gesture=GestureType.NOD,
    )


@pytest.mark.asyncio
async def test_resolved_turn_atomic_commit_all_six_records(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """FR-014: All six records commit atomically in a single transaction."""
    _, session_maker = shared_db

    async with session_maker() as session:
        repo = SessionRepository(session)
        active_session = await repo.create_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )
        await session.commit()
        session_id = active_session.id

    async with session_maker() as session:
        uow = ResolvedTurnUnitOfWork(session)
        assessment = make_assessment(session_id=session_id, turn_id="turn-1")
        response_plan = make_response_plan(session_id=session_id, turn_id="turn-1")

        outcome = await uow.execute(
            session_id=session_id,
            turn_number=1,
            message_id="msg-101",
            item_token="item.colors.red",
            skill_token="colors.red",
            expected_state_version=1,
            new_session_state="IN_PROGRESS",
            assessment=assessment,
            response_plan=response_plan,
        )

        assert outcome.is_replay is False
        assert outcome.state_version == 2
        assert outcome.session_state == "IN_PROGRESS"
        assert outcome.mastery_result is not None
        assert outcome.mastery_result.new_band == MasteryBand.PRACTICING
        assert outcome.mastery_result.explanation_code == "PROMOTED_PRACTICING"

    # Verify all 6 records are durably present in DB
    async with session_maker() as session:
        turn = (await session.execute(select(Turn).where(Turn.id == outcome.turn_id))).scalar_one()
        assert turn.turn_number == 1
        assert turn.status == "RESOLVED"
        assert turn.state_version == 2

        attempt = (
            await session.execute(select(Attempt).where(Attempt.id == outcome.attempt_id))
        ).scalar_one()
        assert attempt.message_id == "msg-101"
        assert attempt.is_correct is True

        mastery = (
            await session.execute(
                select(ChildMastery).where(
                    ChildMastery.child_id == "child-demo-001",
                    ChildMastery.skill_token == "colors.red",
                )
            )
        ).scalar_one()
        assert mastery.mastery_band == MasteryBand.PRACTICING.value
        assert mastery.practice_count == 1
        assert mastery.success_count == 1

        history = (
            await session.execute(
                select(MasteryHistory).where(MasteryHistory.attempt_id == outcome.attempt_id)
            )
        ).scalar_one()
        assert history.previous_band == MasteryBand.INTRODUCED.value
        assert history.new_band == MasteryBand.PRACTICING.value
        assert history.transition_reason == "PROMOTED_PRACTICING"

        sess = (await session.execute(select(Session).where(Session.id == session_id))).scalar_one()
        assert sess.state_version == 2
        assert sess.state == "IN_PROGRESS"
        assert sess.current_turn_number == 1

        event = (
            await session.execute(
                select(DomainEvent).where(DomainEvent.id == outcome.domain_event_id)
            )
        ).scalar_one()
        assert event.event_type == "session.turn_resolved"
        assert event.event_sequence == 1

        outbox = (
            await session.execute(
                select(OutboxEvent).where(OutboxEvent.id == outcome.outbox_event_id)
            )
        ).scalar_one()
        assert outbox.status == "PENDING"
        assert outbox.event_id == event.id

        # Check payload equality between domain event and outbox
        assert outbox.payload == event.payload


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fail_point",
    [
        "after_turn",
        "after_attempt",
        "after_mastery",
        "after_session",
        "after_event",
        "after_outbox",
    ],
)
async def test_failure_injection_all_boundaries_leave_zero_rows(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
    fail_point: str,
) -> None:
    """FR-014: Failure injection at boundary triggers rollback leaving 0 partial records."""
    _, session_maker = shared_db

    async with session_maker() as session:
        repo = SessionRepository(session)
        active_session = await repo.create_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )
        await session.commit()
        session_id = active_session.id

    async with session_maker() as session:
        uow = ResolvedTurnUnitOfWork(session)
        assessment = make_assessment(session_id=session_id, turn_id="turn-fail")
        response_plan = make_response_plan(session_id=session_id, turn_id="turn-fail")

        with pytest.raises(InjectedFailureError):
            await uow.execute(
                session_id=session_id,
                turn_number=1,
                message_id="msg-fail-test",
                item_token="item.colors.red",
                skill_token="colors.red",
                expected_state_version=1,
                new_session_state="IN_PROGRESS",
                assessment=assessment,
                response_plan=response_plan,
                failure_injection_point=fail_point,
            )

    # In a fresh session, verify zero partial records exist across all 6 entities
    async with session_maker() as session:
        turn_count = (
            await session.execute(select(func.count(Turn.id)).where(Turn.session_id == session_id))
        ).scalar_one()
        assert turn_count == 0

        attempt_count = (
            await session.execute(
                select(func.count(Attempt.id)).where(Attempt.message_id == "msg-fail-test")
            )
        ).scalar_one()
        assert attempt_count == 0

        mastery_count = (
            await session.execute(
                select(func.count(ChildMastery.id)).where(
                    ChildMastery.child_id == "child-demo-001",
                    ChildMastery.skill_token == "colors.red",
                )
            )
        ).scalar_one()
        assert mastery_count == 0

        history_count = (
            await session.execute(
                select(func.count(MasteryHistory.id)).where(
                    MasteryHistory.child_id == "child-demo-001"
                )
            )
        ).scalar_one()
        assert history_count == 0

        event_count = (
            await session.execute(
                select(func.count(DomainEvent.id)).where(DomainEvent.session_id == session_id)
            )
        ).scalar_one()
        assert event_count == 0

        outbox_count = (
            await session.execute(
                select(func.count(OutboxEvent.id)).where(
                    OutboxEvent.topic == "session.turn_resolved"
                )
            )
        ).scalar_one()
        assert outbox_count == 0

        # Verify session state was untouched
        sess = (await session.execute(select(Session).where(Session.id == session_id))).scalar_one()
        assert sess.state == "INITIALIZING"
        assert sess.state_version == 1


@pytest.mark.asyncio
async def test_idempotency_replay_creates_zero_duplicates(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """DATA-004: Replay with identical message_id returns prior durable outcome."""
    _, session_maker = shared_db

    async with session_maker() as session:
        repo = SessionRepository(session)
        active_session = await repo.create_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )
        await session.commit()
        session_id = active_session.id

    # 1. First execution
    async with session_maker() as session:
        uow = ResolvedTurnUnitOfWork(session)
        assessment = make_assessment(session_id=session_id, turn_id="turn-1")
        response_plan = make_response_plan(session_id=session_id, turn_id="turn-1")

        first_outcome = await uow.execute(
            session_id=session_id,
            turn_number=1,
            message_id="msg-replay-101",
            item_token="item.colors.red",
            skill_token="colors.red",
            expected_state_version=1,
            new_session_state="IN_PROGRESS",
            assessment=assessment,
            response_plan=response_plan,
        )
        assert first_outcome.is_replay is False

    # 2. Replay execution with identical message_id
    async with session_maker() as session:
        uow = ResolvedTurnUnitOfWork(session)
        replay_outcome = await uow.execute(
            session_id=session_id,
            turn_number=1,
            message_id="msg-replay-101",
            item_token="item.colors.red",
            skill_token="colors.red",
            expected_state_version=2,  # Notice state_version changed
            new_session_state="IN_PROGRESS",
            assessment=assessment,
            response_plan=response_plan,
        )
        assert replay_outcome.is_replay is True
        assert replay_outcome.turn_id == first_outcome.turn_id
        assert replay_outcome.attempt_id == first_outcome.attempt_id
        assert replay_outcome.domain_event_id == first_outcome.domain_event_id

    # 3. Verify exactly 1 record in each table, zero duplicates
    async with session_maker() as session:
        attempts = (
            await session.execute(
                select(func.count(Attempt.id)).where(Attempt.message_id == "msg-replay-101")
            )
        ).scalar_one()
        assert attempts == 1

        events = (
            await session.execute(
                select(func.count(DomainEvent.id)).where(DomainEvent.session_id == session_id)
            )
        ).scalar_one()
        assert events == 1

        outbox_count = (
            await session.execute(
                select(func.count(OutboxEvent.id)).where(
                    OutboxEvent.topic == "session.turn_resolved"
                )
            )
        ).scalar_one()
        assert outbox_count == 1


@pytest.mark.asyncio
async def test_stale_state_version_rejected_without_partial_commit(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """DATA-002: State version mismatch raises OptimisticLockError and commits no records."""
    _, session_maker = shared_db

    async with session_maker() as session:
        repo = SessionRepository(session)
        active_session = await repo.create_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )
        await session.commit()
        session_id = active_session.id

    async with session_maker() as session:
        uow = ResolvedTurnUnitOfWork(session)
        assessment = make_assessment(session_id=session_id, turn_id="turn-1")
        response_plan = make_response_plan(session_id=session_id, turn_id="turn-1")

        with pytest.raises(OptimisticLockError):
            await uow.execute(
                session_id=session_id,
                turn_number=1,
                message_id="msg-stale-test",
                item_token="item.colors.red",
                skill_token="colors.red",
                expected_state_version=99,  # Stale version! (actual is 1)
                new_session_state="IN_PROGRESS",
                assessment=assessment,
                response_plan=response_plan,
            )

    # Verify zero records committed
    async with session_maker() as session:
        attempt_count = (
            await session.execute(
                select(func.count(Attempt.id)).where(Attempt.message_id == "msg-stale-test")
            )
        ).scalar_one()
        assert attempt_count == 0

        sess = (await session.execute(select(Session).where(Session.id == session_id))).scalar_one()
        assert sess.state_version == 1


@pytest.mark.asyncio
async def test_uncertain_evidence_skips_mastery_and_history(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """FR-009, FR-015: Uncertain evidence persists turn/attempt but skips mastery."""
    _, session_maker = shared_db

    async with session_maker() as session:
        repo = SessionRepository(session)
        active_session = await repo.create_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )
        await session.commit()
        session_id = active_session.id

    async with session_maker() as session:
        uow = ResolvedTurnUnitOfWork(session)
        assessment = make_assessment(
            session_id=session_id,
            turn_id="turn-1",
            status=AssessmentStatus.UNCERTAIN,
            is_correct=False,
            confidence=0.30,
            reason_code=AssessmentReasonCode.LOW_CONFIDENCE,
            matched_phrase=None,
        )
        response_plan = make_response_plan(session_id=session_id, turn_id="turn-1")

        outcome = await uow.execute(
            session_id=session_id,
            turn_number=1,
            message_id="msg-uncertain-101",
            item_token="item.colors.red",
            skill_token="colors.red",
            expected_state_version=1,
            new_session_state="IN_PROGRESS",
            assessment=assessment,
            response_plan=response_plan,
        )

        assert outcome.is_replay is False
        assert outcome.mastery_result is None

    # Verify Turn and Attempt were saved, but Mastery was NOT created
    async with session_maker() as session:
        attempt = (
            await session.execute(select(Attempt).where(Attempt.message_id == "msg-uncertain-101"))
        ).scalar_one()
        assert attempt.reason_code == AssessmentReasonCode.LOW_CONFIDENCE.value

        mastery = (
            await session.execute(
                select(ChildMastery).where(
                    ChildMastery.child_id == "child-demo-001",
                    ChildMastery.skill_token == "colors.red",
                )
            )
        ).scalar_one_or_none()
        assert mastery is None

        history_count = (
            await session.execute(
                select(func.count(MasteryHistory.id)).where(
                    MasteryHistory.child_id == "child-demo-001"
                )
            )
        ).scalar_one()
        assert history_count == 0


def test_mastery_rule_reproducibility() -> None:
    """Evaluation requirement: Reproduce mastery outcome from prior state + evidence + policy."""
    policy = RuleBasedMasteryPolicy(policy_version="MASTERY-RULE-1.0")
    assessment = make_assessment(
        session_id="sess-rep",
        turn_id="turn-rep",
        status=AssessmentStatus.CORRECT,
        is_correct=True,
        confidence=0.95,
        reason_code=AssessmentReasonCode.EXACT_MATCH,
    )

    # First evaluation
    res1 = policy.evaluate_mastery(
        child_id="child-1",
        skill_token="colors.red",
        current_band=MasteryBand.PRACTICING,
        current_practice_count=3,
        current_success_count=2,
        assessment=assessment,
    )

    # Second evaluation with identical inputs
    res2 = policy.evaluate_mastery(
        child_id="child-1",
        skill_token="colors.red",
        current_band=MasteryBand.PRACTICING,
        current_practice_count=3,
        current_success_count=2,
        assessment=assessment,
    )

    assert res1.model_dump() == res2.model_dump()
    assert res1.new_band == MasteryBand.ACQUIRED
    assert res1.explanation_code == "PROMOTED_ACQUIRED"
    assert res1.practice_count == 4
    assert res1.success_count == 3
