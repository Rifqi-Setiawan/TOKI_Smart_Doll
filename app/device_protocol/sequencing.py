"""Transport-neutral protocol sequencing, validation, and idempotency (FR-004, SEC-004)."""

from app.contracts.device import DeviceEnvelope
from app.device_protocol.models import ProtocolValidationResult
from app.device_protocol.reason_codes import ProtocolReasonCode
from app.persistence.repositories import (
    NotFoundError,
    ProtocolRepository,
    SessionRepository,
)


class ProtocolSequencer:
    """Validates protocol version, message ordering, deduplication, and session expiry."""

    def __init__(
        self,
        protocol_repo: ProtocolRepository,
        session_repo: SessionRepository,
        session_ttl_s: int = 1800,
    ) -> None:
        self.protocol_repo = protocol_repo
        self.session_repo = session_repo
        self.session_ttl_s = session_ttl_s

    async def validate_and_record_inbound(
        self,
        envelope: DeviceEnvelope,
        expected_state_version: int | None = None,
        expected_turn_id: str | None = None,
    ) -> ProtocolValidationResult:
        """Validate an incoming envelope against protocol invariants and record sequence.

        Enforces:
        - Strict protocol version check ("1.0") (API-001).
        - Rejection of unknown or expired sessions (SEC-004).
        - Rejection of events on closed/terminal sessions.
        - Message idempotency and deduplication (FR-004, DATA-004).
        - Strictly monotonic sequence numbering with gap and reorder detection (FR-004).
        - Stale callback detection (FR-002, ADR-003).
        """
        # 1. Protocol version validation
        if envelope.schema_version != "1.0":
            return ProtocolValidationResult(
                valid=False,
                reason_code=ProtocolReasonCode.INVALID_PROTOCOL_VERSION,
                message=f"Unsupported protocol version '{envelope.schema_version}', expected '1.0'",
            )

        # 2. Session existence and status validation
        try:
            session = await self.session_repo.get_session(envelope.session_id)
        except NotFoundError:
            return ProtocolValidationResult(
                valid=False,
                reason_code=ProtocolReasonCode.SESSION_NOT_FOUND,
                message=f"Session '{envelope.session_id}' not found",
            )

        # Terminal state check
        if session.state in ("COMPLETED", "SESSION_ABORTED"):
            return ProtocolValidationResult(
                valid=False,
                reason_code=ProtocolReasonCode.SESSION_TERMINAL,
                message=f"Session '{envelope.session_id}' is in terminal state '{session.state}'",
            )

        # Expiry check
        if await self.protocol_repo.is_session_expired(envelope.session_id):
            return ProtocolValidationResult(
                valid=False,
                reason_code=ProtocolReasonCode.SESSION_EXPIRED,
                message=f"Session '{envelope.session_id}' has expired past TTL window",
            )

        # 3. Idempotency & duplicate message check (FR-004, SEC-004)
        if await self.protocol_repo.is_message_processed(envelope.session_id, envelope.message_id):
            return ProtocolValidationResult(
                valid=False,
                reason_code=ProtocolReasonCode.DUPLICATE_MESSAGE,
                message=f"Duplicate message_id '{envelope.message_id}' already processed",
                is_duplicate=True,
            )

        # 4. Stale state version or turn check (FR-002, ADR-003)
        if expected_state_version is not None:
            if session.state_version != expected_state_version:
                return ProtocolValidationResult(
                    valid=False,
                    reason_code=ProtocolReasonCode.STALE_STATE_VERSION,
                    message=(
                        f"Stale state_version: expected {session.state_version}, "
                        f"got {expected_state_version}"
                    ),
                    is_stale=True,
                )

        if expected_turn_id is not None and envelope.turn_id:
            if envelope.turn_id != expected_turn_id:
                return ProtocolValidationResult(
                    valid=False,
                    reason_code=ProtocolReasonCode.STALE_TURN,
                    message=(
                        f"Stale turn_id: active is '{expected_turn_id}', "
                        f"envelope carried '{envelope.turn_id}'"
                    ),
                    is_stale=True,
                )

        # 5. Monotonic sequence ordering and gap detection (FR-004)
        cursor = await self.protocol_repo.get_or_create_cursor(
            envelope.session_id, self.session_ttl_s
        )

        if envelope.seq <= cursor.last_inbound_seq:
            return ProtocolValidationResult(
                valid=False,
                reason_code=ProtocolReasonCode.OUT_OF_ORDER_SEQUENCE,
                message=(
                    f"Out of order sequence: got {envelope.seq}, "
                    f"last processed was {cursor.last_inbound_seq}"
                ),
                is_out_of_order=True,
            )

        if envelope.seq > cursor.last_inbound_seq + 1:
            return ProtocolValidationResult(
                valid=False,
                reason_code=ProtocolReasonCode.SEQUENCE_GAP,
                message=(
                    f"Sequence gap detected: expected {cursor.last_inbound_seq + 1}, "
                    f"got {envelope.seq}"
                ),
            )

        # 6. Record accepted inbound sequence and message_id atomically in DB
        await self.protocol_repo.record_inbound(
            session_id=envelope.session_id,
            message_id=envelope.message_id,
            sequence_number=envelope.seq,
            session_ttl_s=self.session_ttl_s,
        )

        return ProtocolValidationResult(
            valid=True,
            reason_code=ProtocolReasonCode.ACCEPTED,
            message="Message accepted and sequenced durably",
        )
