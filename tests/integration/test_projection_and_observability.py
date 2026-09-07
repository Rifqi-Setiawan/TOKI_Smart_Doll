"""Integration tests for event projection, outbox consumption, and turn observability.

Requirements: FR-016, FR-017, FR-021, OBS-001–005, SEC-007.
"""

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.analytics.projector import EventProjector
from app.contracts.device import DisplayState, GestureType
from app.contracts.response import ContentProvenance, PedagogicalAct, ResponsePlan
from app.contracts.understanding import AssessmentReasonCode, AssessmentResult, AssessmentStatus
from app.persistence.database import Base, get_engine, get_session_maker
from app.persistence.models import DomainEvent, OutboxEvent
from app.persistence.repositories import SessionRepository
from app.persistence.seed import seed_minimal_database
from app.persistence.unit_of_work import ResolvedTurnUnitOfWork
from app.telemetry.redaction import scan_for_privacy_violations
from app.telemetry.tracer import TurnTracer


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


@pytest.mark.asyncio
async def test_end_to_end_outbox_consumption_projection_and_trace(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """FR-016, FR-017, OBS-001-005, SEC-007: Outbox consumption, projection, and turn trace."""
    _, session_maker = shared_db

    # 1. Create active session
    async with session_maker() as session:
        repo = SessionRepository(session)
        sess = await repo.create_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )
        await session.commit()
        session_id = sess.id

    # 2. Execute resolved turn via Unit of Work
    async with session_maker() as session:
        uow = ResolvedTurnUnitOfWork(session)
        assessment = AssessmentResult(
            session_id=session_id,
            turn_id="turn-e2e-1",
            state_version=1,
            target_concept="colors.red",
            status=AssessmentStatus.CORRECT,
            is_correct=True,
            confidence=0.95,
            reason_code=AssessmentReasonCode.EXACT_MATCH,
            matched_phrase="merah",
            evaluation_latency_ms=18.0,
        )
        response_plan = ResponsePlan(
            plan_id=str(uuid4()),
            session_id=session_id,
            turn_id="turn-e2e-1",
            pedagogical_act=PedagogicalAct.PRAISE,
            approved_text="Bagus, itu merah!",
            spoken_text="Bagus, itu merah!",
            audio_asset_id="audio-asset-praise-01",
            provenance=ContentProvenance(
                curriculum_version="curriculum-v1.0",
                module_id="colors",
                activity_id="color_naming",
                template_id="tpl_red_01",
            ),
            display=DisplayState.HAPPY,
            gesture=GestureType.CELEBRATE,
        )

        outcome = await uow.execute(
            session_id=session_id,
            turn_number=1,
            message_id="msg-e2e-101",
            item_token="item.colors.red",
            skill_token="colors.red",
            expected_state_version=1,
            new_session_state="IN_PROGRESS",
            assessment=assessment,
            response_plan=response_plan,
        )

    # 3. Verify OutboxEvent is PENDING
    async with session_maker() as session:
        outbox = (
            await session.execute(
                select(OutboxEvent).where(OutboxEvent.id == outcome.outbox_event_id)
            )
        ).scalar_one()
        assert outbox.status == "PENDING"

    # 4. Consume Outbox with EventProjector
    projector = EventProjector()
    async with session_maker() as session:
        consumed = await projector.consume_pending_outbox(session)
        assert consumed == 1

    # Verify OutboxEvent is now PUBLISHED
    async with session_maker() as session:
        outbox = (
            await session.execute(
                select(OutboxEvent).where(OutboxEvent.id == outcome.outbox_event_id)
            )
        ).scalar_one()
        assert outbox.status == "PUBLISHED"
        assert outbox.published_at is not None

    # 5. Verify ChildProgressDTO from projection
    progress = projector.get_child_progress("child-demo-001")
    assert progress.total_sessions_count == 1
    assert progress.total_activities_count == 1
    assert len(progress.skills) == 1
    assert progress.skills[0].skill_id == "colors.red"
    assert progress.skills[0].practice_count == 1
    assert progress.skills[0].recent_success_rate == 1.0

    # 6. Rebuild Equivalence Check (FR-017)
    async with session_maker() as session:
        events = (await session.execute(select(DomainEvent))).scalars().all()
    rebuild_projector = EventProjector()
    rebuild_results = rebuild_projector.rebuild(list(events), {session_id: "child-demo-001"})
    assert "child-demo-001" in rebuild_results
    assert rebuild_results["child-demo-001"].model_dump() == progress.model_dump()

    # 7. Record Root Turn Trace and Run Privacy Scan (OBS-001, OBS-002, SEC-007)
    tracer = TurnTracer()
    trace = TurnTracer.create_trace(
        session_id=session_id,
        turn_id="turn-e2e-1",
        turn_number=1,
        message_id="msg-e2e-101",
        state_before="INITIALIZING",
        state_after="IN_PROGRESS",
        state_version=2,
        curriculum_version="curriculum-v1.0",
        module_id="colors",
        activity_id="color_naming",
        template_id="tpl_red_01",
        item_token="item.colors.red",
        assessment_status="CORRECT",
        is_correct=True,
        confidence=0.95,
        reason_code="EXACT_MATCH",
        pedagogical_act="PRAISE",
        spoken_text="Bagus, itu merah!",
        audio_asset_id="audio-asset-praise-01",
        previous_mastery_band="INTRODUCED",
        new_mastery_band="PRACTICING",
        mastery_explanation_code="PROMOTED_PRACTICING",
        mastery_transition_reason="First successful attempt demonstrates emerging proficiency",
        assessment_latency_ms=18.0,
        total_turn_latency_ms=75.0,
    )
    tracer.record_trace(trace)

    # SEC-007: Redaction scan reports 0 critical findings
    trace_dict = trace.model_dump()
    violations = scan_for_privacy_violations(trace_dict)
    assert violations == []
