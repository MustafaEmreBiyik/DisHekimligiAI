"""Add mini_cases table (T-5B).

Revision ID: n9i3l1m48h65
Revises: l7g1j9k26f43
Create Date: 2026-05-31

"""
from alembic import op
import sqlalchemy as sa

revision = "n9i3l1m48h65"
down_revision = "l7g1j9k26f43"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("mini_cases"):
        op.create_table(
            "mini_cases",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("mini_case_id", sa.String(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("linked_topic_ids", sa.JSON(), nullable=True),
            sa.Column("clinical_vignette", sa.Text(), nullable=False),
            sa.Column("key_findings", sa.JSON(), nullable=True),
            sa.Column("question_ids", sa.JSON(), nullable=True),
            sa.Column("learning_objectives", sa.JSON(), nullable=True),
            sa.Column("difficulty", sa.String(), nullable=False, server_default="medium"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("mini_case_id"),
        )
        op.create_index("ix_mini_cases_id", "mini_cases", ["id"])
        op.create_index("ix_mini_cases_mini_case_id", "mini_cases", ["mini_case_id"])


def downgrade() -> None:
    op.drop_index("ix_mini_cases_mini_case_id", table_name="mini_cases")
    op.drop_index("ix_mini_cases_id", table_name="mini_cases")
    op.drop_table("mini_cases")
