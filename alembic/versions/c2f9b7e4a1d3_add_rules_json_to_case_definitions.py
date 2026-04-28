"""add_rules_json_to_case_definitions

Revision ID: c2f9b7e4a1d3
Revises: b7d42a1f63e2
Create Date: 2026-04-27 13:25:00.000000

"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2f9b7e4a1d3"
down_revision: Union[str, Sequence[str], None] = "b7d42a1f63e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _load_legacy_rules() -> dict[str, list[dict]]:
    rules_path = Path(__file__).resolve().parents[2] / "data" / "scoring_rules.json"
    if not rules_path.exists():
        return {}

    try:
        payload = json.loads(rules_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if not isinstance(payload, list):
        return {}

    legacy_rules: dict[str, list[dict]] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue

        case_id = str(item.get("case_id") or "").strip()
        rules = item.get("rules")
        if case_id and isinstance(rules, list):
            legacy_rules[case_id] = [rule for rule in rules if isinstance(rule, dict)]

    return legacy_rules


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("case_definitions"):
        return

    columns = {column["name"] for column in inspector.get_columns("case_definitions")}
    if "rules_json" not in columns:
        op.add_column(
            "case_definitions",
            sa.Column("rules_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )

    legacy_rules = _load_legacy_rules()
    case_definitions = sa.table(
        "case_definitions",
        sa.column("id", sa.Integer()),
        sa.column("case_id", sa.String()),
        sa.column("source_payload", sa.JSON()),
        sa.column("rules_json", sa.JSON()),
    )

    rows = bind.execute(
        sa.select(
            case_definitions.c.id,
            case_definitions.c.case_id,
            case_definitions.c.source_payload,
            case_definitions.c.rules_json,
        )
    ).mappings()

    for row in rows:
        stored_rules = row.get("rules_json")
        normalized_rules: list[dict] | None = None

        if isinstance(stored_rules, list) and any(isinstance(rule, dict) for rule in stored_rules):
            normalized_rules = [rule for rule in stored_rules if isinstance(rule, dict)]
        else:
            source_payload = row.get("source_payload")
            if isinstance(source_payload, dict) and isinstance(source_payload.get("rules"), list):
                normalized_rules = [
                    rule for rule in source_payload.get("rules", [])
                    if isinstance(rule, dict)
                ]
            else:
                normalized_rules = legacy_rules.get(str(row.get("case_id") or "").strip(), [])

        bind.execute(
            case_definitions.update()
            .where(case_definitions.c.id == row["id"])
            .values(rules_json=normalized_rules or [])
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("case_definitions"):
        return

    columns = {column["name"] for column in inspector.get_columns("case_definitions")}
    if "rules_json" in columns:
        op.drop_column("case_definitions", "rules_json")
