"""Sprint 14-B S14B-1: mastery trajectory service + endpoint tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import (
    Base,
    GradingStatus,
    MasteryState,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
)
from app.services.mastery_trajectory_service import build_trajectory


# ── In-memory DB fixture ───────────────────────────────────────────────────────

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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _add_question(db, *, topic_id: str, q_id: str) -> Question:
    q = Question(
        question_id=q_id,
        question_type=QuestionType.MCQ,
        question_text=f"Question {q_id}",
        topic_id=topic_id,
        max_score=10,
        bloom_level="comprehension",
        difficulty="easy",
        safety_category="low",
        correct_option="A",
        competency_areas=[],
    )
    db.add(q)
    db.flush()
    return q


def _add_answer(db, *, attempt: QuizAttempt, question: Question, score: int) -> QuizAnswer:
    a = QuizAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        student_response_text="A",
        auto_score=score,
        grading_status=GradingStatus.PUBLISHED,
    )
    db.add(a)
    db.flush()
    return a


def _seed(db, user_id: str = "stu_test"):
    """Two topics: one correct (score=9), one incorrect (score=2)."""
    q_perio = _add_question(db, topic_id="periodontitis", q_id="q_perio_01")
    q_oscc = _add_question(db, topic_id="oscc", q_id="q_oscc_01")

    attempt = QuizAttempt(user_id=user_id, total_score=11, max_score=20)
    db.add(attempt)
    db.flush()

    _add_answer(db, attempt=attempt, question=q_perio, score=9)   # correct (9 >= 5)
    _add_answer(db, attempt=attempt, question=q_oscc, score=2)    # incorrect (2 < 5)
    db.commit()


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_trajectory_returns_both_topics(db):
    _seed(db)
    result = build_trajectory(user_id="stu_test", db=db)
    topic_ids = {t["topic_id"] for t in result["topics"]}
    assert "periodontitis" in topic_ids
    assert "oscc" in topic_ids


def test_trajectory_has_ci_bands(db):
    _seed(db)
    result = build_trajectory(user_id="stu_test", db=db)
    for topic in result["topics"]:
        assert len(topic["points"]) >= 1
        pt = topic["points"][0]
        assert "ci_lower" in pt
        assert "ci_upper" in pt
        assert pt["ci_lower"] <= pt["mastery"] <= pt["ci_upper"]


def test_ci_bounds_valid(db):
    _seed(db)
    result = build_trajectory(user_id="stu_test", db=db)
    for topic in result["topics"]:
        for pt in topic["points"]:
            assert 0.0 <= pt["ci_lower"] <= 1.0
            assert 0.0 <= pt["ci_upper"] <= 1.0
            assert pt["ci_lower"] <= pt["ci_upper"]


def test_topic_filter(db):
    _seed(db)
    result = build_trajectory(user_id="stu_test", db=db, topic_id="oscc")
    assert len(result["topics"]) == 1
    assert result["topics"][0]["topic_id"] == "oscc"


def test_empty_for_new_user(db):
    result = build_trajectory(user_id="no_such_student", db=db)
    assert result["topics"] == []


def test_correct_flag_true(db):
    _seed(db)
    result = build_trajectory(user_id="stu_test", db=db, topic_id="periodontitis")
    pt = result["topics"][0]["points"][0]
    assert pt["correct"] is True   # score=9 >= 10*0.5=5


def test_correct_flag_false(db):
    _seed(db)
    result = build_trajectory(user_id="stu_test", db=db, topic_id="oscc")
    pt = result["topics"][0]["points"][0]
    assert pt["correct"] is False  # score=2 < 10*0.5=5


def test_mastery_increases_on_correct(db):
    """Consecutive correct answers should monotonically raise mastery."""
    q = _add_question(db, topic_id="herpes", q_id="q_herpes_01")
    attempt = QuizAttempt(user_id="stu_mono", total_score=30, max_score=30)
    db.add(attempt)
    db.flush()
    for _ in range(3):
        _add_answer(db, attempt=attempt, question=q, score=10)
    db.commit()

    result = build_trajectory(user_id="stu_mono", db=db)
    points = result["topics"][0]["points"]
    assert len(points) == 3
    masteries = [p["mastery"] for p in points]
    assert masteries[0] <= masteries[1] <= masteries[2]


def test_n_observations_count(db):
    _seed(db)
    result = build_trajectory(user_id="stu_test", db=db)
    for topic in result["topics"]:
        assert topic["n_observations"] == len(topic["points"])
