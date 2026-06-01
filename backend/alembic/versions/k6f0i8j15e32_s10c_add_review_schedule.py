"""S10-C: Add review_schedules table for SM-2 spaced repetition scheduler.

Revision ID: k6f0i8j15e32
Revises: j5e9h7i04d21
Create Date: 2026-05-30

"""
from alembic import op
import sqlalchemy as sa

revision = "k6f0i8j15e32"
down_revision = "j5e9h7i04d21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=False),
        sa.Column("interval_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"),
        sa.Column("repetitions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_schedules_id", "review_schedules", ["id"])
    op.create_index("ix_review_schedules_user_id", "review_schedules", ["user_id"])
    op.create_index("ix_review_schedules_question_id", "review_schedules", ["question_id"])
    op.create_index("ix_review_schedules_due_date", "review_schedules", ["due_date"])


def downgrade() -> None:
    op.drop_index("ix_review_schedules_due_date", table_name="review_schedules")
    op.drop_index("ix_review_schedules_question_id", table_name="review_schedules")
    op.drop_index("ix_review_schedules_user_id", table_name="review_schedules")
    op.drop_index("ix_review_schedules_id", table_name="review_schedules")
    op.drop_table("review_schedules")
