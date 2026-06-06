"""s12t08_add_research_exports_table

Adds research_exports table for KVKK-anonymised dataset export bundles.

Revision ID: t5o9p3q42l11
Revises: s4n8o2p31k10
Create Date: 2026-06-06
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "t5o9p3q42l11"
down_revision: Union[str, Sequence[str], None] = "s4n8o2p31k10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("research_exports"):
        op.create_table(
            "research_exports",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("created_by", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("tables_included", sa.JSON(), nullable=False),
            sa.Column("row_count_total", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("zip_bytes", sa.LargeBinary(), nullable=True),
            sa.Column("status", sa.String(), nullable=False, server_default="ready"),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("filename", sa.String(), nullable=True),
        )
        op.create_index("ix_research_exports_id", "research_exports", ["id"])
        op.create_index("ix_research_exports_created_by", "research_exports", ["created_by"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("research_exports"):
        op.drop_index("ix_research_exports_created_by", table_name="research_exports")
        op.drop_index("ix_research_exports_id", table_name="research_exports")
        op.drop_table("research_exports")
