"""Import OE/MCQ questions into the database with validation and upsert."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from db.database import Question, QuestionType

DEFAULT_SQLITE_DB_PATH = PROJECT_ROOT / "db" / "runtime" / "dentai_app.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_DB_PATH.as_posix()}"

REQUIRED_FIELDS = {
    "question_id",
    "question_type",
    "question_text",
    "topic_id",
    "difficulty",
    "bloom_level",
    "safety_category",
}
ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
ALLOWED_TYPES = {"MCQ", "OPEN_ENDED"}
ALLOWED_BLOOM_LEVELS = {"remember", "understand", "apply", "analyze", "evaluate", "create"}


class QuestionImportValidationError(ValueError):
    pass


@dataclass
class ImportReport:
    added: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _resolve_database_url(database_url: str | None) -> str:
    if database_url:
        return database_url
    return os.getenv("DENTAI_DATABASE_URL") or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


def _build_session_factory(database_url: str) -> sessionmaker:
    connect_args: dict[str, Any] = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    engine = create_engine(database_url, connect_args=connect_args)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def load_questions(questions_file: Path) -> list[dict[str, Any]]:
    with open(questions_file, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, list):
        raise QuestionImportValidationError("Payload must be a top-level JSON array")
    return payload


def validate_question(q: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    missing = sorted(REQUIRED_FIELDS - set(q.keys()))
    if missing:
        errors.append(f"missing fields: {', '.join(missing)}")

    qid = q.get("question_id")
    if not isinstance(qid, str) or not qid.strip():
        errors.append("question_id must be a non-empty string")

    qtype = q.get("question_type")
    if qtype not in ALLOWED_TYPES:
        errors.append(f"question_type must be one of: {', '.join(sorted(ALLOWED_TYPES))}")

    if not isinstance(q.get("question_text"), str) or not q["question_text"].strip():
        errors.append("question_text must be a non-empty string")

    if q.get("difficulty") not in ALLOWED_DIFFICULTIES:
        errors.append(f"difficulty must be one of: {', '.join(sorted(ALLOWED_DIFFICULTIES))}")

    bloom = q.get("bloom_level")
    if bloom not in ALLOWED_BLOOM_LEVELS:
        errors.append(f"bloom_level must be one of: {', '.join(sorted(ALLOWED_BLOOM_LEVELS))}")

    return errors


def _validate_all(questions: Iterable[dict[str, Any]]) -> list[str]:
    all_errors: list[str] = []
    for q in questions:
        qid = str(q.get("question_id", "<missing>")).strip() or "<missing>"
        errs = validate_question(q)
        for e in errs:
            all_errors.append(f"{qid}: {e}")
    return all_errors


def _apply_question_fields(model: Question, q: dict[str, Any]) -> None:
    model.question_type = QuestionType(q["question_type"])
    model.question_text = q["question_text"]
    model.topic_id = q.get("topic_id", "")
    model.difficulty = q.get("difficulty", "medium")
    model.bloom_level = q.get("bloom_level", "apply")
    model.safety_category = q.get("safety_category", "safe")
    model.max_score = q.get("max_score", 1)
    model.rubric_guide = q.get("rubric_guide")
    model.model_answer_outline = q.get("model_answer_outline")
    model.options_json = q.get("options_json")
    model.correct_option = q.get("correct_option")
    model.instructor_explanation = q.get("instructor_explanation")
    model.unit_id = q.get("unit_id")
    model.week_number = q.get("week_number")
    model.competency_areas = q.get("competency_areas", [])


def import_questions(
    db: Session,
    questions: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    upsert: bool = False,
) -> ImportReport:
    inspector = sa.inspect(db.bind)
    if not inspector.has_table("questions"):
        raise RuntimeError("questions table not found. Run 'alembic upgrade head' first.")

    validation_errors = _validate_all(questions)
    if validation_errors:
        return ImportReport(errors=validation_errors)

    report = ImportReport()

    for q in questions:
        qid = q["question_id"].strip()
        existing = db.query(Question).filter(Question.question_id == qid).first()

        if existing is None:
            report.added += 1
            if not dry_run:
                model = Question(question_id=qid)
                _apply_question_fields(model, q)
                db.add(model)
        elif upsert:
            report.updated += 1
            if not dry_run:
                _apply_question_fields(existing, q)
        else:
            report.skipped += 1

    if not dry_run:
        db.commit()

    return report


def run_import(
    questions_file: Path,
    database_url: str | None,
    *,
    dry_run: bool = False,
    upsert: bool = False,
) -> ImportReport:
    session_factory = _build_session_factory(_resolve_database_url(database_url))
    questions = load_questions(questions_file)
    db = session_factory()
    try:
        return import_questions(db, questions, dry_run=dry_run, upsert=upsert)
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import questions (OE or MCQ) into the question bank"
    )
    parser.add_argument(
        "--file",
        default=str(BACKEND_ROOT / "data" / "sample_oe_questions.json"),
        help="Path to questions JSON file",
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
    parser.add_argument(
        "--upsert",
        action="store_true",
        help="Update existing questions instead of skipping",
    )
    args = parser.parse_args()

    questions_file = Path(args.file)
    if not questions_file.exists():
        print(f"ERROR: file not found: {questions_file}")
        return 1

    report = run_import(
        questions_file=questions_file,
        database_url=args.database_url,
        dry_run=args.dry_run,
        upsert=args.upsert,
    )

    if report.errors:
        print("Validation errors:")
        for e in report.errors:
            print(f"  - {e}")
        return 1

    mode = "DRY-RUN" if args.dry_run else "APPLY"
    print(f"[{mode}] added={report.added} updated={report.updated} skipped={report.skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
