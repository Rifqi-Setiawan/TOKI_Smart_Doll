"""Domain models for protocol validation and session resumption (FR-004, FR-005)."""

from dataclasses import dataclass

from app.contracts.device import DeviceEnvelope
from app.device_protocol.reason_codes import ProtocolReasonCode


@dataclass(frozen=True)
class ProtocolValidationResult:
    """Outcome of inbound sequence and idempotency validation."""

    valid: bool
    reason_code: ProtocolReasonCode
    message: str
    is_duplicate: bool = False
    is_stale: bool = False
    is_out_of_order: bool = False


@dataclass(frozen=True)
class ResumeResponse:
    """Computed state and pending command for client reconnection (FR-005)."""

    session_id: str
    status: str  # "RESUMED", "EXPIRED", "TERMINAL"
    resumed_state: str
    state_version: int
    turn_number: int
    pending_command: DeviceEnvelope | None = None
    reason_code: ProtocolReasonCode = ProtocolReasonCode.ACCEPTED
    resend_count: int = 0
