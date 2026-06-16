"""s12t02_add_case_images_to_case_definitions

Adds case_images_json column to case_definitions so each case can carry a list
of clinical images ({url, type, caption}) displayed to the student during the
chat and passed to the MedGemma validator for multimodal evaluation.

Revision ID: q2l6n4p71k98
Revises: p1k5n3o60j87
Create Date: 2026-06-05 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "q2l6n4p71k98"
down_revision: Union[str, Sequence[str], None] = "p1k5n3o60j87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("case_definitions"):
        return

    columns = {column["name"] for column in inspector.get_columns("case_definitions")}
    if "case_images_json" not in columns:
        op.add_column(
            "case_definitions",
            sa.Column(
                "case_images_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("case_definitions"):
        return

    columns = {column["name"] for column in inspector.get_columns("case_definitions")}
    if "case_images_json" in columns:
        op.drop_column("case_definitions", "case_images_json")
