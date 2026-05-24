"""add_rubric_versioning

Revision ID: f1a5d2c83b06
Revises: e3f7b2a91c05
Create Date: 2026-05-24 11:00:00.000000

Implements T-4B — Rubric Versioning:

  rubric_versions table:
    - Stores immutable snapshots of rubric_guide + model_answer_outline
      whenever an instructor publishes a rubric change for a question.

  questions.current_rubric_version:
    - Integer tracking the current (latest) published rubric version number.

  quiz_answers.rubric_version_id:
    - FK to rubric_versions.id — stamped at grading time so we can audit
      which rubric criteria were active when an answer was graded.

All new columns are nullable so existing rows are unaffected.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a5d2c83b06"
down_revision: Union[str, Sequence[str], None] = "e3f7b2a91c05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the rubric_versions table
    op.create_table(
        "rubric_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rubric_guide", sa.Text(), nullable=False),
        sa.Column("model_answer_outline", sa.Text(), nullable=False),
        sa.Column("change_notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rubric_versions_id", "rubric_versions", ["id"])
    op.create_index("ix_rubric_versions_question_id", "rubric_versions", ["question_id"])
    op.create_index("ix_rubric_versions_created_by", "rubric_versions", ["created_by"])
    op.create_index("ix_rubric_versions_created_at", "rubric_versions", ["created_at"])

    # 2. Add current_rubric_version to questions
    with op.batch_alter_table("questions") as batch_op:
        batch_op.add_column(sa.Column("current_rubric_version", sa.Integer(), nullable=True))

    # 3. Add rubric_version_id to quiz_answers
    with op.batch_alter_table("quiz_answers") as batch_op:
        batch_op.add_column(
            sa.Column("rubric_version_id", sa.Integer(), nullable=True)
        )
        batch_op.create_index("ix_quiz_answers_rubric_version_id", ["rubric_version_id"])


def downgrade() -> None:
    # 3. Remove from quiz_answers
    with op.batch_alter_table("quiz_answers") as batch_op:
        batch_op.drop_index("ix_quiz_answers_rubric_version_id")
        batch_op.drop_column("rubric_version_id")

    # 2. Remove from questions
    with op.batch_alter_table("questions") as batch_op:
        batch_op.drop_column("current_rubric_version")

    # 1. Drop rubric_versions table
    op.drop_index("ix_rubric_versions_created_at", "rubric_versions")
    op.drop_index("ix_rubric_versions_created_by", "rubric_versions")
    op.drop_index("ix_rubric_versions_question_id", "rubric_versions")
    op.drop_index("ix_rubric_versions_id", "rubric_versions")
    op.drop_table("rubric_versions")
