"""Sprint 14-B S14B-2: learning curve service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import (
    Base,
    GradingStatus,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
)
from app.services.learning_curve_service import build_learning_curves, MASTERY_THRESHOLD


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


def _add_question(db, *, topic_id: str, q_id: str) -> Question:
    q = Question(
        question_id=q_id,
        question_type=QuestionType.MCQ,
        question_text=f"Q {q_id}",
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


def _add_answer(db, *, attempt, question, score: int) -> QuizAnswer:
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


def _seed_many_correct(db, n: int = 8, topic_id: str = "periodontitis"):
    """Seed n correct answers to give the fitter enough points."""
    q = _add_question(db, topic_id=topic_id, q_id=f"q_{topic_id}_01")
    attempt = QuizAttempt(user_id="stu_lc", total_score=n * 10, max_score=n * 10)
    db.add(attempt)
    db.flush()
    for _ in range(n):
        _add_answer(db, attempt=attempt, question=q, score=10)
    db.commit()


def _seed_mixed(db, topic_id: str = "oscc"):
    """Alternating correct/incorrect to create a realistic accuracy curve."""
    q = _add_question(db, topic_id=topic_id, q_id=f"q_{topic_id}_02")
    attempt = QuizAttempt(user_id="stu_mixed", total_score=50, max_score=80)
    db.add(attempt)
    db.flush()
    for i in range(8):
        score = 10 if i % 2 == 0 else 2
        _add_answer(db, attempt=attempt, question=q, score=score)
    db.commit()


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_returns_topics(db):
    _seed_many_correct(db)
    result = build_learning_curves(user_id="stu_lc", db=db)
    assert len(result["topics"]) == 1
    assert result["topics"][0]["topic_id"] == "periodontitis"


def test_observed_accuracy_present(db):
    _seed_many_correct(db)
    result = build_learning_curves(user_id="stu_lc", db=db)
    obs = result["topics"][0]["observed_accuracy"]
    assert len(obs) == 8
    # All correct → cumulative accuracy should be 1.0 throughout
    for pt in obs:
        assert pt["cumulative_accuracy"] == 1.0


def test_fit_model_present(db):
    _seed_many_correct(db)
    result = build_learning_curves(user_id="stu_lc", db=db)
    fit = result["topics"][0]["fit"]
    assert fit["model"] in ("exponential", "power_law")
    assert fit["r_squared"] is not None
    assert 0.0 <= fit["r_squared"] <= 1.0


def test_fitted_curve_non_empty(db):
    _seed_many_correct(db)
    result = build_learning_curves(user_id="stu_lc", db=db)
    fit = result["topics"][0]["fit"]
    assert len(fit["fitted_curve"]) > 0
    for pt in fit["fitted_curve"]:
        assert 0.0 <= pt["predicted"] <= 1.0


def test_mastery_threshold_in_fit(db):
    _seed_many_correct(db)
    result = build_learning_curves(user_id="stu_lc", db=db)
    fit = result["topics"][0]["fit"]
    assert fit["mastery_threshold"] == MASTERY_THRESHOLD


def test_topic_filter(db):
    _seed_many_correct(db, topic_id="periodontitis")
    _seed_mixed(db, topic_id="oscc")
    # mixed uses different user; seed periodontitis for same user for filter test
    result = build_learning_curves(user_id="stu_lc", db=db, topic_id="periodontitis")
    assert len(result["topics"]) == 1
    assert result["topics"][0]["topic_id"] == "periodontitis"


def test_empty_user(db):
    result = build_learning_curves(user_id="nobody", db=db)
    assert result["topics"] == []


def test_too_few_points_returns_note(db):
    """With < MIN_POINTS_FOR_FIT observations the fit should include a note."""
    q = _add_question(db, topic_id="herpes", q_id="q_herpes_lc")
    attempt = QuizAttempt(user_id="stu_few", total_score=10, max_score=10)
    db.add(attempt)
    db.flush()
    _add_answer(db, attempt=attempt, question=q, score=10)  # only 1 obs
    db.commit()

    result = build_learning_curves(user_id="stu_few", db=db)
    fit = result["topics"][0]["fit"]
    assert fit["model"] is None
    assert "note" in fit


def test_all_correct_projection_already_reached(db):
    """All-correct trajectory → mastery already ≥ threshold → projection ≤ current n."""
    _seed_many_correct(db, n=10)
    result = build_learning_curves(user_id="stu_lc", db=db)
    fit = result["topics"][0]["fit"]
    # Projection may be None (already past threshold) or a small number
    if fit["projected_trials_to_mastery"] is not None:
        assert fit["projected_trials_to_mastery"] <= 10 + 1
