"""Tests for SessionOrchestrator persistence boundary and invariant enforcement (FR-001, FR-002)."""

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.base import CallbackCorrelation
from app.persistence.database import get_engine, get_session_maker
from app.persistence.models import Base
from app.persistence.repositories import (
    ConsentRepository,
    EventOutboxRepository,
    SessionRepository,
)
from app.persistence.seed import seed_minimal_database
from app.sessions.exceptions import (
    ConsentRequiredError,
    DeviceAuthenticationError,
    SessionTerminalError,
    StaleCallbackError,
)
from app.sessions.orchestrator import SessionOrchestrator
from app.sessions.states import SessionEvent, SessionState


@pytest.fixture
async def isolated_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = get_session_maker(engine)
    async with session_maker() as session:
        await seed_minimal_database(session)
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_orchestrator_session_lifecycle_and_db_persistence(
    isolated_session: AsyncSession,
) -> None:
    """Acceptance Criterion 2: Only orchestrator mutates state and advances state_version.

    Enforces FR-002 and DATA-002 invariants.
    """
    session_repo = SessionRepository(isolated_session)
    consent_repo = ConsentRepository(isolated_session)
    event_repo = EventOutboxRepository(isolated_session)
    orchestrator = SessionOrchestrator(
        session_repo=session_repo,
        consent_repo=consent_repo,
        event_repo=event_repo,
    )

    # 1. Start session
    ctx = await orchestrator.start_session(
        device_id="dev-demo-001",
        child_id="child-demo-001",
        curriculum_version_id="curr-v1.0",
        session_id="sess-orch-001",
    )
    assert ctx.state == SessionState.SESSION_STARTING
    assert ctx.state_version == 1

    # Verify DB record
    db_rec = await session_repo.get_session("sess-orch-001")
    assert db_rec.state == SessionState.SESSION_STARTING.value
    assert db_rec.state_version == 1

    # 2. Advance to GREETING
    res1 = await orchestrator.dispatch_event(
        session_id="sess-orch-001",
        event=SessionEvent.LOAD_COMPLETED,
    )
    assert res1.to_state == SessionState.GREETING
    assert ctx.state_version == 2

    db_rec2 = await session_repo.get_session("sess-orch-001")
    assert db_rec2.state == SessionState.GREETING.value
    assert db_rec2.state_version == 2

    # 3. Advance to ACTIVITY_SELECTING
    res2 = await orchestrator.dispatch_event(
        session_id="sess-orch-001",
        event=SessionEvent.GREETING_DELIVERED,
    )
    assert res2.to_state == SessionState.ACTIVITY_SELECTING
    assert ctx.state_version == 3

    # 4. Advance to PROMPTING (starts Turn 1)
    res3 = await orchestrator.dispatch_event(
        session_id="sess-orch-001",
        event=SessionEvent.ACTIVITY_SELECTED,
    )
    assert res3.to_state == SessionState.PROMPTING
    assert ctx.current_turn_number == 1
    assert ctx.current_turn_id == "turn-1"
    assert ctx.state_version == 4


@pytest.mark.asyncio
async def test_orchestrator_rejects_stale_callback(
    isolated_session: AsyncSession,
) -> None:
    """Acceptance Criterion 5: Stale callbacks are rejected without state divergence.

    Enforces FR-002 and ADR-003.
    """
    session_repo = SessionRepository(isolated_session)
    consent_repo = ConsentRepository(isolated_session)
    orchestrator = SessionOrchestrator(
        session_repo=session_repo,
        consent_repo=consent_repo,
    )

    ctx = await orchestrator.start_session(
        device_id="dev-demo-001",
        child_id="child-demo-001",
        curriculum_version_id="curr-v1.0",
        session_id="sess-stale-001",
    )
    assert ctx.state_version == 1

    # Normal advance to version 2
    await orchestrator.dispatch_event(
        session_id="sess-stale-001",
        event=SessionEvent.LOAD_COMPLETED,
    )
    assert ctx.state_version == 2

    # Stale callback arrives with outdated state_version = 1
    stale_correlation = CallbackCorrelation(
        session_id="sess-stale-001",
        turn_id="turn-1",
        state_version=1,
    )

    with pytest.raises(StaleCallbackError) as exc_info:
        await orchestrator.dispatch_event(
            session_id="sess-stale-001",
            event=SessionEvent.GREETING_DELIVERED,
            correlation=stale_correlation,
        )

    assert "expected version 2, got 1" in str(exc_info.value)

    # Verify DB state did not mutate
    db_rec = await session_repo.get_session("sess-stale-001")
    assert db_rec.state_version == 2
    assert db_rec.state == SessionState.GREETING.value


@pytest.mark.asyncio
async def test_orchestrator_consent_enforcement(
    isolated_session: AsyncSession,
) -> None:
    """Acceptance Criterion 2: Consent revocation blocks new session creation (FR-003, DATA-010)."""
    session_repo = SessionRepository(isolated_session)
    consent_repo = ConsentRepository(isolated_session)
    orchestrator = SessionOrchestrator(
        session_repo=session_repo,
        consent_repo=consent_repo,
    )

    # Revoke consent for the test child
    await consent_repo.revoke_consent("child-demo-001")

    with pytest.raises(ConsentRequiredError):
        await orchestrator.start_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )


@pytest.mark.asyncio
async def test_orchestrator_device_authentication_required(
    isolated_session: AsyncSession,
) -> None:
    """Device ID cannot be empty or missing (SEC-002)."""
    session_repo = SessionRepository(isolated_session)
    consent_repo = ConsentRepository(isolated_session)
    orchestrator = SessionOrchestrator(
        session_repo=session_repo,
        consent_repo=consent_repo,
    )

    with pytest.raises(DeviceAuthenticationError):
        await orchestrator.start_session(
            device_id="",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )


@pytest.mark.asyncio
async def test_orchestrator_stop_interrupt_persisted(
    isolated_session: AsyncSession,
) -> None:
    """Acceptance Criterion 3: Stop action from active turn immediately advances DB.

    Enforces FR-022 and SEC-009.
    """
    session_repo = SessionRepository(isolated_session)
    consent_repo = ConsentRepository(isolated_session)
    orchestrator = SessionOrchestrator(
        session_repo=session_repo,
        consent_repo=consent_repo,
    )

    await orchestrator.start_session(
        device_id="dev-demo-001",
        child_id="child-demo-001",
        curriculum_version_id="curr-v1.0",
        session_id="sess-stop-001",
    )
    await orchestrator.dispatch_event("sess-stop-001", SessionEvent.LOAD_COMPLETED)
    await orchestrator.dispatch_event("sess-stop-001", SessionEvent.GREETING_DELIVERED)
    await orchestrator.dispatch_event("sess-stop-001", SessionEvent.ACTIVITY_SELECTED)

    # Now in PROMPTING: user triggers stop
    res_stop = await orchestrator.request_stop("sess-stop-001", reason="child_nap_time")
    assert res_stop.to_state == SessionState.SESSION_ENDING

    db_rec = await session_repo.get_session("sess-stop-001")
    assert db_rec.state == SessionState.SESSION_ENDING.value

    # Complete session
    await orchestrator.dispatch_event("sess-stop-001", SessionEvent.CLOSING_DELIVERED)
    db_rec_done = await session_repo.get_session("sess-stop-001")
    assert db_rec_done.state == SessionState.COMPLETED.value

    # Further events are rejected with SessionTerminalError
    with pytest.raises(SessionTerminalError):
        await orchestrator.dispatch_event("sess-stop-001", SessionEvent.LOAD_COMPLETED)
