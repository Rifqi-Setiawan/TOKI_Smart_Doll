"""Tests for device hardware simulator and Flutter mobile simulator (API-001, API-002, SEC-010)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.device import CodecType, EnvelopeType
from simulators.device_simulator import DeviceSimulator
from simulators.flutter_simulator import FlutterSimulator

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "contracts"


def test_device_simulator_handshake_envelope() -> None:
    """Device simulator constructs versioned handshake envelope with monotonic sequence."""
    sim = DeviceSimulator(device_serial="TOKI-SIM-001")
    env = sim.create_handshake_envelope(session_id="sess-001")

    assert env.schema_version == "1.0"
    assert env.session_id == "sess-001"
    assert env.seq == 1
    assert env.type == EnvelopeType.EVENT
    assert env.event is not None
    assert env.event.metadata["action"] == "HANDSHAKE"
    assert env.event.metadata["device_serial"] == "TOKI-SIM-001"

    # Second envelope must have incremented sequence number
    env2 = sim.create_handshake_envelope(session_id="sess-001")
    assert env2.seq == 2


def test_device_simulator_audio_chunk_and_size_limit() -> None:
    """Device simulator constructs audio envelopes and enforces 32KB limit (SEC-003)."""
    sim = DeviceSimulator()

    # Valid chunk (1024 bytes)
    valid_audio = b"\x00" * 1024
    env = sim.create_audio_chunk_envelope(
        session_id="sess-001",
        turn_id="turn-001",
        chunk_index=0,
        audio_bytes=valid_audio,
        codec=CodecType.OPUS,
    )
    assert env.type == EnvelopeType.AUDIO_METADATA
    assert env.audio_meta is not None
    assert env.audio_meta.byte_length == 1024
    assert env.audio_meta.chunk_index == 0

    # Oversized chunk (33KB) must raise ValueError before network transmission
    oversized_audio = b"\x00" * (33 * 1024)
    with pytest.raises(ValueError, match="SEC-003 violation"):
        sim.create_audio_chunk_envelope(
            session_id="sess-001",
            turn_id="turn-001",
            chunk_index=1,
            audio_bytes=oversized_audio,
        )


def test_device_simulator_receives_ack_and_command_fixtures() -> None:
    """Device simulator validates server ACK and Command contracts against frozen fixtures."""
    sim = DeviceSimulator()

    # Feed command extracted from valid envelope fixture
    with open(FIXTURES_DIR / "device_envelope_valid.json", encoding="utf-8") as f:
        env_data = json.load(f)
    cmd = sim.receive_command(env_data["command"])
    assert cmd.command_type.value == "SPEAK"
    assert len(sim.received_commands) == 1

    # Feed ACK data matching DeviceAck contract
    ack_data = {
        "schema_version": "1.0",
        "original_message_id": "msg-123",
        "original_seq": 1,
        "status": "OK",
    }
    ack = sim.receive_ack(ack_data)
    assert ack.status == "OK"
    assert ack.original_seq == 1
    assert len(sim.received_acks) == 1


def test_flutter_simulator_consumes_progress_and_enforces_non_clinical() -> None:
    """Flutter simulator parses valid progress fixtures and rejects clinical claims (SEC-010)."""
    sim = FlutterSimulator()

    # Consume valid progress fixture
    with open(FIXTURES_DIR / "child_progress_valid.json", encoding="utf-8") as f:
        progress_data = json.load(f)
    progress_dto = sim.consume_child_progress(progress_data)
    assert progress_dto.display_name == "Budi"
    assert len(progress_dto.skills) > 0

    # Test rejection of clinical wording in summary parent_tip
    forbidden_summary = {
        "schema_version": "1.0",
        "session_id": "sess-001",
        "duration_minutes": 15,
        "completed_activities": 3,
        "skills_addressed": ["Mengenal Anggota Tubuh"],
        "parent_tip": "Hasil diagnosis menunjukkan perlunya terapi wicara untuk speech delay.",
    }
    with pytest.raises(ValidationError, match="SEC-010 violation"):
        sim.consume_session_summary(forbidden_summary)
