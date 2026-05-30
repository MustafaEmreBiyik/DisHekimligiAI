"""S9-C: Add llm_interaction_logs table for LLM cost and latency tracking

Revision ID: j5e9h7i04d21
Revises: i4d8f6g93c20
Create Date: 2026-05-30 00:00:00.000000

Purpose:
  Every Gemini and HuggingFace API call is now recorded with provider, model,
  call type, token counts, latency and estimated USD cost. This table enables:
  - Budget monitoring (EU AI Act + institutional compliance)
  - Rate-limit failure detection
  - Per-session LLM cost attribution for longitudinal research
"""

from alembic import op
import sqlalchemy as sa

revision = "j5e9h7i04d21"
down_revision = "i4d8f6g93c20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_interaction_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column(
            "session_id",
            sa.Integer,
            sa.ForeignKey("student_sessions.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("provider", sa.String, nullable=False, index=True),
        sa.Column("model_id", sa.String, nullable=False),
        sa.Column("call_type", sa.String, nullable=False, index=True),
        sa.Column("prompt_tokens", sa.Integer, nullable=True),
        sa.Column("completion_tokens", sa.Integer, nullable=True),
        sa.Column("total_tokens", sa.Integer, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float, nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, server_default="1", index=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("llm_interaction_logs")
