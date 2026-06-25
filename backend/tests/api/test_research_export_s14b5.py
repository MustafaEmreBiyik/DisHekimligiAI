"""Sprint 14-B S14B-5: research export ZIP and snapshot analytics tests."""

from __future__ import annotations

import io
import zipfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import (
    Base,
    ExamResult,
    GradingStatus,
    MasteryState,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
    User,
    UserRole,
)
from app.services.research_export_service import build_export_zip, TABLES
from app.services.research_snapshot_service import _collect_analytics_summary


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


def _add_student(db, uid: str, name: str) -> User:
    u = User(
        user_id=uid,
        display_name=name,
        email=f"{uid}@test.com",
        hashed_password="x",
        role=UserRole.STUDENT,
        is_archived=False,
    )
    db.add(u)
    db.flush()
    return u


def _seed_quiz(db, user_id: str, score: int) -> None:
    q = Question(
        question_id=f"q_exp_{user_id}",
        question_type=QuestionType.MCQ,
        question_text="Q",
        topic_id="periodontitis",
        max_score=10,
        bloom_level="comprehension",
        difficulty="easy",
        safety_category="low",
        correct_option="A",
        competency_areas=[],
    )
    db.add(q)
    db.flush()
    attempt = QuizAttempt(user_id=user_id, total_score=score, max_score=10)
    db.add(attempt)
    db.flush()
    db.add(QuizAnswer(
        attempt_id=attempt.id,
        question_id=q.id,
        student_response_text="A",
        auto_score=score,
        grading_status=GradingStatus.PUBLISHED,
    ))
    db.flush()


def _seed_case(db, user_id: str, score: int) -> None:
    db.add(ExamResult(user_id=user_id, case_id="case_001", score=score, max_score=10))
    db.flush()


def _seed_mastery(db, user_id: str, topic_id: str, prob: float) -> None:
    db.add(MasteryState(
        user_id=user_id,
        topic_id=topic_id,
        mastery_prob=prob,
        p_init=0.2, p_transit=0.1, p_slip=0.1, p_guess=0.2,
        n_observations=5,
    ))
    db.flush()


# ── Export ZIP tests ───────────────────────────────────────────────────────────

def test_zip_contains_all_tables(db):
    db.commit()
    zip_bytes, _, tables = build_export_zip(db)
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = {n.replace(".csv", "") for n in zf.namelist()}
    for table in TABLES:
        assert table in names, f"Missing table: {table}"


def test_zip_has_10_tables(db):
    db.commit()
    zip_bytes, _, tables = build_export_zip(db)
    assert len(tables) == 10


def test_trajectory_csv_populated(db):
    _add_student(db, "s1", "Ali")
    _seed_quiz(db, "s1", 9)
    db.commit()
    zip_bytes, _, _ = build_export_zip(db)
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    content = zf.read("mastery_trajectories.csv").decode("utf-8")
    assert "anon_user_id" in content
    assert "periodontitis" in content


def test_outcome_correlation_csv_populated(db):
    _add_student(db, "s1", "Ali")
    _seed_quiz(db, "s1", 8)
    _seed_case(db, "s1", 7)
    db.commit()
    zip_bytes, _, _ = build_export_zip(db)
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    content = zf.read("outcome_correlation.csv").decode("utf-8")
    assert "quiz_pct" in content
    assert "case_pct" in content


def test_zip_is_valid_on_empty_db(db):
    db.commit()
    zip_bytes, total, _ = build_export_zip(db)
    assert len(zip_bytes) > 0
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    assert len(zf.namelist()) == 10


def test_anon_user_id_not_original(db):
    _add_student(db, "real_user_123", "Ali")
    _seed_quiz(db, "real_user_123", 8)
    db.commit()
    zip_bytes, _, _ = build_export_zip(db)
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    content = zf.read("mastery_trajectories.csv").decode("utf-8")
    assert "real_user_123" not in content


# ── Analytics summary (snapshot) tests ────────────────────────────────────────

def test_analytics_summary_keys(db):
    db.commit()
    summary = _collect_analytics_summary(db)
    assert "bkt_priors" in summary
    assert "cohort_mastery_by_topic" in summary
    assert "outcome_correlation" in summary
    assert "schema_version" in summary
    assert summary["schema_version"] == "14b"


def test_analytics_summary_bkt_priors(db):
    db.commit()
    summary = _collect_analytics_summary(db)
    priors = summary["bkt_priors"]
    assert "p_init" in priors
    assert "p_transit" in priors
    assert "p_slip" in priors
    assert "p_guess" in priors
    assert 0 < priors["p_init"] < 1


def test_analytics_summary_cohort_mastery_with_data(db):
    _add_student(db, "s1", "Ali")
    _seed_mastery(db, "s1", "periodontitis", 0.75)
    db.commit()
    summary = _collect_analytics_summary(db)
    topics = summary["cohort_mastery_by_topic"]
    assert len(topics) >= 1
    perio = next((t for t in topics if t["topic_id"] == "periodontitis"), None)
    assert perio is not None
    assert abs(perio["cohort_avg"] - 0.75) < 0.01


def test_analytics_summary_correlation_empty(db):
    db.commit()
    summary = _collect_analytics_summary(db)
    assert summary["outcome_correlation"]["pearson_r"] is None
    assert summary["outcome_correlation"]["n_paired"] == 0
