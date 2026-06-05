"""s12t01_add_patient_persona_to_case_definitions

Adds the patient_persona_json column to case_definitions so each case can carry
a case-specific simulated patient identity (age, anxiety, evasiveness, speech
style, hidden habits). Optional; the agent falls back to a default persona when
the column is empty.

Revision ID: p1k5n3o60j87
Revises: o0j4m2n59i76
Create Date: 2026-06-05 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "p1k5n3o60j87"
down_revision: Union[str, Sequence[str], None] = "o0j4m2n59i76"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("case_definitions"):
        return

    columns = {column["name"] for column in inspector.get_columns("case_definitions")}
    if "patient_persona_json" not in columns:
        op.add_column(
            "case_definitions",
            sa.Column(
                "patient_persona_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("case_definitions"):
        return

    columns = {column["name"] for column in inspector.get_columns("case_definitions")}
    if "patient_persona_json" in columns:
        op.drop_column("case_definitions", "patient_persona_json")
