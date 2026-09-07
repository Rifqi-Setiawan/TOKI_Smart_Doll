"""Initial schema for TOKI Smart Doll authoritative persistence.
Requirements: DATA-001–005, DATA-007–010, DEV-003.

Revision ID: 001
Revises: None
Create Date: 2026-09-07 11:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. guardians
    op.create_table(
        "guardians",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pseudonym", sa.String(length=64), nullable=False),
        sa.Column("email_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_guardians_email_hash", "guardians", ["email_hash"])

    # 2. children (DATA-008: pseudonymous, age_band instead of exact DOB)
    op.create_table(
        "children",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("guardian_id", sa.String(length=36), nullable=False),
        sa.Column("pseudonym", sa.String(length=64), nullable=False),
        sa.Column("age_band", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["guardian_id"], ["guardians.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_children_guardian_id", "children", ["guardian_id"])

    # 3. devices
    op.create_table(
        "devices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("device_serial", sa.String(length=64), nullable=False),
        sa.Column("guardian_id", sa.String(length=36), nullable=True),
        sa.Column("child_id", sa.String(length=36), nullable=True),
        sa.Column("firmware_version", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["guardian_id"], ["guardians.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_devices_device_serial", "devices", ["device_serial"], unique=True)
    op.create_index("ix_devices_child_id", "devices", ["child_id"])
    op.create_index("ix_devices_guardian_id", "devices", ["guardian_id"])

    # 4. consents (DATA-010)
    op.create_table(
        "consents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("guardian_id", sa.String(length=36), nullable=False),
        sa.Column("child_id", sa.String(length=36), nullable=False),
        sa.Column("consent_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guardian_id"], ["guardians.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_consents_child_id", "consents", ["child_id"])
    op.create_index("ix_consents_guardian_id", "consents", ["guardian_id"])

    # 5. curriculum_versions (DATA-003)
    op.create_table(
        "curriculum_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("version_token", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("approved_by", sa.String(length=64), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_curriculum_versions_version_token",
        "curriculum_versions",
        ["version_token"],
        unique=True,
    )

    # 6. curriculum_skills
    op.create_table(
        "curriculum_skills",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("curriculum_version_id", sa.String(length=36), nullable=False),
        sa.Column("skill_token", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("target_age_band", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"], ["curriculum_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "curriculum_version_id", "skill_token", name="uq_curriculum_version_skill"
        ),
    )
    op.create_index(
        "ix_curriculum_skills_curriculum_version_id", "curriculum_skills", ["curriculum_version_id"]
    )

    # 7. curriculum_items
    op.create_table(
        "curriculum_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("curriculum_version_id", sa.String(length=36), nullable=False),
        sa.Column("skill_id", sa.String(length=36), nullable=False),
        sa.Column("item_token", sa.String(length=64), nullable=False),
        sa.Column("prompt_text", sa.String(length=255), nullable=False),
        sa.Column("expected_answers", sa.JSON(), nullable=False),
        sa.Column("fallback_asset_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"], ["curriculum_versions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["skill_id"], ["curriculum_skills.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "curriculum_version_id", "item_token", name="uq_curriculum_version_item"
        ),
    )
    op.create_index(
        "ix_curriculum_items_curriculum_version_id", "curriculum_items", ["curriculum_version_id"]
    )
    op.create_index("ix_curriculum_items_skill_id", "curriculum_items", ["skill_id"])

    # 8. sessions (DATA-002: state_version optimistic concurrency)
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("child_id", sa.String(length=36), nullable=False),
        sa.Column("curriculum_version_id", sa.String(length=36), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("current_turn_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"], ["curriculum_versions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_child_id", "sessions", ["child_id"])
    op.create_index("ix_sessions_curriculum_version_id", "sessions", ["curriculum_version_id"])
    op.create_index("ix_sessions_device_id", "sessions", ["device_id"])

    # 9. turns
    op.create_table(
        "turns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("item_token", sa.String(length=64), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "turn_number", name="uq_session_turn_number"),
    )
    op.create_index("ix_turns_session_id", "turns", ["session_id"])

    # 10. attempts (DATA-004: unique message_id for idempotency)
    op.create_table(
        "attempts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("turn_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=64), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("reason_code", sa.String(length=32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("spoken_text", sa.String(length=255), nullable=True),
        sa.Column("assistance_level", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["turn_id"], ["turns.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_attempts_message_id", "attempts", ["message_id"], unique=True)
    op.create_index("ix_attempts_turn_id", "attempts", ["turn_id"])

    # 11. child_mastery (ADR-011)
    op.create_table(
        "child_mastery",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("child_id", sa.String(length=36), nullable=False),
        sa.Column("skill_token", sa.String(length=64), nullable=False),
        sa.Column("mastery_band", sa.String(length=16), nullable=False),
        sa.Column("practice_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("child_id", "skill_token", name="uq_child_mastery_skill"),
    )
    op.create_index("ix_child_mastery_child_id", "child_mastery", ["child_id"])
    op.create_index("ix_child_mastery_skill_token", "child_mastery", ["skill_token"])

    # 12. mastery_history
    op.create_table(
        "mastery_history",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("child_id", sa.String(length=36), nullable=False),
        sa.Column("skill_token", sa.String(length=64), nullable=False),
        sa.Column("attempt_id", sa.String(length=36), nullable=True),
        sa.Column("previous_band", sa.String(length=16), nullable=False),
        sa.Column("new_band", sa.String(length=16), nullable=False),
        sa.Column("transition_reason", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["attempt_id"], ["attempts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["child_id"], ["children.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mastery_history_attempt_id", "mastery_history", ["attempt_id"])
    op.create_index("ix_mastery_history_child_id", "mastery_history", ["child_id"])

    # 13. domain_events (DATA-005)
    op.create_table(
        "domain_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("event_sequence", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("privacy_class", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_domain_events_event_type", "domain_events", ["event_type"])
    op.create_index("ix_domain_events_session_id", "domain_events", ["session_id"])

    # 14. outbox_events (DATA-005, ADR-012)
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["domain_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_outbox_events_event_id", "outbox_events", ["event_id"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])
    op.create_index("ix_outbox_events_topic", "outbox_events", ["topic"])

    # 15. version_metadata (DATA-007)
    op.create_table(
        "version_metadata",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("component", sa.String(length=32), nullable=False),
        sa.Column("version_token", sa.String(length=64), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("component", "version_token", name="uq_component_version_token"),
    )
    op.create_index("ix_version_metadata_component", "version_metadata", ["component"])


def downgrade() -> None:
    # Drop in strict reverse dependency order
    op.drop_table("version_metadata")
    op.drop_table("outbox_events")
    op.drop_table("domain_events")
    op.drop_table("mastery_history")
    op.drop_table("child_mastery")
    op.drop_table("attempts")
    op.drop_table("turns")
    op.drop_table("sessions")
    op.drop_table("curriculum_items")
    op.drop_table("curriculum_skills")
    op.drop_table("curriculum_versions")
    op.drop_table("consents")
    op.drop_table("devices")
    op.drop_table("children")
    op.drop_table("guardians")
