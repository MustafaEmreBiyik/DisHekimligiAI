"""Import canonical case definitions into the database with validation and upsert."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import CaseDefinition


DEFAULT_SQLITE_DB_PATH = PROJECT_ROOT / "db" / "runtime" / "dentai_app.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_DB_PATH.as_posix()}"
REQUIRED_FIELDS = {
    "case_id",
    "schema_version",
    "title",
    "category",
    "difficulty",
    "estimated_duration_minutes",
    "is_active",
    "learning_objectives",
    "prerequisite_competencies",
    "competency_tags",
    "initial_state",
    "states",
    "patient_info",
}
ALLOWED_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


@dataclass
class ImportReport:
    added: int = 0
    updated: int = 0
    skipped: int = 0


class CaseImportValidationError(ValueError):
    """Raised when canonical case schema validation fails."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _resolve_database_url(database_url: str | None) -> str:
    if database_url:
        return database_url
    return os.getenv("DENTAI_DATABASE_URL", DEFAULT_DATABASE_URL)


def _build_session_factory(database_url: str) -> sessionmaker:
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(database_url, connect_args=connect_args)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def load_cases(cases_file: Path) -> list[dict[str, Any]]:
    with open(cases_file, "r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise CaseImportValidationError("case_scenarios payload must be a top-level list")

    return payload


def validate_case_payload(case_payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing_fields = sorted(REQUIRED_FIELDS.difference(case_payload.keys()))
    if missing_fields:
        errors.append(f"missing fields: {', '.join(missing_fields)}")

    case_id = case_payload.get("case_id")
    if not isinstance(case_id, str) or not case_id.strip():
        errors.append("case_id must be a non-empty string")

    if case_payload.get("schema_version") != "2.0":
        errors.append("schema_version must be '2.0'")

    difficulty = case_payload.get("difficulty")
    if difficulty not in ALLOWED_DIFFICULTIES:
        errors.append(
            "difficulty must be one of: beginner, intermediate, advanced"
        )

    estimated_duration = case_payload.get("estimated_duration_minutes")
    if not isinstance(estimated_duration, int) or estimated_duration <= 0:
        errors.append("estimated_duration_minutes must be a positive integer")

    if not isinstance(case_payload.get("is_active"), bool):
        errors.append("is_active must be a boolean")

    if not isinstance(case_payload.get("states"), dict):
        errors.append("states must be an object")

    if not isinstance(case_payload.get("patient_info"), dict):
        errors.append("patient_info must be an object")

    for list_field in (
        "learning_objectives",
        "prerequisite_competencies",
        "competency_tags",
    ):
        field_value = case_payload.get(list_field)
        if not isinstance(field_value, list) or not all(
            isinstance(item, str) and item.strip() for item in field_value
        ):
            errors.append(f"{list_field} must be a non-empty string list")

    return errors


def _apply_case_payload(model: CaseDefinition, case_payload: dict[str, Any]) -> None:
    model.schema_version = case_payload["schema_version"]
    model.title = case_payload["title"]
    model.category = case_payload["category"]
    model.difficulty = case_payload["difficulty"]
    model.estimated_duration_minutes = case_payload["estimated_duration_minutes"]
    model.is_active = case_payload["is_active"]
    model.learning_objectives = case_payload["learning_objectives"]
    model.prerequisite_competencies = case_payload["prerequisite_competencies"]
    model.competency_tags = case_payload["competency_tags"]
    model.initial_state = case_payload["initial_state"]
    model.states_json = case_payload["states"]
    model.patient_info_json = case_payload["patient_info"]
    model.source_payload = case_payload


def _validate_all_cases(case_payloads: Iterable[dict[str, Any]]) -> None:
    errors: list[str] = []

    for case_payload in case_payloads:
        case_id = str(case_payload.get("case_id", "<missing>")).strip() or "<missing>"
        case_errors = validate_case_payload(case_payload)
        for case_error in case_errors:
            errors.append(f"{case_id}: {case_error}")

    if errors:
        details = "\n".join(f"- {line}" for line in errors)
        raise CaseImportValidationError(
            "Canonical case schema validation failed:\n" + details
        )


def import_cases(
    db: Session,
    case_payloads: list[dict[str, Any]],
    dry_run: bool = False,
) -> ImportReport:
    inspector = sa.inspect(db.bind)
    if not inspector.has_table("case_definitions"):
        raise RuntimeError(
            "case_definitions table not found. Run 'alembic upgrade head' first."
        )

    _validate_all_cases(case_payloads)

    report = ImportReport()

    for case_payload in case_payloads:
        case_id = case_payload["case_id"].strip()
        existing = (
            db.query(CaseDefinition)
            .filter(CaseDefinition.case_id == case_id)
            .first()
        )

        if existing is None:
            report.added += 1
            if not dry_run:
                model = CaseDefinition(case_id=case_id)
                _apply_case_payload(model, case_payload)
                db.add(model)
            continue

        existing_payload = existing.source_payload or {}
        if _canonical_json(existing_payload) == _canonical_json(case_payload):
            report.skipped += 1
            continue

        report.updated += 1
        if not dry_run:
            _apply_case_payload(existing, case_payload)

    if not dry_run:
        db.commit()

    return report


def run_import(cases_file: Path, database_url: str | None, dry_run: bool) -> ImportReport:
    session_factory = _build_session_factory(_resolve_database_url(database_url))
    case_payloads = load_cases(cases_file)

    db = session_factory()
    try:
        return import_cases(db=db, case_payloads=case_payloads, dry_run=dry_run)
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import normalized canonical case payloads into case_definitions"
    )
    parser.add_argument(
        "--cases-file",
        default="data/case_scenarios.json",
        help="Path to canonical case_scenarios JSON file",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional database URL override",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report without writing to DB",
    )
    args = parser.parse_args()

    cases_file = Path(args.cases_file)
    if not cases_file.exists():
        raise FileNotFoundError(f"cases file not found: {cases_file}")

    report = run_import(
        cases_file=cases_file,
        database_url=args.database_url,
        dry_run=args.dry_run,
    )

    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"[{mode}] added={report.added} updated={report.updated} skipped={report.skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
