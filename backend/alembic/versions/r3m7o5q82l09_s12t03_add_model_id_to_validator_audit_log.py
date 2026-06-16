"""s12t03_add_model_id_to_validator_audit_log

Adds model_id column to validator_audit_log so each validation call records
the exact HuggingFace model used, enabling A/B comparison between validator
versions without code changes (switched via VALIDATOR_MODEL_ID env var).

Revision ID: r3m7o5q82l09
Revises: q2l6n4p71k98
Create Date: 2026-06-06 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "r3m7o5q82l09"
down_revision: Union[str, Sequence[str], None] = "q2l6n4p71k98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("validator_audit_log"):
        return

    columns = {column["name"] for column in inspector.get_columns("validator_audit_log")}
    if "model_id" not in columns:
        op.add_column(
            "validator_audit_log",
            sa.Column("model_id", sa.String(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("validator_audit_log"):
        return

    columns = {column["name"] for column in inspector.get_columns("validator_audit_log")}
    if "model_id" in columns:
        op.drop_column("validator_audit_log", "model_id")
