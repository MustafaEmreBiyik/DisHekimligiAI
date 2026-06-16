"""s12t06_add_experiment_framework

Adds experiment_group column to users table and creates the
experiment_assignments table for deterministic A/B test group tracking.
Each student is assigned once per experiment and stays in the same group
across sessions.

Revision ID: s4n8o2p31k10
Revises: r3m7o5q82l09
Create Date: 2026-06-06 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "s4n8o2p31k10"
down_revision: Union[str, Sequence[str], None] = "r3m7o5q82l09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ── experiment_group column on users ─────────────────────────────────────
    if inspector.has_table("users"):
        columns = {col["name"] for col in inspector.get_columns("users")}
        if "experiment_group" not in columns:
            op.add_column(
                "users",
                sa.Column("experiment_group", sa.String(), nullable=True),
            )

    # ── experiment_assignments table ─────────────────────────────────────────
    if not inspector.has_table("experiment_assignments"):
        op.create_table(
            "experiment_assignments",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("experiment_id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=False),
            sa.Column("group_name", sa.String(), nullable=False),
            sa.Column("assigned_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_experiment_assignments_id",
            "experiment_assignments",
            ["id"],
        )
        op.create_index(
            "ix_experiment_assignments_user_id",
            "experiment_assignments",
            ["user_id"],
        )
        op.create_index(
            "ix_experiment_assignments_experiment_id",
            "experiment_assignments",
            ["experiment_id"],
        )
        op.create_index(
            "uq_experiment_user",
            "experiment_assignments",
            ["user_id", "experiment_id"],
            unique=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("experiment_assignments"):
        op.drop_index("uq_experiment_user", table_name="experiment_assignments")
        op.drop_index("ix_experiment_assignments_experiment_id", table_name="experiment_assignments")
        op.drop_index("ix_experiment_assignments_user_id", table_name="experiment_assignments")
        op.drop_index("ix_experiment_assignments_id", table_name="experiment_assignments")
        op.drop_table("experiment_assignments")

    if inspector.has_table("users"):
        columns = {col["name"] for col in inspector.get_columns("users")}
        if "experiment_group" in columns:
            op.drop_column("users", "experiment_group")
