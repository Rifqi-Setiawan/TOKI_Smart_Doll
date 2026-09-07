"""Add protocol_cursors table for sequence, idempotency, and recovery (FR-004, FR-005, SEC-004).

Revision ID: 002
Revises: 001
Create Date: 2026-09-07 12:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "protocol_cursors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("last_inbound_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_outbound_seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_acked_message_id", sa.String(length=64), nullable=True),
        sa.Column("last_sent_command_id", sa.String(length=64), nullable=True),
        sa.Column("last_sent_command_type", sa.String(length=64), nullable=True),
        sa.Column("last_sent_command_payload", sa.JSON(), nullable=True),
        sa.Column("resend_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_message_ids", sa.JSON(), nullable=False),
        sa.Column("session_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_protocol_cursor_session"),
    )
    op.create_index("ix_protocol_cursors_session_id", "protocol_cursors", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_protocol_cursors_session_id", table_name="protocol_cursors")
    op.drop_table("protocol_cursors")
