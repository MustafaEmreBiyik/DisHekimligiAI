"""
Unit tests for rubric_version_service (T-4B)
=============================================
All DB interactions use an in-memory SQLite database so no files or
network connections are required.
"""
from __future__ import annotations

import datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# We import Base and the models we need after patching the engine
from db.database import Base, Question, QuizAnswer, RubricVersion, QuizAttempt
from db.database import QuestionType, GradingStatus

from app.services.rubric_version_service import (
    RubricVersionError,
    RubricVersionInfo,
    snapshot_rubric,
    get_rubric_versions,
    get_rubric_version,
    get_current_rubric_version_id,
    stamp_answer_rubric_version,
)


# ---------------------------------------------------------------------------
# Test DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db():
    """Provide an isolated in-memory SQLite session for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_question(db, rubric_guide="Rubrik A", model_answer="Model A") -> Question:
    """Insert a minimal Question row and return it."""
    q = Question(
        question_id="Q-TEST-001",
        question_type=QuestionType.OPEN_ENDED,
        question_text="Test sorusu?",
        topic_id="oral_pathology",
        competency_areas=["diagnosis"],
        bloom_level="analysis",
        difficulty="medium",
        safety_category="standard",
        rubric_guide=rubric_guide,
        model_answer_outline=model_answer,
        max_score=10,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def _make_attempt(db, user_id="student-1") -> QuizAttempt:
    attempt = QuizAttempt(
        user_id=user_id,
        total_score=0,
        max_score=10,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def _make_answer(db, attempt_id: int, question_id: int) -> QuizAnswer:
    answer = QuizAnswer(
        attempt_id=attempt_id,
        question_id=question_id,
        student_response_text="Öğrenci cevabı.",
        grading_status=GradingStatus.PENDING,
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)
    return answer


# ---------------------------------------------------------------------------
# TestSnapshotRubric
# ---------------------------------------------------------------------------

class TestSnapshotRubric:
    def test_returns_rubric_version_info(self, db):
        q = _make_question(db)
        result = snapshot_rubric(
            db, question_id=q.id,
            rubric_guide="Yeni Rubrik", model_answer_outline="Yeni Model",
            change_notes="İlk versiyon", created_by="hoca@dentai.edu",
        )
        assert isinstance(result, RubricVersionInfo)

    def test_version_starts_at_one(self, db):
        q = _make_question(db)
        result = snapshot_rubric(
            db, question_id=q.id,
            rubric_guide="R", model_answer_outline="M",
            change_notes=None, created_by="hoca@dentai.edu",
        )
        assert result.version == 1

    def test_second_snapshot_increments_version(self, db):
        q = _make_question(db)
        snapshot_rubric(db, question_id=q.id, rubric_guide="R1", model_answer_outline="M1",
                        change_notes=None, created_by="hoca@dentai.edu")
        result2 = snapshot_rubric(db, question_id=q.id, rubric_guide="R2", model_answer_outline="M2",
                                  change_notes="Güncelleme", created_by="hoca@dentai.edu")
        assert result2.version == 2

    def test_question_rubric_guide_updated(self, db):
        q = _make_question(db, rubric_guide="Eski Rubrik")
        snapshot_rubric(db, question_id=q.id, rubric_guide="Yeni Rubrik", model_answer_outline="M",
                        change_notes=None, created_by="hoca@dentai.edu")
        db.refresh(q)
        assert q.rubric_guide == "Yeni Rubrik"

    def test_question_model_answer_updated(self, db):
        q = _make_question(db, model_answer="Eski Model")
        snapshot_rubric(db, question_id=q.id, rubric_guide="R", model_answer_outline="Yeni Model",
                        change_notes=None, created_by="hoca@dentai.edu")
        db.refresh(q)
        assert q.model_answer_outline == "Yeni Model"

    def test_question_current_rubric_version_updated(self, db):
        q = _make_question(db)
        snapshot_rubric(db, question_id=q.id, rubric_guide="R", model_answer_outline="M",
                        change_notes=None, created_by="hoca@dentai.edu")
        db.refresh(q)
        assert q.current_rubric_version == 1

    def test_change_notes_stored(self, db):
        q = _make_question(db)
        result = snapshot_rubric(db, question_id=q.id, rubric_guide="R", model_answer_outline="M",
                                 change_notes="Kritik kriter eklendi.", created_by="hoca@dentai.edu")
        assert result.change_notes == "Kritik kriter eklendi."

    def test_none_change_notes_accepted(self, db):
        q = _make_question(db)
        result = snapshot_rubric(db, question_id=q.id, rubric_guide="R", model_answer_outline="M",
                                 change_notes=None, created_by="hoca@dentai.edu")
        assert result.change_notes is None

    def test_created_by_stored(self, db):
        q = _make_question(db)
        result = snapshot_rubric(db, question_id=q.id, rubric_guide="R", model_answer_outline="M",
                                 change_notes=None, created_by="prof@dentai.edu")
        assert result.created_by == "prof@dentai.edu"

    def test_created_at_is_iso_string(self, db):
        q = _make_question(db)
        result = snapshot_rubric(db, question_id=q.id, rubric_guide="R", model_answer_outline="M",
                                 change_notes=None, created_by="hoca@dentai.edu")
        assert result.created_at.endswith("Z")

    def test_invalid_question_id_raises(self, db):
        with pytest.raises(RubricVersionError, match="not found"):
            snapshot_rubric(db, question_id=9999, rubric_guide="R", model_answer_outline="M",
                            change_notes=None, created_by="hoca@dentai.edu")

    def test_rubric_guide_stripped(self, db):
        q = _make_question(db)
        result = snapshot_rubric(db, question_id=q.id, rubric_guide="  Stripped  ",
                                 model_answer_outline="M", change_notes=None, created_by="h@d.edu")
        assert result.rubric_guide == "Stripped"

    def test_model_answer_stripped(self, db):
        q = _make_question(db)
        result = snapshot_rubric(db, question_id=q.id, rubric_guide="R",
                                 model_answer_outline="  Model  ", change_notes=None, created_by="h@d.edu")
        assert result.model_answer_outline == "Model"


# ---------------------------------------------------------------------------
# TestGetRubricVersions
# ---------------------------------------------------------------------------

class TestGetRubricVersions:
    def test_empty_list_before_any_snapshot(self, db):
        q = _make_question(db)
        results = get_rubric_versions(db, question_id=q.id)
        assert results == []

    def test_returns_list_of_rubric_version_info(self, db):
        q = _make_question(db)
        snapshot_rubric(db, question_id=q.id, rubric_guide="R1", model_answer_outline="M1",
                        change_notes=None, created_by="h@d.edu")
        results = get_rubric_versions(db, question_id=q.id)
        assert len(results) == 1
        assert isinstance(results[0], RubricVersionInfo)

    def test_two_snapshots_returned(self, db):
        q = _make_question(db)
        snapshot_rubric(db, question_id=q.id, rubric_guide="R1", model_answer_outline="M",
                        change_notes=None, created_by="h@d.edu")
        snapshot_rubric(db, question_id=q.id, rubric_guide="R2", model_answer_outline="M",
                        change_notes=None, created_by="h@d.edu")
        results = get_rubric_versions(db, question_id=q.id)
        assert len(results) == 2

    def test_newest_first_ordering(self, db):
        q = _make_question(db)
        snapshot_rubric(db, question_id=q.id, rubric_guide="R1", model_answer_outline="M",
                        change_notes=None, created_by="h@d.edu")
        snapshot_rubric(db, question_id=q.id, rubric_guide="R2", model_answer_outline="M",
                        change_notes=None, created_by="h@d.edu")
        results = get_rubric_versions(db, question_id=q.id)
        assert results[0].version == 2  # newest first
        assert results[1].version == 1

    def test_invalid_question_raises(self, db):
        with pytest.raises(RubricVersionError, match="not found"):
            get_rubric_versions(db, question_id=9999)


# ---------------------------------------------------------------------------
# TestGetRubricVersion
# ---------------------------------------------------------------------------

class TestGetRubricVersion:
    def test_returns_correct_snapshot(self, db):
        q = _make_question(db)
        created = snapshot_rubric(db, question_id=q.id, rubric_guide="Unique Guide",
                                  model_answer_outline="M", change_notes=None, created_by="h@d.edu")
        fetched = get_rubric_version(db, version_id=created.id)
        assert fetched.id == created.id
        assert fetched.rubric_guide == "Unique Guide"

    def test_not_found_raises(self, db):
        with pytest.raises(RubricVersionError, match="not found"):
            get_rubric_version(db, version_id=99999)

    def test_question_id_preserved(self, db):
        q = _make_question(db)
        created = snapshot_rubric(db, question_id=q.id, rubric_guide="R",
                                  model_answer_outline="M", change_notes=None, created_by="h@d.edu")
        fetched = get_rubric_version(db, version_id=created.id)
        assert fetched.question_id == q.id


# ---------------------------------------------------------------------------
# TestGetCurrentRubricVersionId
# ---------------------------------------------------------------------------

class TestGetCurrentRubricVersionId:
    def test_returns_none_before_any_snapshot(self, db):
        q = _make_question(db)
        result = get_current_rubric_version_id(db, question_id=q.id)
        assert result is None

    def test_returns_id_after_first_snapshot(self, db):
        q = _make_question(db)
        rv = snapshot_rubric(db, question_id=q.id, rubric_guide="R", model_answer_outline="M",
                             change_notes=None, created_by="h@d.edu")
        result = get_current_rubric_version_id(db, question_id=q.id)
        assert result == rv.id

    def test_returns_latest_after_multiple_snapshots(self, db):
        q = _make_question(db)
        snapshot_rubric(db, question_id=q.id, rubric_guide="R1", model_answer_outline="M",
                        change_notes=None, created_by="h@d.edu")
        rv2 = snapshot_rubric(db, question_id=q.id, rubric_guide="R2", model_answer_outline="M",
                              change_notes=None, created_by="h@d.edu")
        result = get_current_rubric_version_id(db, question_id=q.id)
        assert result == rv2.id


# ---------------------------------------------------------------------------
# TestStampAnswerRubricVersion
# ---------------------------------------------------------------------------

class TestStampAnswerRubricVersion:
    def test_stamps_answer_with_rubric_version_id(self, db):
        q = _make_question(db)
        attempt = _make_attempt(db)
        answer = _make_answer(db, attempt.id, q.id)
        rv = snapshot_rubric(db, question_id=q.id, rubric_guide="R", model_answer_outline="M",
                             change_notes=None, created_by="h@d.edu")

        stamp_answer_rubric_version(db, answer_id=answer.id, rubric_version_id=rv.id)
        db.refresh(answer)
        assert answer.rubric_version_id == rv.id

    def test_missing_answer_does_not_raise(self, db):
        """stamp_answer_rubric_version is a no-op for non-existent answers."""
        stamp_answer_rubric_version(db, answer_id=99999, rubric_version_id=1)

    def test_stamp_can_be_updated(self, db):
        """If called twice, the second stamp overwrites the first."""
        q = _make_question(db)
        attempt = _make_attempt(db)
        answer = _make_answer(db, attempt.id, q.id)
        rv1 = snapshot_rubric(db, question_id=q.id, rubric_guide="R1", model_answer_outline="M",
                              change_notes=None, created_by="h@d.edu")
        rv2 = snapshot_rubric(db, question_id=q.id, rubric_guide="R2", model_answer_outline="M",
                              change_notes=None, created_by="h@d.edu")

        stamp_answer_rubric_version(db, answer_id=answer.id, rubric_version_id=rv1.id)
        stamp_answer_rubric_version(db, answer_id=answer.id, rubric_version_id=rv2.id)
        db.refresh(answer)
        assert answer.rubric_version_id == rv2.id
