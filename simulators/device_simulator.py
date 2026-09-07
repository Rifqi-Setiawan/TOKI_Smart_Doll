"""Hardware doll simulator executing versioned envelope exchanges (API-001, API-002, SEC-003)."""

import time
import uuid
from typing import Any

from app.contracts.device import (
    AudioMetadata,
    AudioSpec,
    CodecType,
    DeviceAck,
    DeviceCommand,
    DeviceEnvelope,
    DeviceEvent,
    EnvelopeType,
    EventType,
)


class DeviceSimulator:
    """Simulates physical ESP32 doll client generating envelopes and receiving server commands."""

    def __init__(
        self,
        device_serial: str = "TOKI-SIM-001",
        firmware_version: str = "1.0.0",
    ) -> None:
        self.device_serial = device_serial
        self.firmware_version = firmware_version
        self.sequence_number: int = 0
        self.received_commands: list[DeviceCommand] = []
        self.received_acks: list[DeviceAck] = []

    def _next_sequence(self) -> int:
        self.sequence_number += 1
        return self.sequence_number

    def _now_ms(self) -> int:
        return int(time.time() * 1000)

    def create_handshake_envelope(self, session_id: str) -> DeviceEnvelope:
        """Construct versioned handshake envelope for session negotiation."""
        event = DeviceEvent(
            event_type=EventType.BUTTON_PRESSED,
            metadata={
                "action": "HANDSHAKE",
                "device_serial": self.device_serial,
                "firmware_version": self.firmware_version,
            },
        )
        return DeviceEnvelope(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            seq=self._next_sequence(),
            timestamp_ms=self._now_ms(),
            type=EnvelopeType.EVENT,
            event=event,
        )

    def create_audio_chunk_envelope(
        self,
        session_id: str,
        turn_id: str,
        chunk_index: int,
        audio_bytes: bytes,
        codec: CodecType = CodecType.OPUS,
        sample_rate: int = 16000,
        channels: int = 1,
        is_final: bool = False,
    ) -> DeviceEnvelope:
        """Construct bounded audio chunk envelope, enforcing the 32KB limit (SEC-003)."""
        byte_length = len(audio_bytes)
        if byte_length > 32768:
            raise ValueError(
                f"SEC-003 violation: Audio chunk size {byte_length} exceeds 32KB limit"
            )

        audio_spec = AudioSpec(
            codec=codec,
            sample_rate=sample_rate,
            channels=channels,
        )
        audio_meta = AudioMetadata(
            audio_spec=audio_spec,
            chunk_index=chunk_index,
            is_final=is_final,
            byte_length=byte_length,
        )

        return DeviceEnvelope(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            turn_id=turn_id,
            seq=self._next_sequence(),
            timestamp_ms=self._now_ms(),
            type=EnvelopeType.AUDIO_METADATA,
            audio_meta=audio_meta,
        )

    def receive_ack(self, ack_data: dict[str, Any]) -> DeviceAck:
        """Validate and record received server ACK."""
        ack = DeviceAck.model_validate(ack_data)
        self.received_acks.append(ack)
        return ack

    def receive_command(self, command_data: dict[str, Any]) -> DeviceCommand:
        """Validate and record received server command (LED, gesture, audio play)."""
        cmd = DeviceCommand.model_validate(command_data)
        self.received_commands.append(cmd)
        return cmd

    def create_ack_envelope(
        self,
        session_id: str,
        acked_message_id: str,
        original_seq: int = 1,
        status: str = "OK",
    ) -> DeviceEnvelope:
        """Construct acknowledgment envelope for a received server command."""
        ack = DeviceAck(
            original_message_id=acked_message_id,
            original_seq=original_seq,
            status=status,
        )
        return DeviceEnvelope(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            seq=self._next_sequence(),
            timestamp_ms=self._now_ms(),
            type=EnvelopeType.ACK,
            ack=ack,
        )
