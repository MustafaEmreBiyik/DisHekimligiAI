"""sprint8_exam_schedule

Revision ID: i4d8f6g93c20
Revises: h3c7e5f82b19
Create Date: 2026-05-25 14:00:00.000000

Sprint 8 schema changes:
  - T-8A: exam_schedules table
  - T-8B: schedule_id + time_limit_expires_at on quiz_attempts
  - T-8C: secondary grading fields on quiz_answers
"""

from alembic import op
import sqlalchemy as sa

revision = "i4d8f6g93c20"
down_revision = "h3c7e5f82b19"
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _get_columns(bind, table_name: str) -> set:
    return {col["name"] for col in sa.inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()

    if not _has_table(bind, "exam_schedules"):
        op.create_table(
            "exam_schedules",
            sa.Column("id", sa.Integer, primary_key=True, index=True),
            sa.Column("title", sa.String, nullable=False),
            sa.Column("question_ids", sa.JSON, nullable=False, server_default="[]"),
            sa.Column("opens_at", sa.DateTime, nullable=False),
            sa.Column("closes_at", sa.DateTime, nullable=False),
            sa.Column("time_limit_minutes", sa.Integer, nullable=True),
            sa.Column("created_by", sa.String, nullable=False, index=True),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default="1", index=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )

    existing_attempt_cols = _get_columns(bind, "quiz_attempts")
    if "schedule_id" not in existing_attempt_cols:
        op.add_column("quiz_attempts", sa.Column("schedule_id", sa.Integer, nullable=True))
    if "time_limit_expires_at" not in existing_attempt_cols:
        op.add_column("quiz_attempts", sa.Column("time_limit_expires_at", sa.DateTime, nullable=True))

    existing_answer_cols = _get_columns(bind, "quiz_answers")
    if "secondary_instructor_score" not in existing_answer_cols:
        op.add_column("quiz_answers", sa.Column("secondary_instructor_score", sa.Float, nullable=True))
    if "secondary_instructor_id" not in existing_answer_cols:
        op.add_column("quiz_answers", sa.Column("secondary_instructor_id", sa.String, nullable=True))
    if "secondary_graded_at" not in existing_answer_cols:
        op.add_column("quiz_answers", sa.Column("secondary_graded_at", sa.DateTime, nullable=True))
    if "inter_rater_delta" not in existing_answer_cols:
        op.add_column("quiz_answers", sa.Column("inter_rater_delta", sa.Float, nullable=True))


def downgrade() -> None:
    op.drop_column("quiz_answers", "inter_rater_delta")
    op.drop_column("quiz_answers", "secondary_graded_at")
    op.drop_column("quiz_answers", "secondary_instructor_id")
    op.drop_column("quiz_answers", "secondary_instructor_score")
    op.drop_column("quiz_attempts", "time_limit_expires_at")
    op.drop_column("quiz_attempts", "schedule_id")
    op.drop_table("exam_schedules")
