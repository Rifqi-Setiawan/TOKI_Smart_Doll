"""Integration tests for protocol fault matrix and restart recovery (FR-004, FR-005)."""

import time
from collections.abc import AsyncGenerator
from typing import Any

import pytest

from app.contracts.device import (
    CodecType,
    CommandType,
    DeviceCommand,
    DeviceEnvelope,
    EnvelopeType,
)
from app.device_protocol.reason_codes import ProtocolReasonCode
from app.device_protocol.recovery import ProtocolRecoveryManager
from app.device_protocol.sequencing import ProtocolSequencer
from app.persistence.database import get_engine, get_session_maker
from app.persistence.models import Base, utc_now
from app.persistence.repositories import (
    ProtocolRepository,
    SessionRepository,
)
from app.persistence.seed import seed_minimal_database
from simulators.device_simulator import DeviceSimulator


@pytest.fixture
async def shared_db() -> AsyncGenerator[tuple[Any, Any], None]:
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
async def test_fault_matrix_duplicate_and_out_of_order(
    shared_db: tuple[Any, Any],
) -> None:
    """Acceptance Criterion 1 & 5: Fault matrix exercises duplicates and out-of-order rejections."""
    engine, session_maker = shared_db

    async with session_maker() as session:
        session_repo = SessionRepository(session)
        protocol_repo = ProtocolRepository(session)
        sequencer = ProtocolSequencer(protocol_repo=protocol_repo, session_repo=session_repo)

        db_sess = await session_repo.create_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )
        session_id = db_sess.id

        simulator = DeviceSimulator(device_serial="TOKI-DEMO-001")

        # 1. Normal handshake (seq=1)
        handshake_env = simulator.create_handshake_envelope(session_id=session_id)
        assert handshake_env.seq == 1
        res1 = await sequencer.validate_and_record_inbound(handshake_env)
        assert res1.valid is True
        assert res1.reason_code == ProtocolReasonCode.ACCEPTED

        # 2. FAULT: Network duplicate delivery of handshake
        res_dup = await sequencer.validate_and_record_inbound(handshake_env)
        assert res_dup.valid is False
        assert res_dup.is_duplicate is True
        assert res_dup.reason_code == ProtocolReasonCode.DUPLICATE_MESSAGE

        # 3. Audio chunk (seq=2)
        chunk_env = simulator.create_audio_chunk_envelope(
            session_id=session_id,
            turn_id="turn-1",
            chunk_index=0,
            audio_bytes=b"opus-encoded-voice-data",
            codec=CodecType.OPUS,
        )
        assert chunk_env.seq == 2
        res2 = await sequencer.validate_and_record_inbound(chunk_env)
        assert res2.valid is True
        assert res2.reason_code == ProtocolReasonCode.ACCEPTED

        # 4. FAULT: Packet reordering - client emits seq=4 before seq=3 arrives
        env4_premature = DeviceEnvelope(
            message_id="msg-turn-event-premature",
            session_id=session_id,
            seq=4,  # Gap: expected 3
            timestamp_ms=int(time.time() * 1000),
            type=EnvelopeType.EVENT,
        )
        res_gap = await sequencer.validate_and_record_inbound(env4_premature)
        assert res_gap.valid is False
        assert res_gap.reason_code == ProtocolReasonCode.SEQUENCE_GAP

        # 5. Correct in-order packet arrives (seq=3)
        env3 = DeviceEnvelope(
            message_id="msg-seq-3",
            session_id=session_id,
            seq=3,
            timestamp_ms=int(time.time() * 1000),
            type=EnvelopeType.EVENT,
        )
        res3 = await sequencer.validate_and_record_inbound(env3)
        assert res3.valid is True
        assert res3.reason_code == ProtocolReasonCode.ACCEPTED


@pytest.mark.asyncio
async def test_fault_matrix_restart_and_durable_resume(
    shared_db: tuple[Any, Any],
) -> None:
    """Acceptance Criterion 2: Server restart recovery from durable DB state (FR-005)."""
    engine, session_maker = shared_db
    session_id: str

    # PHASE 1: Run interaction before crash
    async with session_maker() as session:
        session_repo = SessionRepository(session)
        protocol_repo = ProtocolRepository(session)
        recovery = ProtocolRecoveryManager(protocol_repo=protocol_repo, session_repo=session_repo)

        db_sess = await session_repo.create_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )
        session_id = db_sess.id

        # Advance state to PROMPTING
        await session_repo.advance_state(
            session_id=session_id,
            expected_state_version=1,
            new_state="PROMPTING",
            new_turn_number=1,
        )

        # Server dispatches play_prompt command to device
        command_env = DeviceEnvelope(
            message_id="cmd-unacked-prompt-001",
            session_id=session_id,
            turn_id="turn-1",
            seq=1,
            timestamp_ms=int(time.time() * 1000),
            type=EnvelopeType.COMMAND,
            command=DeviceCommand(
                command_type=CommandType.SPEAK,
                parameters={"asset_id": "audio_mata_001", "text": "Sebutkan anggota tubuh!"},
            ),
        )
        await recovery.record_sent_command(session_id, command_env)
        await session.commit()

    # PHASE 2: SIMULATE PROCESS CRASH & FRESH RESTART
    # All in-memory objects from Phase 1 are destroyed.
    # Instantiate completely fresh repositories and managers from the DB.
    async with session_maker() as fresh_session:
        fresh_session_repo = SessionRepository(fresh_session)
        fresh_protocol_repo = ProtocolRepository(fresh_session)
        fresh_recovery = ProtocolRecoveryManager(
            protocol_repo=fresh_protocol_repo,
            session_repo=fresh_session_repo,
            max_resends=1,
        )

        # Client reconnects after crash!
        resume = await fresh_recovery.compute_resume(session_id)
        assert resume.status == "RESUMED"
        assert resume.resumed_state == "PROMPTING"
        assert resume.state_version == 2
        assert resume.turn_number == 1
        assert resume.pending_command is not None
        assert resume.resend_count == 1
        assert resume.pending_command.command is not None
        assert resume.pending_command.command.parameters["asset_id"] == "audio_mata_001"
        assert resume.pending_command.command.parameters["is_resend"] is True

        # Client delivers ACK for the resent command
        simulator = DeviceSimulator()
        ack_env = simulator.create_ack_envelope(
            session_id=session_id,
            acked_message_id="cmd-unacked-prompt-001",
            status="OK",
        )
        ack_res = await fresh_recovery.process_ack(session_id, ack_env)
        assert ack_res.valid is True
        assert ack_res.reason_code == ProtocolReasonCode.ACCEPTED

        # Next resume has no pending commands
        resume_post_ack = await fresh_recovery.compute_resume(session_id)
        assert resume_post_ack.status == "RESUMED"
        assert resume_post_ack.pending_command is None
        assert resume_post_ack.resend_count == 0


@pytest.mark.asyncio
async def test_fault_matrix_session_expiry(
    shared_db: tuple[Any, Any],
) -> None:
    """Acceptance Criterion 5: Expired session halts further message processing (SEC-004)."""
    engine, session_maker = shared_db

    async with session_maker() as session:
        session_repo = SessionRepository(session)
        protocol_repo = ProtocolRepository(session)
        sequencer = ProtocolSequencer(
            protocol_repo=protocol_repo, session_repo=session_repo, session_ttl_s=1
        )
        recovery = ProtocolRecoveryManager(protocol_repo=protocol_repo, session_repo=session_repo)

        db_sess = await session_repo.create_session(
            device_id="dev-demo-001",
            child_id="child-demo-001",
            curriculum_version_id="curr-v1.0",
        )
        session_id = db_sess.id

        # Initialize cursor and manually expire it
        cursor = await protocol_repo.get_or_create_cursor(session_id)
        cursor.session_expires_at = utc_now()  # Expired right now
        await session.flush()

        # Inbound message rejected as expired
        env = DeviceEnvelope(
            message_id="msg-expired",
            session_id=session_id,
            seq=1,
            timestamp_ms=int(time.time() * 1000),
            type=EnvelopeType.EVENT,
        )
        res = await sequencer.validate_and_record_inbound(env)
        assert res.valid is False
        assert res.reason_code == ProtocolReasonCode.SESSION_EXPIRED

        # Resume reports EXPIRED
        resume = await recovery.compute_resume(session_id)
        assert resume.status == "EXPIRED"
        assert resume.reason_code == ProtocolReasonCode.SESSION_EXPIRED
