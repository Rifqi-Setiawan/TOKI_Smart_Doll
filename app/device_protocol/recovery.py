"""Transport-neutral protocol acknowledgment and reconnection recovery (FR-005, REL-001)."""

import time
from uuid import uuid4

from app.contracts.device import (
    CommandType,
    DeviceCommand,
    DeviceEnvelope,
    EnvelopeType,
)
from app.device_protocol.models import ProtocolValidationResult, ResumeResponse
from app.device_protocol.reason_codes import ProtocolReasonCode
from app.persistence.repositories import (
    NotFoundError,
    ProtocolRepository,
    SessionRepository,
)


class ProtocolRecoveryManager:
    """Manages outbound command acknowledgments, durable state cursor, and reconnect resume."""

    def __init__(
        self,
        protocol_repo: ProtocolRepository,
        session_repo: SessionRepository,
        max_resends: int = 1,  # Exactly one bounded resend rule (TASK-008, FR-005)
    ) -> None:
        self.protocol_repo = protocol_repo
        self.session_repo = session_repo
        self.max_resends = max_resends

    async def record_sent_command(
        self,
        session_id: str,
        command_envelope: DeviceEnvelope,
    ) -> None:
        """Durably record sent outbound command for acknowledgment and recovery tracking."""
        cmd = command_envelope.command
        cmd_type = (
            cmd.command_type.value
            if cmd and hasattr(cmd.command_type, "value")
            else (cmd.command_type if cmd else "SPEAK")
        )
        cmd_payload = cmd.parameters if cmd else {}

        await self.protocol_repo.record_outbound(
            session_id=session_id,
            command_id=command_envelope.message_id,
            command_type=str(cmd_type),
            command_payload=cmd_payload,
            sequence_number=command_envelope.seq,
        )

    async def process_ack(
        self,
        session_id: str,
        ack_envelope: DeviceEnvelope,
    ) -> ProtocolValidationResult:
        """Process incoming client acknowledgment and clear un-ACKed command state."""
        if ack_envelope.type != EnvelopeType.ACK or not ack_envelope.ack:
            return ProtocolValidationResult(
                valid=False,
                reason_code=ProtocolReasonCode.UNEXPECTED_ENVELOPE_TYPE,
                message="Expected EnvelopeType.ACK with valid DeviceAck payload",
            )

        cursor = await self.protocol_repo.get_or_create_cursor(session_id)
        acked_msg_id = ack_envelope.ack.original_message_id

        # Check duplicate ACK
        if cursor.last_acked_message_id == acked_msg_id:
            return ProtocolValidationResult(
                valid=True,
                reason_code=ProtocolReasonCode.DUPLICATE_MESSAGE,
                message=f"ACK for message_id '{acked_msg_id}' already processed",
                is_duplicate=True,
            )

        # Verify ACK matches last sent command
        if cursor.last_sent_command_id and cursor.last_sent_command_id != acked_msg_id:
            return ProtocolValidationResult(
                valid=False,
                reason_code=ProtocolReasonCode.ACK_MISMATCH,
                message=(
                    f"ACK message_id mismatch: expected '{cursor.last_sent_command_id}', "
                    f"got '{acked_msg_id}'"
                ),
            )

        # Durably record ACK
        await self.protocol_repo.record_ack(session_id, acked_msg_id)

        return ProtocolValidationResult(
            valid=True,
            reason_code=ProtocolReasonCode.ACCEPTED,
            message="Client acknowledgment recorded durably",
        )

    async def compute_resume(self, session_id: str) -> ResumeResponse:
        """Compute the recovery state and pending command after client reconnect or restart.

        Enforces:
        - Resuming from the last durable acknowledged state after process restart (FR-005).
        - Exactly one bounded resend rule; does not resend repeatedly (FR-005).
        - Terminal and expired session handling.
        """
        try:
            session = await self.session_repo.get_session(session_id)
        except NotFoundError:
            return ResumeResponse(
                session_id=session_id,
                status="EXPIRED",
                resumed_state="UNKNOWN",
                state_version=0,
                turn_number=0,
                reason_code=ProtocolReasonCode.SESSION_NOT_FOUND,
            )

        # 1. Terminal session check
        if session.state in ("COMPLETED", "SESSION_ABORTED"):
            return ResumeResponse(
                session_id=session_id,
                status="TERMINAL",
                resumed_state=session.state,
                state_version=session.state_version,
                turn_number=session.current_turn_number,
                reason_code=ProtocolReasonCode.SESSION_TERMINAL,
            )

        # 2. Expiry check
        if await self.protocol_repo.is_session_expired(session_id):
            return ResumeResponse(
                session_id=session_id,
                status="EXPIRED",
                resumed_state=session.state,
                state_version=session.state_version,
                turn_number=session.current_turn_number,
                reason_code=ProtocolReasonCode.SESSION_EXPIRED,
            )

        cursor = await self.protocol_repo.get_or_create_cursor(session_id)

        # 3. Check for unacknowledged outbound command
        unacked = (
            cursor.last_sent_command_id is not None
            and cursor.last_acked_message_id != cursor.last_sent_command_id
        )

        if unacked:
            # Check bounded resend limit (FR-005)
            if cursor.resend_count < self.max_resends:
                new_resend_count = await self.protocol_repo.increment_resend(session_id)

                # Reconstruct un-ACKed command with resend metadata
                cmd_type_str = cursor.last_sent_command_type or "SPEAK"
                try:
                    resend_cmd_type = CommandType(cmd_type_str)
                except ValueError:
                    resend_cmd_type = CommandType.SPEAK

                resend_cmd = DeviceCommand(
                    command_type=resend_cmd_type,
                    parameters={
                        **(cursor.last_sent_command_payload or {}),
                        "is_resend": True,
                        "resend_count": new_resend_count,
                    },
                )
                pending_envelope = DeviceEnvelope(
                    message_id=str(uuid4()),
                    session_id=session_id,
                    turn_id=f"turn-{session.current_turn_number}",
                    seq=cursor.last_outbound_seq + 1,
                    timestamp_ms=int(time.time() * 1000),
                    type=EnvelopeType.COMMAND,
                    command=resend_cmd,
                )

                return ResumeResponse(
                    session_id=session_id,
                    status="RESUMED",
                    resumed_state=session.state,
                    state_version=session.state_version,
                    turn_number=session.current_turn_number,
                    pending_command=pending_envelope,
                    reason_code=ProtocolReasonCode.ACCEPTED,
                    resend_count=new_resend_count,
                )
            else:
                # Bounded resend limit exceeded: do NOT resend again (TASK-008 constraint)
                return ResumeResponse(
                    session_id=session_id,
                    status="RESUMED",
                    resumed_state=session.state,
                    state_version=session.state_version,
                    turn_number=session.current_turn_number,
                    pending_command=None,
                    reason_code=ProtocolReasonCode.MAX_RESENDS_EXCEEDED,
                    resend_count=cursor.resend_count,
                )

        # 4. No unacknowledged command: resume from last durable state
        return ResumeResponse(
            session_id=session_id,
            status="RESUMED",
            resumed_state=session.state,
            state_version=session.state_version,
            turn_number=session.current_turn_number,
            pending_command=None,
            reason_code=ProtocolReasonCode.ACCEPTED,
            resend_count=0,
        )
