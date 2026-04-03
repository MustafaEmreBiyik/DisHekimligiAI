"""add_case_publish_history

Revision ID: b7d42a1f63e2
Revises: 9c1a7c0b5aa1
Create Date: 2026-04-03 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7d42a1f63e2"
down_revision: Union[str, Sequence[str], None] = "9c1a7c0b5aa1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("case_publish_history"):
        return

    op.create_table(
        "case_publish_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("change_notes", sa.Text(), nullable=False),
        sa.Column("published_by", sa.String(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_publish_history_case_id", "case_publish_history", ["case_id"], unique=False)
    op.create_index("ix_case_publish_history_published_by", "case_publish_history", ["published_by"], unique=False)
    op.create_index("ix_case_publish_history_published_at", "case_publish_history", ["published_at"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("case_publish_history"):
        return

    op.drop_table("case_publish_history")
