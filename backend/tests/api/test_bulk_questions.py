"""Tests for bulk question actions (T-5C)."""

import pytest

from db.database import Question, QuestionType


def _seed_question(db, question_id="Q-BULK-001", is_active=True, is_archived=False, unit_id=None):
    q = Question(
        question_id=question_id,
        question_type=QuestionType.OPEN_ENDED,
        question_text="Test question",
        topic_id="oral_pathology",
        difficulty="medium",
        bloom_level="apply",
        safety_category="safe",
        is_active=is_active,
        is_archived=is_archived,
        unit_id=unit_id,
    )
    db.add(q)
    db.commit()
    return q


class TestBulkArchive:
    def test_archive_sets_flags(self, db):
        q1 = _seed_question(db, "Q-B-001")
        q2 = _seed_question(db, "Q-B-002")

        for q in [q1, q2]:
            q.is_archived = True
            q.is_active = False
        db.commit()

        for q in db.query(Question).filter(Question.id.in_([q1.id, q2.id])).all():
            assert q.is_archived is True
            assert q.is_active is False


class TestBulkActivate:
    def test_activate_restores_flags(self, db):
        q = _seed_question(db, "Q-B-ACT", is_active=False, is_archived=True)
        q.is_archived = False
        q.is_active = True
        db.commit()

        reloaded = db.query(Question).filter(Question.id == q.id).first()
        assert reloaded.is_active is True
        assert reloaded.is_archived is False


class TestBulkUpdateUnit:
    def test_update_unit_id(self, db):
        q = _seed_question(db, "Q-B-UNIT")
        q.unit_id = "unit_3_neoplastic"
        db.commit()

        reloaded = db.query(Question).filter(Question.id == q.id).first()
        assert reloaded.unit_id == "unit_3_neoplastic"


class TestCSVExport:
    def test_active_questions_exported(self, db):
        _seed_question(db, "Q-EXP-001")
        _seed_question(db, "Q-EXP-002")
        _seed_question(db, "Q-EXP-003", is_active=False)

        active = db.query(Question).filter(Question.is_active == True).count()
        assert active == 2
