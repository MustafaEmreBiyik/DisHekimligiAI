"""add_unit_id_week_number_to_questions

Revision ID: d1e8a3f92c04
Revises: b7d42a1f63e2
Create Date: 2026-05-24 09:00:00.000000

Adds unit_id (String, nullable) and week_number (Integer, nullable) to the
questions table to satisfy the full konu/ünite/hafta/zorluk/yetkinlik
tagging requirement from Sprint 1.

Both columns are nullable so existing rows are unaffected and no data
migration is required.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1e8a3f92c04"
down_revision: Union[str, Sequence[str], None] = "b7d42a1f63e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.add_column(sa.Column("unit_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("week_number", sa.Integer(), nullable=True))
        batch_op.create_index("ix_questions_unit_id", ["unit_id"])


def downgrade() -> None:
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_index("ix_questions_unit_id")
        batch_op.drop_column("week_number")
        batch_op.drop_column("unit_id")
