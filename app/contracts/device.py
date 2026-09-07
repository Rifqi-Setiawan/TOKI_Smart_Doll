"""Device communication protocol contracts and compact control envelope (API-001, API-002)."""

from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from app.contracts.base import ContractModel


class EnvelopeType(str, Enum):
    """High-level envelope dispatch category."""

    COMMAND = "COMMAND"
    EVENT = "EVENT"
    ACK = "ACK"
    AUDIO_METADATA = "AUDIO_METADATA"


class CommandType(str, Enum):
    """Authoritative commands sent from orchestrator to device client."""

    START_SESSION = "START_SESSION"
    SPEAK = "SPEAK"
    DISPLAY = "DISPLAY"
    GESTURE = "GESTURE"
    CAPTURE_OBJECT = "CAPTURE_OBJECT"
    STOP_SESSION = "STOP_SESSION"


class EventType(str, Enum):
    """Physical and interaction events originating from device."""

    AUDIO_START = "AUDIO_START"
    AUDIO_END = "AUDIO_END"
    BUTTON_PRESSED = "BUTTON_PRESSED"
    WAKE_WORD_DETECTED = "WAKE_WORD_DETECTED"
    ERROR = "ERROR"


class CodecType(str, Enum):
    """Supported device audio codecs."""

    PCM_16BIT = "PCM_16BIT"
    OPUS = "OPUS"
    AAC = "AAC"


class DisplayState(str, Enum):
    """OLED/screen face expression enum."""

    IDLE = "IDLE"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    HAPPY = "HAPPY"
    CURIOUS = "CURIOUS"
    ENCOURAGING = "ENCOURAGING"


class GestureType(str, Enum):
    """Servo/motor physical actuation enum."""

    NOD = "NOD"
    WAVE = "WAVE"
    TILT_HEAD = "TILT_HEAD"
    CELEBRATE = "CELEBRATE"
    RESET = "RESET"


class AudioSpec(ContractModel):
    """Audio streaming negotiation and constraints (API-002, SEC-003)."""

    codec: CodecType = Field(default=CodecType.PCM_16BIT, description="Negotiated audio codec")
    sample_rate: int = Field(default=16000, description="Sample rate in Hz (default 16kHz)")
    channels: int = Field(default=1, description="Number of channels (1 = mono)")
    max_duration_ms: int = Field(default=15000, description="Hard cap on audio turn duration")
    max_chunk_bytes: int = Field(default=32768, description="Hard limit on binary chunk size")


class DeviceAck(ContractModel):
    """Reliable protocol acknowledgement payload (FR-004)."""

    original_message_id: str = Field(description="Message ID being acknowledged")
    original_seq: int = Field(ge=0, description="Sequence number being acknowledged")
    status: str = Field(default="OK", description="'OK' or 'FAILED'")
    error_reason: str | None = Field(default=None, description="Optional error detail")


class DeviceCommand(ContractModel):
    """Typed command sent to device."""

    command_type: CommandType
    audio_asset_id: str | None = Field(default=None, description="Cached audio asset identifier")
    display: DisplayState | None = Field(default=None, description="Expression state")
    gesture: GestureType | None = Field(default=None, description="Physical gesture")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Auxiliary parameters")


class DeviceEvent(ContractModel):
    """Typed event emitted by device."""

    event_type: EventType
    button_id: str | None = Field(default=None, description="Identifier of pressed button")
    error_code: str | None = Field(default=None, description="Hardware error code if error event")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Event telemetry metadata")


class AudioMetadata(ContractModel):
    """Metadata describing a separate binary audio segment or chunk (API-002)."""

    audio_spec: AudioSpec
    chunk_index: int = Field(ge=0, description="Monotonic index of chunk within turn")
    is_final: bool = Field(default=False, description="True if this is final chunk of speech")
    byte_length: int = Field(gt=0, description="Length of associated binary frame in bytes")

    @field_validator("byte_length")
    @classmethod
    def validate_chunk_size(cls, value: int) -> int:
        if value > 32768:
            raise ValueError(f"Chunk size {value} exceeds max allowed 32768 bytes (SEC-003)")
        return value


class DeviceEnvelope(ContractModel):
    """Compact JSON control envelope separated from binary media (API-001, API-002, FR-004)."""

    message_id: str = Field(description="Unique UUID message identifier")
    session_id: str = Field(description="Session correlation identifier")
    turn_id: str | None = Field(default=None, description="Turn correlation identifier")
    seq: int = Field(ge=0, description="Monotonically increasing sequence number")
    timestamp_ms: int = Field(description="UTC timestamp in epoch milliseconds")
    type: EnvelopeType = Field(description="Envelope payload type")
    command: DeviceCommand | None = Field(default=None, description="Command payload")
    event: DeviceEvent | None = Field(default=None, description="Event payload")
    ack: DeviceAck | None = Field(default=None, description="Ack payload")
    audio_meta: AudioMetadata | None = Field(default=None, description="Audio metadata")
