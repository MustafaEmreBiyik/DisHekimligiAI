"""Merge branch1 (48d32c8e65ec) and branch2 (k6f0i8j15e32) into single head.

Branch 1 ends at: 48d32c8e65ec (S8B quiz+question models)
Branch 2 ends at: k6f0i8j15e32 (S10-C review schedules)

Revision ID: m8h2k0l37g54
Revises: 48d32c8e65ec, k6f0i8j15e32
Create Date: 2026-05-31

"""
from alembic import op

revision = "m8h2k0l37g54"
down_revision = ("48d32c8e65ec", "k6f0i8j15e32")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
