"""Authoritative persistence repositories enforcing domain invariants (DATA-001–005, DATA-010)."""

from datetime import UTC, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import (
    Attempt,
    Consent,
    CurriculumItem,
    CurriculumVersion,
    DomainEvent,
    OutboxEvent,
    ProtocolCursor,
    Session,
    utc_now,
)


class PersistenceError(Exception):
    """Base exception for persistence layer operations."""

    pass


class OptimisticLockError(PersistenceError):
    """Raised when an update fails due to a state_version mismatch (DATA-002)."""

    pass


class DuplicateKeyError(PersistenceError):
    """Raised when an idempotent operation receives an already processed identifier (DATA-004)."""

    pass


class NotFoundError(PersistenceError):
    """Raised when an expected record is not found."""

    pass


class ConsentRevokedError(PersistenceError):
    """Raised when an operation requires active consent but consent is revoked (DATA-010)."""

    pass


class ImmutabilityViolationError(PersistenceError):
    """Raised when mutating an immutable approved version or event (DATA-003, DATA-005)."""

    pass


class ConsentRepository:
    """Guardian consent management and active status checks (DATA-010)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def has_active_consent(self, child_id: str) -> bool:
        """Verify if a child has active granted consent for data processing."""
        stmt = (
            select(Consent)
            .where(
                Consent.child_id == child_id,
                Consent.status == "GRANTED",
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def revoke_consent(self, child_id: str) -> None:
        """Revoke all active consents for a child."""
        stmt = (
            update(Consent)
            .where(Consent.child_id == child_id, Consent.status == "GRANTED")
            .values(status="REVOKED", revoked_at=utc_now())
        )
        await self.session.execute(stmt)
        await self.session.flush()


class SessionRepository:
    """Interactive learning session repository with optimistic concurrency (DATA-002)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(
        self,
        device_id: str,
        child_id: str,
        curriculum_version_id: str,
        session_id: str | None = None,
        initial_state: str = "INITIALIZING",
    ) -> Session:
        """Create a new session, enforcing active consent requirement (DATA-010)."""
        consent_repo = ConsentRepository(self.session)
        if not await consent_repo.has_active_consent(child_id):
            raise ConsentRevokedError(
                f"DATA-010 violation: Cannot start session for child '{child_id}' "
                "without active consent"
            )

        new_session = Session(
            id=session_id or str(uuid4()),
            device_id=device_id,
            child_id=child_id,
            curriculum_version_id=curriculum_version_id,
            state=initial_state,
            state_version=1,
            current_turn_number=0,
            started_at=utc_now(),
        )
        self.session.add(new_session)
        await self.session.flush()
        return new_session

    async def get_session(self, session_id: str) -> Session:
        """Fetch session by ID or raise NotFoundError."""
        stmt = select(Session).where(Session.id == session_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            raise NotFoundError(f"Session '{session_id}' not found")
        return record

    async def advance_state(
        self,
        session_id: str,
        expected_state_version: int,
        new_state: str,
        new_turn_number: int | None = None,
    ) -> int:
        """Atomically advance session state protected by optimistic concurrency (DATA-002).

        Returns the new state_version or raises OptimisticLockError.
        """
        values: dict[str, Any] = {
            "state": new_state,
            "state_version": Session.state_version + 1,
            "updated_at": utc_now(),
        }
        if new_turn_number is not None:
            values["current_turn_number"] = new_turn_number

        stmt = (
            update(Session)
            .where(
                Session.id == session_id,
                Session.state_version == expected_state_version,
            )
            .values(**values)
        )
        result = await self.session.execute(stmt)
        if result.rowcount == 0:
            raise OptimisticLockError(
                f"DATA-002 violation: Concurrent update or stale state_version "
                f"(expected {expected_state_version}) on session '{session_id}'"
            )
        await self.session.flush()
        return expected_state_version + 1


class CurriculumRepository:
    """Immutable approved curriculum access repository (DATA-003)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_version(self, version_token: str) -> CurriculumVersion:
        """Retrieve curriculum version by version token."""
        stmt = select(CurriculumVersion).where(CurriculumVersion.version_token == version_token)
        result = await self.session.execute(stmt)
        version = result.scalar_one_or_none()
        if version is None:
            raise NotFoundError(f"Curriculum version '{version_token}' not found")
        return version

    async def update_item_prompt(
        self,
        curriculum_version_id: str,
        item_token: str,
        new_prompt: str,
    ) -> None:
        """Update a curriculum item prompt only if the curriculum version is DRAFT (DATA-003)."""
        stmt = select(CurriculumVersion).where(CurriculumVersion.id == curriculum_version_id)
        result = await self.session.execute(stmt)
        version = result.scalar_one_or_none()
        if version is None:
            raise NotFoundError(f"Curriculum version id '{curriculum_version_id}' not found")

        if version.status == "APPROVED":
            raise ImmutabilityViolationError(
                f"DATA-003 violation: Approved curriculum version '{version.version_token}' "
                "is immutable"
            )

        update_stmt = (
            update(CurriculumItem)
            .where(
                CurriculumItem.curriculum_version_id == curriculum_version_id,
                CurriculumItem.item_token == item_token,
            )
            .values(prompt_text=new_prompt)
        )
        await self.session.execute(update_stmt)
        await self.session.flush()


class AttemptRepository:
    """Atomic and idempotent attempt persistence (DATA-004)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_attempt(
        self,
        turn_id: str,
        message_id: str,
        is_correct: bool,
        reason_code: str,
        confidence: float | None = None,
        spoken_text: str | None = None,
        assistance_level: str = "NONE",
    ) -> Attempt:
        """Record attempt with uniqueness check on message_id preventing replay (DATA-004)."""
        # Check for existing message_id to prevent duplicates
        stmt = select(Attempt).where(Attempt.message_id == message_id)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise DuplicateKeyError(
                f"DATA-004 violation: Duplicate message_id '{message_id}' already recorded"
            )

        attempt = Attempt(
            turn_id=turn_id,
            message_id=message_id,
            is_correct=is_correct,
            reason_code=reason_code,
            confidence=confidence,
            spoken_text=spoken_text,
            assistance_level=assistance_level,
            created_at=utc_now(),
        )
        self.session.add(attempt)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise DuplicateKeyError(
                f"DATA-004 violation: Duplicate attempt for message_id '{message_id}'"
            ) from exc
        return attempt


class EventOutboxRepository:
    """Append-only domain events and transactional outbox written atomically (DATA-005, ADR-012)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record_event_and_outbox(
        self,
        session_id: str | None,
        event_sequence: int,
        event_type: str,
        payload: dict[str, Any],
        outbox_topic: str,
        privacy_class: str = "OPERATIONAL",
    ) -> tuple[DomainEvent, OutboxEvent]:
        """Atomically append a domain event and outbox row within the same transaction."""
        domain_event = DomainEvent(
            id=str(uuid4()),
            session_id=session_id,
            event_sequence=event_sequence,
            event_type=event_type,
            payload=payload,
            privacy_class=privacy_class,
            created_at=utc_now(),
        )
        self.session.add(domain_event)
        await self.session.flush()

        outbox_event = OutboxEvent(
            id=str(uuid4()),
            event_id=domain_event.id,
            topic=outbox_topic,
            payload=payload,
            status="PENDING",
            retry_count=0,
            created_at=utc_now(),
        )
        self.session.add(outbox_event)
        await self.session.flush()

        return domain_event, outbox_event

    async def delete_event(self, event_id: str) -> None:
        """Explicitly forbid deletion of domain events (DATA-005 immutability)."""
        raise ImmutabilityViolationError(
            f"DATA-005 violation: Domain events are append-only; cannot delete event '{event_id}'"
        )


class ProtocolRepository:
    """Durable sequence, idempotency, and acknowledgment tracking (FR-004, FR-005, SEC-004)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_cursor(
        self,
        session_id: str,
        session_ttl_s: int = 1800,
    ) -> ProtocolCursor:
        """Fetch existing cursor or initialize a new cursor for the session."""
        stmt = select(ProtocolCursor).where(ProtocolCursor.session_id == session_id)
        result = await self.session.execute(stmt)
        cursor = result.scalar_one_or_none()
        if cursor is not None:
            return cursor

        now = utc_now()
        cursor = ProtocolCursor(
            id=str(uuid4()),
            session_id=session_id,
            last_inbound_seq=0,
            last_outbound_seq=0,
            resend_count=0,
            processed_message_ids=[],
            session_expires_at=now + timedelta(seconds=session_ttl_s),
            created_at=now,
        )
        self.session.add(cursor)
        await self.session.flush()
        return cursor

    async def is_message_processed(self, session_id: str, message_id: str) -> bool:
        """Check if message_id has already been processed for replay prevention."""
        stmt = select(ProtocolCursor).where(ProtocolCursor.session_id == session_id)
        result = await self.session.execute(stmt)
        cursor = result.scalar_one_or_none()
        if cursor is None:
            return False
        return message_id in cursor.processed_message_ids

    async def record_inbound(
        self,
        session_id: str,
        message_id: str,
        sequence_number: int,
        session_ttl_s: int = 1800,
    ) -> ProtocolCursor:
        """Record accepted inbound message, advancing sequence and appending message_id."""
        cursor = await self.get_or_create_cursor(session_id, session_ttl_s)
        cursor.last_inbound_seq = sequence_number
        if message_id not in cursor.processed_message_ids:
            cursor.processed_message_ids = [*cursor.processed_message_ids, message_id]
        cursor.updated_at = utc_now()
        await self.session.flush()
        return cursor

    async def record_outbound(
        self,
        session_id: str,
        command_id: str,
        command_type: str,
        command_payload: dict[str, Any],
        sequence_number: int,
    ) -> ProtocolCursor:
        """Record outbound sent command for acknowledgment tracking and potential recovery."""
        cursor = await self.get_or_create_cursor(session_id)
        cursor.last_outbound_seq = sequence_number
        cursor.last_sent_command_id = command_id
        cursor.last_sent_command_type = command_type
        cursor.last_sent_command_payload = command_payload
        cursor.resend_count = 0  # Reset resend count for new command
        cursor.updated_at = utc_now()
        await self.session.flush()
        return cursor

    async def record_ack(
        self,
        session_id: str,
        acked_message_id: str,
    ) -> ProtocolCursor:
        """Record client acknowledgment of outbound command."""
        cursor = await self.get_or_create_cursor(session_id)
        cursor.last_acked_message_id = acked_message_id
        cursor.resend_count = 0
        cursor.updated_at = utc_now()
        await self.session.flush()
        return cursor

    async def increment_resend(self, session_id: str) -> int:
        """Increment resend count durably and return new count."""
        cursor = await self.get_or_create_cursor(session_id)
        cursor.resend_count += 1
        cursor.updated_at = utc_now()
        await self.session.flush()
        return cursor.resend_count

    async def is_session_expired(self, session_id: str) -> bool:
        """Check if session has expired past TTL."""
        stmt = select(ProtocolCursor).where(ProtocolCursor.session_id == session_id)
        result = await self.session.execute(stmt)
        cursor = result.scalar_one_or_none()
        if cursor is None or cursor.session_expires_at is None:
            return False
        expires_at = cursor.session_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return utc_now() > expires_at
