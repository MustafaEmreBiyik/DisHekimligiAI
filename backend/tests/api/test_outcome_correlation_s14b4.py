"""Sprint 14-B S14B-4: quiz↔case outcome correlation service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import (
    Base,
    ExamResult,
    GradingStatus,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
    User,
    UserRole,
)
from app.services.outcome_correlation_service import build_outcome_correlation, _pearson


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _add_student(db, user_id: str, name: str) -> User:
    u = User(
        user_id=user_id,
        display_name=name,
        email=f"{user_id}@test.com",
        hashed_password="x",
        role=UserRole.STUDENT,
        is_archived=False,
    )
    db.add(u)
    db.flush()
    return u


def _add_quiz_score(db, user_id: str, earned: int, max_score: int) -> None:
    q = Question(
        question_id=f"q_{user_id}",
        question_type=QuestionType.MCQ,
        question_text="Q",
        topic_id="test_topic",
        max_score=max_score,
        bloom_level="comprehension",
        difficulty="easy",
        safety_category="low",
        correct_option="A",
        competency_areas=[],
    )
    db.add(q)
    db.flush()
    attempt = QuizAttempt(user_id=user_id, total_score=earned, max_score=max_score)
    db.add(attempt)
    db.flush()
    answer = QuizAnswer(
        attempt_id=attempt.id,
        question_id=q.id,
        student_response_text="A",
        auto_score=earned,
        grading_status=GradingStatus.PUBLISHED,
    )
    db.add(answer)
    db.flush()


def _add_case_score(db, user_id: str, score: int, max_score: int) -> None:
    db.add(ExamResult(user_id=user_id, case_id="case_001", score=score, max_score=max_score))
    db.flush()


# ── Unit tests for _pearson ────────────────────────────────────────────────────

def test_pearson_perfect_positive():
    r = _pearson([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert r is not None
    assert abs(r - 1.0) < 0.001


def test_pearson_perfect_negative():
    r = _pearson([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
    assert r is not None
    assert abs(r - (-1.0)) < 0.001


def test_pearson_too_few_points():
    assert _pearson([1.0, 2.0], [1.0, 2.0]) is None


# ── Integration tests ──────────────────────────────────────────────────────────

def test_returns_all_students(db):
    _add_student(db, "s1", "Ali")
    _add_student(db, "s2", "Zeynep")
    db.commit()
    result = build_outcome_correlation(db=db)
    assert len(result["students"]) == 2


def test_no_data_gives_none_r(db):
    _add_student(db, "s1", "Ali")
    db.commit()
    result = build_outcome_correlation(db=db)
    assert result["pearson_r"] is None
    assert result["n_paired"] == 0


def test_students_with_both_scores_paired(db):
    for uid, name, q, c in [("s1", "Ali", 90, 80), ("s2", "Zeynep", 70, 65), ("s3", "Mert", 50, 45)]:
        _add_student(db, uid, name)
        _add_quiz_score(db, uid, q, 100)
        _add_case_score(db, uid, c, 100)
    db.commit()
    result = build_outcome_correlation(db=db)
    assert result["n_paired"] == 3
    assert result["pearson_r"] is not None
    assert -1.0 <= result["pearson_r"] <= 1.0


def test_student_missing_case_not_paired(db):
    _add_student(db, "s1", "Ali")
    _add_quiz_score(db, "s1", 80, 100)
    # no case score for s1
    db.commit()
    result = build_outcome_correlation(db=db)
    s1 = next(s for s in result["students"] if s["user_id"] == "s1")
    assert s1["quiz_pct"] is not None
    assert s1["case_pct"] is None
    assert result["n_paired"] == 0


def test_interpretation_present(db):
    result = build_outcome_correlation(db=db)
    assert isinstance(result["interpretation"], str)
    assert len(result["interpretation"]) > 0


def test_archived_students_excluded(db):
    archived = User(
        user_id="s_arch",
        display_name="Silindi",
        email="arch@test.com",
        hashed_password="x",
        role=UserRole.STUDENT,
        is_archived=True,
    )
    db.add(archived)
    db.commit()
    result = build_outcome_correlation(db=db)
    assert all(s["user_id"] != "s_arch" for s in result["students"])
