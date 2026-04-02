"""add_case_definitions

Revision ID: 37c561418f83
Revises: 20aeab586022
Create Date: 2026-04-02 23:27:32.955890

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37c561418f83'
down_revision: Union[str, Sequence[str], None] = '20aeab586022'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("case_definitions"):
        return

    op.create_table(
        "case_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.String(), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("learning_objectives", sa.JSON(), nullable=False),
        sa.Column("prerequisite_competencies", sa.JSON(), nullable=False),
        sa.Column("competency_tags", sa.JSON(), nullable=False),
        sa.Column("initial_state", sa.String(), nullable=False),
        sa.Column("states_json", sa.JSON(), nullable=False),
        sa.Column("patient_info_json", sa.JSON(), nullable=False),
        sa.Column("source_payload", sa.JSON(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("archived_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_case_definitions_case_id", "case_definitions", ["case_id"], unique=True)
    op.create_index("ix_case_definitions_is_active", "case_definitions", ["is_active"], unique=False)
    op.create_index("ix_case_definitions_is_archived", "case_definitions", ["is_archived"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("case_definitions"):
        return

    op.drop_table("case_definitions")
