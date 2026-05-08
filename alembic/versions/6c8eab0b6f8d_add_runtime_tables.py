"""add_runtime_tables

Revision ID: 6c8eab0b6f8d
Revises: 5f8a72c1d9b4
Create Date: 2026-04-27 11:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c8eab0b6f8d"
down_revision: Union[str, Sequence[str], None] = "5f8a72c1d9b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(bind, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _get_columns(bind, table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


def _get_indexes(bind, table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if not _has_table(bind, "student_sessions"):
        op.create_table(
            "student_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.String(), nullable=False),
            sa.Column("case_id", sa.String(), nullable=False),
            sa.Column("current_score", sa.Float(), nullable=True),
            sa.Column("state_json", sa.Text(), nullable=True),
            sa.Column("start_time", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_student_sessions_student_id", "student_sessions", ["student_id"], unique=False)
    else:
        columns = _get_columns(bind, "student_sessions")
        indexes = _get_indexes(bind, "student_sessions")
        if "state_json" not in columns:
            op.add_column(
                "student_sessions",
                sa.Column("state_json", sa.Text(), nullable=True, server_default=sa.text("'{}'")),
            )
        if "ix_student_sessions_student_id" not in indexes:
            op.create_index("ix_student_sessions_student_id", "student_sessions", ["student_id"], unique=False)

    if not _has_table(bind, "chat_logs"):
        op.create_table(
            "chat_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["session_id"], ["student_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(bind, "exam_results"):
        op.create_table(
            "exam_results",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("case_id", sa.String(), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("max_score", sa.Integer(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("details_json", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_exam_results_user_id", "exam_results", ["user_id"], unique=False)
        op.create_index("ix_exam_results_case_id", "exam_results", ["case_id"], unique=False)
    else:
        indexes = _get_indexes(bind, "exam_results")
        if "ix_exam_results_user_id" not in indexes:
            op.create_index("ix_exam_results_user_id", "exam_results", ["user_id"], unique=False)
        if "ix_exam_results_case_id" not in indexes:
            op.create_index("ix_exam_results_case_id", "exam_results", ["case_id"], unique=False)

    if not _has_table(bind, "feedback_logs"):
        op.create_table(
            "feedback_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("student_id", sa.String(), nullable=False),
            sa.Column("case_id", sa.String(), nullable=False),
            sa.Column("rating", sa.Integer(), nullable=False),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["session_id"], ["student_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_feedback_logs_student_id", "feedback_logs", ["student_id"], unique=False)
        op.create_index("ix_feedback_logs_case_id", "feedback_logs", ["case_id"], unique=False)
    else:
        indexes = _get_indexes(bind, "feedback_logs")
        if "ix_feedback_logs_student_id" not in indexes:
            op.create_index("ix_feedback_logs_student_id", "feedback_logs", ["student_id"], unique=False)
        if "ix_feedback_logs_case_id" not in indexes:
            op.create_index("ix_feedback_logs_case_id", "feedback_logs", ["case_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    if _has_table(bind, "feedback_logs"):
        op.drop_table("feedback_logs")

    if _has_table(bind, "exam_results"):
        op.drop_table("exam_results")

    if _has_table(bind, "chat_logs"):
        op.drop_table("chat_logs")

    if _has_table(bind, "student_sessions"):
        op.drop_table("student_sessions")
