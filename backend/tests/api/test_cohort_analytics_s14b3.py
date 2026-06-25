"""Sprint 14-B S14B-3: cohort mastery heatmap service tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from db.database import Base, MasteryState, User, UserRole
from app.services.cohort_analytics_service import build_cohort_heatmap, MASTERY_THRESHOLD


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


def _add_mastery(db, user_id: str, topic_id: str, prob: float) -> None:
    db.add(MasteryState(
        user_id=user_id,
        topic_id=topic_id,
        mastery_prob=prob,
        p_init=0.2,
        p_transit=0.1,
        p_slip=0.1,
        p_guess=0.2,
        n_observations=5,
    ))
    db.flush()


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_returns_all_students(db):
    _add_student(db, "s1", "Ali")
    _add_student(db, "s2", "Zeynep")
    db.commit()
    result = build_cohort_heatmap(db=db)
    assert result["n_students"] == 2
    assert len(result["students"]) == 2


def test_topics_collected(db):
    _add_student(db, "s1", "Ali")
    _add_mastery(db, "s1", "periodontitis", 0.8)
    _add_mastery(db, "s1", "oscc", 0.4)
    db.commit()
    result = build_cohort_heatmap(db=db)
    topic_ids = {t["topic_id"] for t in result["topics"]}
    assert "periodontitis" in topic_ids
    assert "oscc" in topic_ids
    assert result["n_topics"] == 2


def test_missing_topic_is_none(db):
    _add_student(db, "s1", "Ali")
    _add_student(db, "s2", "Zeynep")
    _add_mastery(db, "s1", "periodontitis", 0.8)
    # s2 has no mastery rows
    db.commit()
    result = build_cohort_heatmap(db=db)
    s2_row = next(s for s in result["students"] if s["user_id"] == "s2")
    assert s2_row["mastery"]["periodontitis"] is None
    assert s2_row["avg_mastery"] is None


def test_cohort_avg_computed(db):
    _add_student(db, "s1", "Ali")
    _add_student(db, "s2", "Zeynep")
    _add_mastery(db, "s1", "periodontitis", 0.6)
    _add_mastery(db, "s2", "periodontitis", 0.4)
    db.commit()
    result = build_cohort_heatmap(db=db)
    perio = next(t for t in result["topics"] if t["topic_id"] == "periodontitis")
    assert abs(perio["cohort_avg"] - 0.5) < 0.01


def test_mastered_count(db):
    _add_student(db, "s1", "Ali")
    _add_mastery(db, "s1", "periodontitis", 0.85)
    _add_mastery(db, "s1", "oscc", 0.3)
    db.commit()
    result = build_cohort_heatmap(db=db)
    s1 = result["students"][0]
    # periodontitis >= 0.7 threshold → mastered_count = 1
    assert s1["mastered_count"] == 1


def test_empty_cohort(db):
    result = build_cohort_heatmap(db=db)
    assert result["n_students"] == 0
    assert result["n_topics"] == 0
    assert result["students"] == []


def test_archived_students_excluded(db):
    _add_student(db, "s1", "Ali")
    archived = User(
        user_id="s_archived",
        display_name="Silinmiş",
        email="arch@test.com",
        hashed_password="x",
        role=UserRole.STUDENT,
        is_archived=True,
    )
    db.add(archived)
    db.commit()
    result = build_cohort_heatmap(db=db)
    assert result["n_students"] == 1
    assert all(s["user_id"] != "s_archived" for s in result["students"])


def test_mastery_threshold_in_response(db):
    result = build_cohort_heatmap(db=db)
    assert result["mastery_threshold"] == MASTERY_THRESHOLD
