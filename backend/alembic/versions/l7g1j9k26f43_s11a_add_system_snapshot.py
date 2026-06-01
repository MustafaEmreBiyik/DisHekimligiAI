"""S11-A: Add system_snapshots table for reproducible research snapshots.

Revision ID: l7g1j9k26f43
Revises: k6f0i8j15e32
Create Date: 2026-05-31

"""
from alembic import op
import sqlalchemy as sa

revision = "l7g1j9k26f43"
down_revision = "m8h2k0l37g54"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("git_commit_hash", sa.String(), nullable=True),
        sa.Column("questions_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cases_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("questions_payload", sa.JSON(), nullable=False),
        sa.Column("case_definitions_payload", sa.JSON(), nullable=False),
        sa.Column("scoring_config_payload", sa.JSON(), nullable=False),
        sa.Column("llm_config_payload", sa.JSON(), nullable=False),
        sa.Column("rubric_versions_payload", sa.JSON(), nullable=False),
        sa.Column("bundle_size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_snapshots_id", "system_snapshots", ["id"])
    op.create_index("ix_system_snapshots_created_by", "system_snapshots", ["created_by"])
    op.create_index("ix_system_snapshots_created_at", "system_snapshots", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_system_snapshots_created_at", table_name="system_snapshots")
    op.drop_index("ix_system_snapshots_created_by", table_name="system_snapshots")
    op.drop_index("ix_system_snapshots_id", table_name="system_snapshots")
    op.drop_table("system_snapshots")
