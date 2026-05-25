"""Tests for the question import script."""

import json
import pytest
from pathlib import Path

from db.database import Question, QuestionType

import sys
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.import_questions import (
    import_questions,
    validate_question,
    load_questions,
    ImportReport,
    QuestionImportValidationError,
)


def _make_valid_question(**overrides) -> dict:
    base = {
        "question_id": "Q-TEST-001",
        "question_type": "OPEN_ENDED",
        "question_text": "Test question text",
        "topic_id": "oral_pathology",
        "difficulty": "medium",
        "bloom_level": "apply",
        "safety_category": "safe",
        "max_score": 10,
    }
    base.update(overrides)
    return base


class TestValidation:
    def test_valid_question_passes(self):
        errors = validate_question(_make_valid_question())
        assert errors == []

    def test_missing_required_field(self):
        q = _make_valid_question()
        del q["question_id"]
        errors = validate_question(q)
        assert any("question_id" in e for e in errors)

    def test_invalid_difficulty(self):
        q = _make_valid_question(difficulty="extreme")
        errors = validate_question(q)
        assert any("difficulty" in e for e in errors)

    def test_invalid_question_type(self):
        q = _make_valid_question(question_type="ESSAY")
        errors = validate_question(q)
        assert any("question_type" in e for e in errors)

    def test_invalid_bloom_level(self):
        q = _make_valid_question(bloom_level="invent")
        errors = validate_question(q)
        assert any("bloom_level" in e for e in errors)


class TestImport:
    def test_add_new_questions(self, db):
        questions = [
            _make_valid_question(question_id="Q-001"),
            _make_valid_question(question_id="Q-002"),
        ]
        report = import_questions(db, questions)

        assert report.added == 2
        assert report.updated == 0
        assert report.skipped == 0
        assert report.errors == []
        assert db.query(Question).count() == 2

    def test_dry_run_does_not_persist(self, db):
        questions = [_make_valid_question(question_id="Q-DRY")]
        report = import_questions(db, questions, dry_run=True)

        assert report.added == 1
        assert db.query(Question).count() == 0

    def test_duplicate_without_upsert_skips(self, db):
        questions = [_make_valid_question(question_id="Q-DUP")]
        import_questions(db, questions)

        report = import_questions(db, questions, upsert=False)
        assert report.skipped == 1
        assert report.added == 0

    def test_duplicate_with_upsert_updates(self, db):
        questions = [_make_valid_question(question_id="Q-UPD", max_score=10)]
        import_questions(db, questions)

        updated = [_make_valid_question(question_id="Q-UPD", max_score=20)]
        report = import_questions(db, updated, upsert=True)

        assert report.updated == 1
        row = db.query(Question).filter(Question.question_id == "Q-UPD").first()
        assert row.max_score == 20

    def test_validation_errors_prevent_import(self, db):
        questions = [{"question_id": "Q-BAD"}]  # missing most fields
        report = import_questions(db, questions)

        assert len(report.errors) > 0
        assert report.added == 0
        assert db.query(Question).count() == 0


class TestLoadQuestions:
    def test_load_valid_json(self, tmp_path):
        f = tmp_path / "questions.json"
        f.write_text(json.dumps([_make_valid_question()]), encoding="utf-8")
        result = load_questions(f)
        assert len(result) == 1

    def test_load_non_array_raises(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text('{"not": "an array"}', encoding="utf-8")
        with pytest.raises(QuestionImportValidationError):
            load_questions(f)
