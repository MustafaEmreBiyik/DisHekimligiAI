"""add_recommendation_snapshots

Revision ID: 5f8a72c1d9b4
Revises: 37c561418f83
Create Date: 2026-04-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5f8a72c1d9b4"
down_revision: Union[str, Sequence[str], None] = "37c561418f83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("recommendation_snapshots"):
        return

    op.create_table(
        "recommendation_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("reason_code", sa.String(), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("priority_score", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommendation_snapshots_user_id",
        "recommendation_snapshots",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_snapshots_case_id",
        "recommendation_snapshots",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_snapshots_created_at",
        "recommendation_snapshots",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("recommendation_snapshots"):
        return

    op.drop_table("recommendation_snapshots")
