"""Unit tests for transport-neutral sequencing, idempotency, and recovery (FR-004, FR-005)."""

import time
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.contracts.device import (
    CommandType,
    DeviceAck,
    DeviceCommand,
    DeviceEnvelope,
    EnvelopeType,
)
from app.device_protocol.reason_codes import ProtocolReasonCode
from app.device_protocol.recovery import ProtocolRecoveryManager
from app.device_protocol.sequencing import ProtocolSequencer
from app.persistence.database import get_engine, get_session_maker
from app.persistence.models import Base
from app.persistence.repositories import (
    ProtocolRepository,
    SessionRepository,
)
from app.persistence.seed import seed_minimal_database


@pytest.fixture
async def isolated_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = get_session_maker(engine)
    async with session_maker() as session:
        await seed_minimal_database(session)
        await session.commit()
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_sequencer_monotonic_and_duplicate_detection(
    isolated_session: AsyncSession,
) -> None:
    """Acceptance Criterion 1: Monotonic sequence enforced, duplicates rejected (FR-004)."""
    session_repo = SessionRepository(isolated_session)
    protocol_repo = ProtocolRepository(isolated_session)
    sequencer = ProtocolSequencer(protocol_repo=protocol_repo, session_repo=session_repo)

    sess = await session_repo.create_session(
        device_id="dev-demo-001",
        child_id="child-demo-001",
        curriculum_version_id="curr-v1.0",
    )

    env1 = DeviceEnvelope(
        message_id="msg-001",
        session_id=sess.id,
        seq=1,
        timestamp_ms=int(time.time() * 1000),
        type=EnvelopeType.EVENT,
    )

    # 1. First message with sequence 1 accepted
    res1 = await sequencer.validate_and_record_inbound(env1)
    assert res1.valid is True
    assert res1.reason_code == ProtocolReasonCode.ACCEPTED

    # 2. Duplicate message_id rejected
    res_dup = await sequencer.validate_and_record_inbound(env1)
    assert res_dup.valid is False
    assert res_dup.is_duplicate is True
    assert res_dup.reason_code == ProtocolReasonCode.DUPLICATE_MESSAGE

    # 3. Out of order sequence (seq=1 again with new message_id)
    env1_alt = DeviceEnvelope(
        message_id="msg-002",
        session_id=sess.id,
        seq=1,
        timestamp_ms=int(time.time() * 1000),
        type=EnvelopeType.EVENT,
    )
    res_ooo = await sequencer.validate_and_record_inbound(env1_alt)
    assert res_ooo.valid is False
    assert res_ooo.is_out_of_order is True
    assert res_ooo.reason_code == ProtocolReasonCode.OUT_OF_ORDER_SEQUENCE

    # 4. Sequence gap (seq=3 when last was 1)
    env3 = DeviceEnvelope(
        message_id="msg-003",
        session_id=sess.id,
        seq=3,
        timestamp_ms=int(time.time() * 1000),
        type=EnvelopeType.EVENT,
    )
    res_gap = await sequencer.validate_and_record_inbound(env3)
    assert res_gap.valid is False
    assert res_gap.reason_code == ProtocolReasonCode.SEQUENCE_GAP

    # 5. Valid in-order sequence 2 accepted
    env2 = DeviceEnvelope(
        message_id="msg-004",
        session_id=sess.id,
        seq=2,
        timestamp_ms=int(time.time() * 1000),
        type=EnvelopeType.EVENT,
    )
    res2 = await sequencer.validate_and_record_inbound(env2)
    assert res2.valid is True
    assert res2.reason_code == ProtocolReasonCode.ACCEPTED


@pytest.mark.asyncio
async def test_sequencer_stale_and_version_checks(
    isolated_session: AsyncSession,
) -> None:
    """Acceptance Criterion 4: Stale state version and protocol checks (API-001, ADR-003)."""
    session_repo = SessionRepository(isolated_session)
    protocol_repo = ProtocolRepository(isolated_session)
    sequencer = ProtocolSequencer(protocol_repo=protocol_repo, session_repo=session_repo)

    sess = await session_repo.create_session(
        device_id="dev-demo-001",
        child_id="child-demo-001",
        curriculum_version_id="curr-v1.0",
    )

    # Invalid protocol version
    env_bad_ver = DeviceEnvelope(
        schema_version="2.0",  # Unsupported
        message_id="msg-bad",
        session_id=sess.id,
        seq=1,
        timestamp_ms=int(time.time() * 1000),
        type=EnvelopeType.EVENT,
    )
    res_ver = await sequencer.validate_and_record_inbound(env_bad_ver)
    assert res_ver.valid is False
    assert res_ver.reason_code == ProtocolReasonCode.INVALID_PROTOCOL_VERSION

    # Stale state_version check
    env_stale = DeviceEnvelope(
        message_id="msg-stale",
        session_id=sess.id,
        seq=1,
        timestamp_ms=int(time.time() * 1000),
        type=EnvelopeType.EVENT,
    )
    # Session is at state_version 1, but expected 99
    res_stale = await sequencer.validate_and_record_inbound(env_stale, expected_state_version=99)
    assert res_stale.valid is False
    assert res_stale.is_stale is True
    assert res_stale.reason_code == ProtocolReasonCode.STALE_STATE_VERSION


@pytest.mark.asyncio
async def test_recovery_bounded_resend_and_ack(
    isolated_session: AsyncSession,
) -> None:
    """Acceptance Criterion 3: Exactly one bounded resend rule durably tracked (FR-005)."""
    session_repo = SessionRepository(isolated_session)
    protocol_repo = ProtocolRepository(isolated_session)
    recovery = ProtocolRecoveryManager(
        protocol_repo=protocol_repo, session_repo=session_repo, max_resends=1
    )

    sess = await session_repo.create_session(
        device_id="dev-demo-001",
        child_id="child-demo-001",
        curriculum_version_id="curr-v1.0",
    )

    cmd_envelope = DeviceEnvelope(
        message_id="cmd-play-001",
        session_id=sess.id,
        seq=1,
        timestamp_ms=int(time.time() * 1000),
        type=EnvelopeType.COMMAND,
        command=DeviceCommand(command_type=CommandType.SPEAK, parameters={"asset_id": "prompt_1"}),
    )

    # Record outbound command
    await recovery.record_sent_command(sess.id, cmd_envelope)

    # 1. First resume: client reconnected without ACK -> command resent (resend_count = 1)
    resume1 = await recovery.compute_resume(sess.id)
    assert resume1.status == "RESUMED"
    assert resume1.pending_command is not None
    assert resume1.resend_count == 1
    assert resume1.pending_command.command is not None
    assert resume1.pending_command.command.parameters["is_resend"] is True

    # 2. Second resume: client reconnected again without ACK -> bounded resend limit (max=1) reached
    resume2 = await recovery.compute_resume(sess.id)
    assert resume2.status == "RESUMED"
    assert resume2.pending_command is None  # Does NOT resend again!
    assert resume2.reason_code == ProtocolReasonCode.MAX_RESENDS_EXCEEDED

    # 3. Client delivers ACK for the original command
    ack_envelope = DeviceEnvelope(
        message_id="ack-client-001",
        session_id=sess.id,
        seq=2,
        timestamp_ms=int(time.time() * 1000),
        type=EnvelopeType.ACK,
        ack=DeviceAck(original_message_id="cmd-play-001", original_seq=1, status="OK"),
    )
    ack_res = await recovery.process_ack(sess.id, ack_envelope)
    assert ack_res.valid is True
    assert ack_res.reason_code == ProtocolReasonCode.ACCEPTED

    # 4. Third resume after ACK: clean resume with no pending command
    resume3 = await recovery.compute_resume(sess.id)
    assert resume3.status == "RESUMED"
    assert resume3.pending_command is None
    assert resume3.resend_count == 0
    assert resume3.reason_code == ProtocolReasonCode.ACCEPTED
