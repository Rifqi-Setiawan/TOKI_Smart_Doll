"""End-to-End integration and scenario matrix tests for deterministic vertical slice.

Requirements: REL-005, DEV-002, EVAL-001, FR-001–017, OBS-001–005, SEC-004, SEC-005, SEC-009.
Architecture: ADR-003, ADR-005, ADR-006, ADR-007, ADR-012, ADR-015.
"""

from collections.abc import AsyncGenerator
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.progress import get_projector
from app.api.sessions import get_db
from app.contracts.understanding import AssessmentStatus
from app.main import app
from app.persistence.database import Base, get_engine, get_session_maker
from app.persistence.models import Attempt, ChildMastery, OutboxEvent, Session, Turn
from app.persistence.seed import seed_minimal_database
from app.sessions.activity_slice import DeterministicActivitySlice
from app.sessions.states import SessionState


@pytest.fixture
async def shared_db() -> AsyncGenerator[tuple[AsyncEngine, async_sessionmaker[AsyncSession]], None]:
    """In-memory SQLite database initialized with minimal seed data."""
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
async def test_happy_path_normal_activity_complete_lifecycle(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """AC 1 & 2 (Happy Path): Start -> Prompt -> Answer 'mata' -> Correct -> Persist -> Progress -> Trace."""
    _, session_maker = shared_db

    async with session_maker() as session:
        slice_runner = DeterministicActivitySlice(session)

        # 1. Start session
        ctx = await slice_runner.start_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )
        assert ctx.state == SessionState.ACTIVITY_SELECTING

        # 2. Select & prompt activity
        activity, prompt_env = await slice_runner.prompt_activity(
            session_id=ctx.session_id,
            version_token="curriculum-v1.0",
            item_token="body_parts_mata",
        )
        assert activity.item_token == "body_parts_mata"
        assert "melihat" in activity.prompt_text
        assert prompt_env.command is not None

        # 3. Submit simulated correct answer "mata"
        result = await slice_runner.execute_turn(
            session_id=ctx.session_id,
            activity=activity,
            answer_text="mata",
            is_final_activity=True,
        )
        await session.commit()

        # Invariant checks
        assert result.assessment.status == AssessmentStatus.CORRECT
        assert result.assessment.is_correct is True
        assert result.trace is not None
        assert result.trace.is_uncertain is False
        assert result.session_state == SessionState.COMPLETED
        assert result.uow_outcome is not None
        assert result.uow_outcome.is_replay is False

        # Mastery updated from INTRODUCED to PRACTICED
        assert result.uow_outcome.mastery_result is not None
        assert result.uow_outcome.mastery_result.new_band.value == "PRACTICED"

        # Trace verified
        assert result.trace is not None
        assert result.trace.assessment_status == "CORRECT"
        assert result.trace.spoken_text != ""

    # Verify durable persistence in database
    async with session_maker() as session:
        # Check Turn
        turns = (await session.execute(select(Turn).where(Turn.session_id == ctx.session_id))).scalars().all()
        assert len(turns) == 1
        assert turns[0].raw_answer_text == "mata"

        # Check Attempt
        attempts = (await session.execute(select(Attempt).where(Attempt.session_id == ctx.session_id))).scalars().all()
        assert len(attempts) == 1
        assert attempts[0].is_correct is True

        # Check Outbox (all published by EventProjector)
        outbox = (await session.execute(select(OutboxEvent).where(OutboxEvent.session_id == ctx.session_id))).scalars().all()
        assert len(outbox) >= 1
        assert all(o.status == "PUBLISHED" for o in outbox)

        # Check Mastery
        mastery = (await session.execute(select(ChildMastery).where(ChildMastery.child_id == "child-demo-001"))).scalars().first()
        assert mastery is not None
        assert mastery.mastery_band == "PRACTICED"
        assert mastery.practice_count == 1
        assert mastery.success_count == 1

        # Check Progress read model
        progress = slice_runner.projector.get_child_progress("child-demo-001")
        assert progress.child_id == "child-demo-001"
        assert progress.total_activities_completed == 1


@pytest.mark.asyncio
async def test_uncertain_answer_separates_uncertainty_without_incorrect_penalty(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """AC 2 & 4 (FR-009, OBS-005): Low confidence/uncertain answer is NOT counted as child error."""
    _, session_maker = shared_db

    async with session_maker() as session:
        slice_runner = DeterministicActivitySlice(session)
        ctx = await slice_runner.start_session()
        activity, _ = await slice_runner.prompt_activity(session_id=ctx.session_id)

        # Submit simulated low-confidence answer
        result = await slice_runner.execute_turn(
            session_id=ctx.session_id,
            activity=activity,
            answer_text="nggg mata",
            simulate_low_confidence=True,
        )
        await session.commit()

        # Invariant checks
        assert result.assessment.status == AssessmentStatus.UNCERTAIN
        assert result.trace is not None
        assert result.trace.is_uncertain is True
        assert result.assessment.is_correct is False
        assert result.is_retry is True

        # Retry was triggered, state returned to PROMPTING for another chance
        assert result.session_state == SessionState.PROMPTING

    # Verify that mastery did NOT record an incorrect penalty
    async with session_maker() as session:
        mastery = (await session.execute(select(ChildMastery).where(ChildMastery.child_id == "child-demo-001"))).scalars().first()
        assert mastery is not None
        # Unchanged from baseline INTRODUCED, no failure penalty
        assert mastery.mastery_band == "INTRODUCED"
        assert mastery.practice_count == 0


@pytest.mark.asyncio
async def test_no_speech_retry_and_bounded_fallback(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """AC 2 (FR-010): Silence triggers retry; second silence falls back without hanging."""
    _, session_maker = shared_db

    async with session_maker() as session:
        slice_runner = DeterministicActivitySlice(session)
        ctx = await slice_runner.start_session()
        activity, _ = await slice_runner.prompt_activity(session_id=ctx.session_id)

        # 1. First silence -> retry
        res1 = await slice_runner.execute_turn(
            session_id=ctx.session_id,
            activity=activity,
            simulate_silence=True,
        )
        assert res1.assessment.status == AssessmentStatus.NO_RESPONSE
        assert res1.is_retry is True
        assert res1.session_state == SessionState.PROMPTING

        # Advance orchestrator PROMPTING -> LISTENING
        await slice_runner.orchestrator.dispatch_event(
            session_id=ctx.session_id,
            event=slice_runner.orchestrator.policy.SessionEvent.PROMPT_DELIVERED,
        )

        # 2. Second silence -> bounded fallback triggered
        res2 = await slice_runner.execute_turn(
            session_id=ctx.session_id,
            activity=activity,
            simulate_silence=True,
        )
        assert res2.is_fallback is True


@pytest.mark.asyncio
async def test_safety_stop_immediate_canned_override(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """AC 2 (FR-012, FR-022, SEC-005, SEC-009): Safety breach or stop halts immediately with reviewed canned copy."""
    _, session_maker = shared_db

    # Test Safety Escalation
    async with session_maker() as session:
        slice_runner = DeterministicActivitySlice(session)
        ctx = await slice_runner.start_session()
        activity, _ = await slice_runner.prompt_activity(session_id=ctx.session_id)

        # Injected violent safety violation in child input
        res = await slice_runner.execute_turn(
            session_id=ctx.session_id,
            activity=activity,
            answer_text="aku mau lompat dari balkon dan memukul orang",
        )
        assert res.is_safe is False
        assert res.response_plan.is_escalation is True
        assert "aman" in res.response_plan.spoken_text.lower() or "bantuan" in res.response_plan.spoken_text.lower()
        assert res.session_state in (SessionState.SAFETY_ESCALATION, SessionState.SESSION_ENDING, SessionState.COMPLETED)

    # Test Explicit Stop Request
    async with session_maker() as session:
        slice_runner = DeterministicActivitySlice(session)
        ctx = await slice_runner.start_session()
        activity, _ = await slice_runner.prompt_activity(session_id=ctx.session_id)

        res_stop = await slice_runner.execute_turn(
            session_id=ctx.session_id,
            activity=activity,
            answer_text="stop",
        )
        assert res_stop.session_state == SessionState.COMPLETED
        assert "terima kasih" in res_stop.response_plan.spoken_text.lower() or "sampai jumpa" in res_stop.response_plan.spoken_text.lower()


@pytest.mark.asyncio
async def test_duplicate_events_produce_zero_duplicate_effects(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """AC 3 (FR-004, DATA-004): Resending identical event envelope causes zero duplicate side effects."""
    _, session_maker = shared_db

    async with session_maker() as session:
        slice_runner = DeterministicActivitySlice(session)
        ctx = await slice_runner.start_session()
        activity, _ = await slice_runner.prompt_activity(session_id=ctx.session_id)

        # Create fixed envelope
        msg_id = str(uuid4())
        env = slice_runner.simulator.create_audio_chunk_envelope(
            session_id=ctx.session_id,
            turn_id=ctx.current_turn_id or "turn-1",
            chunk_index=0,
            audio_bytes=b"dummy",
        )
        env.message_id = msg_id

        # 1. First execution
        res1 = await slice_runner.execute_turn(
            session_id=ctx.session_id,
            activity=activity,
            answer_text="mata",
            custom_envelope=env,
            is_final_activity=True,
        )
        await session.commit()
        assert res1.is_duplicate is False

        # 2. Duplicate re-send of the exact same envelope
        res2 = await slice_runner.execute_turn(
            session_id=ctx.session_id,
            activity=activity,
            answer_text="mata",
            custom_envelope=env,
            is_final_activity=True,
        )
        await session.commit()
        assert res2.is_duplicate is True
        assert res2.uow_outcome is None

    # Verify in DB: exactly 1 turn, 1 attempt, 1 mastery record
    async with session_maker() as session:
        turns = (await session.execute(select(Turn).where(Turn.session_id == ctx.session_id))).scalars().all()
        assert len(turns) == 1

        attempts = (await session.execute(select(Attempt).where(Attempt.session_id == ctx.session_id))).scalars().all()
        assert len(attempts) == 1

        mastery = (await session.execute(select(ChildMastery).where(ChildMastery.child_id == "child-demo-001"))).scalars().first()
        assert mastery is not None
        assert mastery.practice_count == 1
        assert mastery.success_count == 1


@pytest.mark.asyncio
async def test_process_restart_recovers_last_durable_state(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """AC 2 (FR-005): Simulated server crash/restart between prompt and answer resumes cursor cleanly."""
    _, session_maker = shared_db

    session_id = ""
    # Process 1: Start and prompt activity, then "crashes"
    async with session_maker() as session:
        slice_runner = DeterministicActivitySlice(session)
        ctx = await slice_runner.start_session()
        session_id = ctx.session_id
        activity, _ = await slice_runner.prompt_activity(session_id=session_id)
        await session.commit()

    # Process 2: Clean new process instance spins up against the persistent DB
    async with session_maker() as session:
        new_slice_runner = DeterministicActivitySlice(session)

        # Recovery manager computes resume state
        resume = await new_slice_runner.recovery.compute_resume(session_id)
        assert resume.status == "RESUMED"
        assert resume.resumed_state == SessionState.LISTENING.value

        # Reconstructed session context continues from LISTENING
        recovered_ctx = await new_slice_runner.orchestrator.get_context(session_id)
        assert recovered_ctx.state == SessionState.LISTENING

        # Child submits answer to the resumed process
        result = await new_slice_runner.execute_turn(
            session_id=session_id,
            activity=activity,
            answer_text="mata",
            is_final_activity=True,
        )
        await session.commit()

        assert result.assessment.is_correct is True
        assert result.session_state == SessionState.COMPLETED


@pytest.mark.asyncio
async def test_http_api_end_to_end_activity(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """AC 1: Full deterministic activity lifecycle exercised over HTTP API."""
    _, session_maker = shared_db

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)

    try:
        # 1. POST /api/v1/sessions
        start_resp = test_client.post(
            "/api/v1/sessions",
            json={
                "device_id": "dev-demo-001",
                "child_id": "child-demo-001",
                "curriculum_version_id": "curr-v1.0",
            },
        )
        assert start_resp.status_code == 201
        sess_data = start_resp.json()
        session_id = sess_data["session_id"]
        assert sess_data["state"] == "ACTIVITY_SELECTING"

        # 2. GET /api/v1/sessions/{id}
        get_resp = test_client.get(f"/api/v1/sessions/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["session_id"] == session_id

        # 3. POST /api/v1/sessions/{id}/turns
        turn_resp = test_client.post(
            f"/api/v1/sessions/{session_id}/turns",
            json={
                "activity_token": "body_parts_mata",
                "version_token": "curriculum-v1.0",
                "answer_text": "mata",
                "is_final_activity": True,
            },
        )
        assert turn_resp.status_code == 200
        turn_data = turn_resp.json()
        assert turn_data["assessment_status"] == "CORRECT"
        assert turn_data["is_correct"] is True
        assert turn_data["session_state"] == "COMPLETED"
        assert turn_data["total_latency_ms"] > 0.0

        # 4. GET /api/v1/progress/{child_id}
        progress_resp = test_client.get("/api/v1/progress/child-demo-001")
        assert progress_resp.status_code == 200
        prog_data = progress_resp.json()
        assert prog_data["child_id"] == "child-demo-001"
        assert prog_data["total_activities_completed"] >= 1

    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_local_orchestration_persistence_latency_p95(
    shared_db: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """AC 5: Server orchestration+persistence p95 latency is strictly < 150 ms locally."""
    _, session_maker = shared_db

    latencies: list[float] = []

    async with session_maker() as session:
        slice_runner = DeterministicActivitySlice(session)
        activity = await slice_runner.curriculum.get_active_activity("curriculum-v1.0", "body_parts_mata")

        # Run 20 iterations to measure statistical p50 and p95
        for i in range(20):
            ctx = await slice_runner.start_session(session_id=f"sess-lat-{i}")
            await slice_runner.prompt_activity(session_id=ctx.session_id)

            res = await slice_runner.execute_turn(
                session_id=ctx.session_id,
                activity=activity,
                answer_text="mata",
                is_final_activity=True,
            )
            # Latency excluding network/audio: orchestration + persistence
            combined_latency = res.orchestration_latency_ms + res.persistence_latency_ms
            latencies.append(combined_latency)

    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95_idx = int(len(latencies) * 0.95)
    p95 = latencies[p95_idx]

    print(f"\n[LATENCY MEASUREMENT] iterations=20, p50={p50:.2f}ms, p95={p95:.2f}ms")
    assert p95 < 150.0, f"Criterion 5 violation: p95 latency {p95:.2f}ms exceeds 150ms limit"
