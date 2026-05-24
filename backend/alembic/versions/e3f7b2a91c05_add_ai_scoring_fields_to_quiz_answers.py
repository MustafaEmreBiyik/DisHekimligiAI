"""add_ai_scoring_fields_to_quiz_answers

Revision ID: e3f7b2a91c05
Revises: d1e8a3f92c04
Create Date: 2026-05-24 10:00:00.000000

Adds three nullable columns to quiz_answers to support the Sprint 4 AI
draft-scoring workflow (T-4A):

  ai_score_suggestion  Float    — LLM-suggested score (0 to max_score)
  ai_score_rationale   Text     — LLM explanation / rationale
  ai_scored_at         DateTime — timestamp of the AI scoring call

All columns are nullable so existing rows are unaffected.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3f7b2a91c05"
down_revision: Union[str, Sequence[str], None] = "d1e8a3f92c04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("quiz_answers") as batch_op:
        batch_op.add_column(sa.Column("ai_score_suggestion", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("ai_score_rationale", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("ai_scored_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("quiz_answers") as batch_op:
        batch_op.drop_column("ai_scored_at")
        batch_op.drop_column("ai_score_rationale")
        batch_op.drop_column("ai_score_suggestion")
