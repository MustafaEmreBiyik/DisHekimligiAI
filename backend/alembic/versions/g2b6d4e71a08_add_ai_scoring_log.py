"""add_ai_scoring_log

Revision ID: g2b6d4e71a08
Revises: f1a5d2c83b06
Create Date: 2026-05-25 10:00:00.000000

Implements T-6D — AI Scoring Rate Limiting & Error Tracking:

  ai_scoring_logs table:
    - Records every AI scoring attempt (success or error)
    - Tracks model_id, latency, and error_message for debugging
"""

from alembic import op
import sqlalchemy as sa

revision = "g2b6d4e71a08"
down_revision = "f1a5d2c83b06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_scoring_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("answer_id", sa.Integer, sa.ForeignKey("quiz_answers.id"), nullable=False, index=True),
        sa.Column("model_id", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("suggested_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table("ai_scoring_logs")
