"""Unit tests for authoritative persistence, optimistic concurrency, and immutability.
Requirements: DATA-001–005, DATA-007–010.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.database import Base
from app.persistence.models import (
    Turn,
    utc_now,
)
from app.persistence.repositories import (
    AttemptRepository,
    ConsentRepository,
    ConsentRevokedError,
    CurriculumRepository,
    DuplicateKeyError,
    EventOutboxRepository,
    ImmutabilityViolationError,
    OptimisticLockError,
    SessionRepository,
)
from app.persistence.seed import seed_minimal_database


@pytest.mark.asyncio
async def test_minimal_database_seeding(db_session: AsyncSession) -> None:
    """Verify minimal database seeding completes and creates test/demo twin baseline."""
    seed_result = await seed_minimal_database(db_session)
    assert seed_result["child_id"] == "child-demo-001"
    assert seed_result["device_serial"] == "TOKI-DEMO-001"
    assert seed_result["curriculum_version_token"] == "curriculum-v1.0"


@pytest.mark.asyncio
async def test_optimistic_concurrency_state_version(db_session: AsyncSession) -> None:
    """DATA-002: Session updates use optimistic concurrency on state_version.

    Stale/concurrent updates must fail without mutating data.
    """
    await seed_minimal_database(db_session)
    session_repo = SessionRepository(db_session)

    # Create active session (initial state_version = 1)
    new_sess = await session_repo.create_session(
        device_id="dev-demo-001",
        child_id="child-demo-001",
        curriculum_version_id="curr-v1.0",
    )
    assert new_sess.state == "INITIALIZING"
    assert new_sess.state_version == 1

    # First update: state_version 1 -> 2
    v2 = await session_repo.advance_state(
        session_id=new_sess.id,
        expected_state_version=1,
        new_state="IN_PROGRESS",
        new_turn_number=1,
    )
    assert v2 == 2

    # Second concurrent / stale update trying to use state_version 1 again
    with pytest.raises(OptimisticLockError, match="DATA-002 violation"):
        await session_repo.advance_state(
            session_id=new_sess.id,
            expected_state_version=1,
            new_state="RESOLVED",
        )

    # Verify session in DB remains at state_version 2, not mutated by stale call
    await db_session.refresh(new_sess)
    assert new_sess.state_version == 2
    assert new_sess.state == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_idempotent_attempt_prevents_duplicate_message(
    db_session: AsyncSession,
) -> None:
    """DATA-004: Replayed or duplicate message_id cannot create duplicate attempt."""
    await seed_minimal_database(db_session)
    session_repo = SessionRepository(db_session)
    attempt_repo = AttemptRepository(db_session)

    sess = await session_repo.create_session(
        device_id="dev-demo-001",
        child_id="child-demo-001",
        curriculum_version_id="curr-v1.0",
    )
    turn = Turn(
        id="turn-test-001",
        session_id=sess.id,
        turn_number=1,
        item_token="body_parts_mata",
        state_version=1,
        status="PENDING",
        created_at=utc_now(),
    )
    db_session.add(turn)
    await db_session.flush()

    # First attempt: succeeds
    att1 = await attempt_repo.record_attempt(
        turn_id=turn.id,
        message_id="msg-unique-12345",
        is_correct=True,
        reason_code="EXACT_MATCH",
        spoken_text="mata",
    )
    assert att1.message_id == "msg-unique-12345"

    # Second attempt with same message_id: must raise DuplicateKeyError
    with pytest.raises(DuplicateKeyError, match="DATA-004 violation"):
        await attempt_repo.record_attempt(
            turn_id=turn.id,
            message_id="msg-unique-12345",
            is_correct=True,
            reason_code="EXACT_MATCH",
            spoken_text="mata",
        )


@pytest.mark.asyncio
async def test_approved_curriculum_immutability(db_session: AsyncSession) -> None:
    """DATA-003: Approved curriculum versions are immutable."""
    await seed_minimal_database(db_session)
    curriculum_repo = CurriculumRepository(db_session)

    # Attempting to mutate an APPROVED curriculum item must raise ImmutabilityViolationError
    with pytest.raises(ImmutabilityViolationError, match="DATA-003 violation"):
        await curriculum_repo.update_item_prompt(
            curriculum_version_id="curr-v1.0",
            item_token="body_parts_mata",
            new_prompt="Modified prompt without version bump",
        )


@pytest.mark.asyncio
async def test_domain_events_and_atomic_outbox(db_session: AsyncSession) -> None:
    """DATA-005 & ADR-012: Domain events are append-only; outbox committed in same transaction."""
    event_repo = EventOutboxRepository(db_session)

    domain_event, outbox_event = await event_repo.record_event_and_outbox(
        session_id="sess-test-999",
        event_sequence=1,
        event_type="SESSION_STARTED",
        payload={"state": "IN_PROGRESS"},
        outbox_topic="toki.events.session",
    )

    assert domain_event.id is not None
    assert outbox_event.event_id == domain_event.id
    assert outbox_event.status == "PENDING"

    # Attempt to delete domain event must fail (append-only enforcement)
    with pytest.raises(ImmutabilityViolationError, match="DATA-005 violation"):
        await event_repo.delete_event(domain_event.id)


@pytest.mark.asyncio
async def test_consent_revocation_blocks_new_session(db_session: AsyncSession) -> None:
    """DATA-010: Guardian consent revocation prevents starting new sessions."""
    await seed_minimal_database(db_session)
    consent_repo = ConsentRepository(db_session)
    session_repo = SessionRepository(db_session)

    # Active consent allows session creation
    sess = await session_repo.create_session(
        device_id="dev-demo-001",
        child_id="child-demo-001",
        curriculum_version_id="curr-v1.0",
    )
    assert sess.id is not None

    # Revoke consent
    await consent_repo.revoke_consent(child_id="child-demo-001")
    assert not await consent_repo.has_active_consent(child_id="child-demo-001")

    # Subsequent session creation must be blocked
    with pytest.raises(ConsentRevokedError, match="DATA-010 violation"):
        await session_repo.create_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )


def test_child_privacy_minimization_audit() -> None:
    """DATA-006, DATA-008, ADR-013: Normal schema contains NO retained raw media or exact DOB."""
    for table_name, table in Base.metadata.tables.items():
        column_names = [col.name.lower() for col in table.columns]

        # 1. No exact DOB column allowed (only age_band per DATA-008)
        assert "dob" not in column_names, f"Table {table_name} contains forbidden DOB column"
        assert (
            "date_of_birth" not in column_names
        ), f"Table {table_name} contains forbidden date_of_birth column"
        assert (
            "birth_date" not in column_names
        ), f"Table {table_name} contains forbidden birth_date column"

        # 2. No raw audio / video / frame media storage in normal schema (DATA-006, ADR-013)
        assert (
            "raw_audio" not in column_names
        ), f"Table {table_name} contains forbidden raw_audio column"
        assert (
            "audio_bytes" not in column_names
        ), f"Table {table_name} contains forbidden audio_bytes column"
        assert (
            "raw_frame" not in column_names
        ), f"Table {table_name} contains forbidden raw_frame column"
        assert (
            "image_bytes" not in column_names
        ), f"Table {table_name} contains forbidden image_bytes column"
        assert (
            "video_bytes" not in column_names
        ), f"Table {table_name} contains forbidden video_bytes column"

    # Inspect Children table specifically
    child_table = Base.metadata.tables["children"]
    child_cols = [c.name for c in child_table.columns]
    assert "age_band" in child_cols
    assert "pseudonym" in child_cols

    # Inspect Guardians table: plain email is not stored, only email_hash
    guardian_table = Base.metadata.tables["guardians"]
    guard_cols = [c.name for c in guardian_table.columns]
    assert "email" not in guard_cols
    assert "email_hash" in guard_cols
