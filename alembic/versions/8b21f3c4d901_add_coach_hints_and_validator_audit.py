"""add_coach_hints_and_validator_audit

Revision ID: 8b21f3c4d901
Revises: 5f8a72c1d9b4
Create Date: 2026-04-03 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b21f3c4d901"
down_revision: Union[str, Sequence[str], None] = "6c8eab0b6f8d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("coach_hints"):
        op.create_table(
            "coach_hints",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("hint_level", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["student_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_coach_hints_session_id", "coach_hints", ["session_id"], unique=False)
        op.create_index("ix_coach_hints_user_id", "coach_hints", ["user_id"], unique=False)
        op.create_index("ix_coach_hints_created_at", "coach_hints", ["created_at"], unique=False)

    if not inspector.has_table("validator_audit_log"):
        op.create_table(
            "validator_audit_log",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("validator_used", sa.String(), nullable=False),
            sa.Column("safety_violation", sa.Boolean(), nullable=False),
            sa.Column("clinical_accuracy", sa.String(), nullable=True),
            sa.Column("response_time_ms", sa.Integer(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["session_id"], ["student_sessions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_validator_audit_log_session_id",
            "validator_audit_log",
            ["session_id"],
            unique=False,
        )
        op.create_index(
            "ix_validator_audit_log_created_at",
            "validator_audit_log",
            ["created_at"],
            unique=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("validator_audit_log"):
        op.drop_table("validator_audit_log")

    if inspector.has_table("coach_hints"):
        op.drop_table("coach_hints")
