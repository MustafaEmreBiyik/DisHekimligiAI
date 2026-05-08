"""add_is_spotlight_to_recommendation_snapshots

Revision ID: 9c1a7c0b5aa1
Revises: 8b21f3c4d901
Create Date: 2026-04-03 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c1a7c0b5aa1"
down_revision: Union[str, Sequence[str], None] = "8b21f3c4d901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("recommendation_snapshots"):
        return

    columns = {col["name"] for col in inspector.get_columns("recommendation_snapshots")}
    if "is_spotlight" not in columns:
        op.add_column(
            "recommendation_snapshots",
            sa.Column("is_spotlight", sa.Boolean(), nullable=False, server_default=sa.false()),
        )

    indexes = {index["name"] for index in inspector.get_indexes("recommendation_snapshots")}
    if "ix_recommendation_snapshots_is_spotlight" not in indexes:
        op.create_index(
            "ix_recommendation_snapshots_is_spotlight",
            "recommendation_snapshots",
            ["is_spotlight"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("recommendation_snapshots"):
        return

    columns = {col["name"] for col in inspector.get_columns("recommendation_snapshots")}
    indexes = {index["name"] for index in inspector.get_indexes("recommendation_snapshots")}

    if "ix_recommendation_snapshots_is_spotlight" in indexes:
        op.drop_index("ix_recommendation_snapshots_is_spotlight", table_name="recommendation_snapshots")

    if "is_spotlight" in columns:
        op.drop_column("recommendation_snapshots", "is_spotlight")
