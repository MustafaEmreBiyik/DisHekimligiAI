"""add_notifications

Revision ID: h3c7e5f82b19
Revises: g2b6d4e71a08
Create Date: 2026-05-25 12:00:00.000000

Implements T-7A — notifications table for score publication alerts.
"""

from alembic import op
import sqlalchemy as sa

revision = "h3c7e5f82b19"
down_revision = "g2b6d4e71a08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.String, nullable=False, index=True),
        sa.Column("type", sa.String, nullable=False),
        sa.Column("payload_json", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default="0", index=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("notifications")
