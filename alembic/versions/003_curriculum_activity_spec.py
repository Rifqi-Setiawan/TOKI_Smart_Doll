"""Add activity_spec column to curriculum_items for rich activity metadata (FR-007, DATA-003).

Revision ID: 003
Revises: 002
Create Date: 2026-09-07 13:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("curriculum_items") as batch_op:
        batch_op.add_column(
            sa.Column("activity_spec", sa.JSON(), nullable=False, server_default="{}")
        )


def downgrade() -> None:
    with op.batch_alter_table("curriculum_items") as batch_op:
        batch_op.drop_column("activity_spec")
