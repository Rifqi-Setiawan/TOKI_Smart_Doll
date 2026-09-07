"""Contract tests for device envelopes, commands, events, and ACKs (API-001, API-002)."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.contracts.device import (
    AudioMetadata,
    AudioSpec,
    CodecType,
    CommandType,
    DeviceAck,
    DeviceCommand,
    DeviceEnvelope,
    DisplayState,
    EnvelopeType,
    GestureType,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "contracts"


def test_device_envelope_valid_fixture():
    """Valid device envelope fixture parses cleanly and preserves types."""
    with open(FIXTURES_DIR / "device_envelope_valid.json", encoding="utf-8") as f:
        data = json.load(f)

    envelope = DeviceEnvelope.model_validate(data)
    assert envelope.schema_version == "1.0"
    assert envelope.type == EnvelopeType.COMMAND
    assert envelope.seq == 1
    assert envelope.command is not None
    assert envelope.command.command_type == CommandType.SPEAK
    assert envelope.command.display == DisplayState.SPEAKING
    assert envelope.command.gesture == GestureType.NOD


def test_device_envelope_invalid_fixture():
    """Invalid device envelope fixture fails validation."""
    with open(FIXTURES_DIR / "device_envelope_invalid.json", encoding="utf-8") as f:
        data = json.load(f)

    with pytest.raises(ValidationError) as exc:
        DeviceEnvelope.model_validate(data)

    errors = str(exc.value)
    assert "seq" in errors or "type" in errors


def test_audio_chunk_limit_enforced():
    """Audio metadata enforces hard limit of 32768 bytes per binary chunk (SEC-003)."""
    spec = AudioSpec(codec=CodecType.PCM_16BIT, sample_rate=16000)

    # Valid chunk size
    valid_meta = AudioMetadata(
        audio_spec=spec,
        chunk_index=0,
        is_final=False,
        byte_length=16000,
    )
    assert valid_meta.byte_length == 16000

    # Oversized chunk size -> must fail validation
    with pytest.raises(ValidationError, match="exceeds max allowed 32768 bytes"):
        AudioMetadata(
            audio_spec=spec,
            chunk_index=0,
            is_final=False,
            byte_length=65536,
        )


def test_unknown_enum_rejection():
    """Unknown commands, events, or envelope types are rejected before policy code (API-001)."""
    with pytest.raises(ValidationError):
        DeviceCommand(command_type="UNSUPPORTED_HACK")

    with pytest.raises(ValidationError):
        DeviceAck(original_message_id="msg-1", original_seq=-1)


def test_extra_fields_forbidden():
    """Extra undeclared fields on boundary contracts are strictly forbidden."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        DeviceCommand.model_validate(
            {"command_type": "SPEAK", "malicious_injected_field": "exploit"}
        )
