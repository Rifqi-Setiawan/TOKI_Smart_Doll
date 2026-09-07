"""SQLAlchemy models for authoritative persistence.
Requirements: DATA-001–005, DATA-007–010, ADR-012, ADR-013.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.persistence.database import Base


def utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(UTC)


def gen_uuid() -> str:
    """Generate canonical UUID string."""
    return str(uuid.uuid4())


class Guardian(Base):
    """Guardian identity record holding pseudonymous email hash and consent relation."""

    __tablename__ = "guardians"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    pseudonym: Mapped[str] = mapped_column(String(64), nullable=False)
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    children: Mapped[list["Child"]] = relationship("Child", back_populates="guardian")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="guardian")
    consents: Mapped[list["Consent"]] = relationship("Consent", back_populates="guardian")


class Child(Base):
    """Pseudonymous child profile using coarse age bands rather than exact DOB (DATA-008)."""

    __tablename__ = "children"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    guardian_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("guardians.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pseudonym: Mapped[str] = mapped_column(String(64), nullable=False)
    age_band: Mapped[str] = mapped_column(String(16), nullable=False)  # e.g. '4-5', '6-8'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    guardian: Mapped["Guardian"] = relationship("Guardian", back_populates="children")
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="child")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="child")
    mastery_records: Mapped[list["ChildMastery"]] = relationship(
        "ChildMastery", back_populates="child"
    )
    consents: Mapped[list["Consent"]] = relationship("Consent", back_populates="child")


class Device(Base):
    """Physical doll hardware unit registered to guardian/child."""

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    device_serial: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    guardian_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("guardians.id", ondelete="SET NULL"), nullable=True, index=True
    )
    child_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("children.id", ondelete="SET NULL"), nullable=True, index=True
    )
    firmware_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    guardian: Mapped["Guardian | None"] = relationship("Guardian", back_populates="devices")
    child: Mapped["Child | None"] = relationship("Child", back_populates="devices")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="device")


class Consent(Base):
    """Guardian data processing and voice interaction consent (DATA-010)."""

    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    guardian_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("guardians.id", ondelete="CASCADE"), nullable=False, index=True
    )
    child_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    consent_type: Mapped[str] = mapped_column(String(32), nullable=False, default="DATA_PROCESSING")
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="GRANTED"
    )  # GRANTED, REVOKED
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    guardian: Mapped["Guardian"] = relationship("Guardian", back_populates="consents")
    child: Mapped["Child"] = relationship("Child", back_populates="consents")


class CurriculumVersion(Base):
    """Immutable approved curriculum version manifest (DATA-003)."""

    __tablename__ = "curriculum_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    version_token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )  # e.g. 'curriculum-v1.0'
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DRAFT"
    )  # DRAFT, APPROVED, ARCHIVED
    approved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    skills: Mapped[list["CurriculumSkill"]] = relationship(
        "CurriculumSkill", back_populates="curriculum_version", cascade="all, delete-orphan"
    )
    items: Mapped[list["CurriculumItem"]] = relationship(
        "CurriculumItem", back_populates="curriculum_version", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="curriculum_version")


class CurriculumSkill(Base):
    """Curriculum skill token within an immutable curriculum release."""

    __tablename__ = "curriculum_skills"
    __table_args__ = (
        UniqueConstraint(
            "curriculum_version_id", "skill_token", name="uq_curriculum_version_skill"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    curriculum_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("curriculum_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_token: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    target_age_band: Mapped[str] = mapped_column(String(16), nullable=False, default="4-6")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    curriculum_version: Mapped["CurriculumVersion"] = relationship(
        "CurriculumVersion", back_populates="skills"
    )
    items: Mapped[list["CurriculumItem"]] = relationship("CurriculumItem", back_populates="skill")


class CurriculumItem(Base):
    """Approved curriculum turn prompt, answer tokens, and fallback asset ID."""

    __tablename__ = "curriculum_items"
    __table_args__ = (
        UniqueConstraint("curriculum_version_id", "item_token", name="uq_curriculum_version_item"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    curriculum_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("curriculum_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("curriculum_skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_token: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_text: Mapped[str] = mapped_column(String(255), nullable=False)
    expected_answers: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    fallback_asset_id: Mapped[str] = mapped_column(String(64), nullable=False)
    activity_spec: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    curriculum_version: Mapped["CurriculumVersion"] = relationship(
        "CurriculumVersion", back_populates="items"
    )
    skill: Mapped["CurriculumSkill"] = relationship("CurriculumSkill", back_populates="items")


class Session(Base):
    """Interactive learning session protected by optimistic concurrency state_version (DATA-002)."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    child_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("children.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    curriculum_version_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("curriculum_versions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="INITIALIZING")
    state_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )  # Optimistic concurrency (DATA-002)
    current_turn_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    device: Mapped["Device"] = relationship("Device", back_populates="sessions")
    child: Mapped["Child"] = relationship("Child", back_populates="sessions")
    curriculum_version: Mapped["CurriculumVersion"] = relationship(
        "CurriculumVersion", back_populates="sessions"
    )
    turns: Mapped[list["Turn"]] = relationship(
        "Turn", back_populates="session", cascade="all, delete-orphan"
    )
    protocol_cursor: Mapped["ProtocolCursor | None"] = relationship(
        "ProtocolCursor", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )


class Turn(Base):
    """Turn execution record holding item token and state snapshot."""

    __tablename__ = "turns"
    __table_args__ = (UniqueConstraint("session_id", "turn_number", name="uq_session_turn_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    item_token: Mapped[str] = mapped_column(String(64), nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING"
    )  # PENDING, RESOLVED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped["Session"] = relationship("Session", back_populates="turns")
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="turn", cascade="all, delete-orphan"
    )


class Attempt(Base):
    """Idempotent attempt resolution record; enforces uniqueness on message_id (DATA-004)."""

    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    turn_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("turns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )  # Replay prevention (DATA-004)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    spoken_text: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Redacted text only, never raw audio (ADR-013)
    assistance_level: Mapped[str] = mapped_column(String(16), nullable=False, default="NONE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    turn: Mapped["Turn"] = relationship("Turn", back_populates="attempts")


class ChildMastery(Base):
    """Authoritative skill mastery state band and practice counters (ADR-011)."""

    __tablename__ = "child_mastery"
    __table_args__ = (UniqueConstraint("child_id", "skill_token", name="uq_child_mastery_skill"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    child_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_token: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    mastery_band: Mapped[str] = mapped_column(
        String(16), nullable=False, default="INTRODUCED"
    )  # INTRODUCED, PRACTICING, ACQUIRED
    practice_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    child: Mapped["Child"] = relationship("Child", back_populates="mastery_records")


class MasteryHistory(Base):
    """Audit log of mastery progression transitions."""

    __tablename__ = "mastery_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    child_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_token: Mapped[str] = mapped_column(String(64), nullable=False)
    attempt_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("attempts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    previous_band: Mapped[str] = mapped_column(String(16), nullable=False)
    new_band: Mapped[str] = mapped_column(String(16), nullable=False)
    transition_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DomainEvent(Base):
    """Append-only domain event log for audit, replay, and projection (DATA-005)."""

    __tablename__ = "domain_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    privacy_class: Mapped[str] = mapped_column(String(32), nullable=False, default="OPERATIONAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OutboxEvent(Base):
    """Transactional outbox event committed atomically with domain events (DATA-005, ADR-012)."""

    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("domain_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING", index=True
    )  # PENDING, PUBLISHED, FAILED
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VersionMetadata(Base):
    """Provenance tracking for models, prompts, policies, thresholds, and releases (DATA-007)."""

    __tablename__ = "version_metadata"
    __table_args__ = (
        UniqueConstraint("component", "version_token", name="uq_component_version_token"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    component: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # curriculum, model, prompt, policy, threshold, firmware, release
    version_token: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProtocolCursor(Base):
    """Durable sequence, idempotency, and acknowledgment cursor (FR-004, FR-005, SEC-004)."""

    __tablename__ = "protocol_cursors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    last_inbound_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_outbound_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_acked_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_sent_command_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_sent_command_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_sent_command_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    resend_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_message_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    session_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    session: Mapped["Session"] = relationship("Session", back_populates="protocol_cursor")
