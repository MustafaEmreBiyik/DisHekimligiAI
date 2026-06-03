"""Sprint 11 T02 — Feature store unit tests.

Verifies:
- FEATURE_COLUMNS has exactly 37 entries.
- Cold-start user: cold_start_flag=1, all features at documented defaults.
- User with sessions: n_sessions_total, n_sessions_last_7d populated correctly.
- Case features: difficulty ordinal mapping, n_competency_tags, n_mapped_questions.
- build_candidate_row: shape-consistent 37-column vector, no unexpected NaNs.
- materialise_training_frame: columns = label + feature columns.
"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import (
    Base,
    CaseDefinition,
    ExamResult,
    MasteryState,
    QuizAttempt,
    QuizAnswer,
    Question,
    QuestionCaseMapping,
    QuestionType,
    GradingStatus,
    MappingType,
    ReviewStatus,
    StudentSession,
    IRTParameters,
)
from app.services.feature_store import (
    FEATURE_COLUMNS,
    build_candidate_row,
    build_case_features,
    build_user_features,
    materialise_training_frame,
    _LABEL_COLUMNS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_case(db, case_id: str, difficulty: str = "beginner", tags: list[str] | None = None) -> CaseDefinition:
    case = CaseDefinition(
        case_id=case_id,
        title=f"Case {case_id}",
        category="oral_pathology",
        difficulty=difficulty,
        estimated_duration_minutes=30,
        is_active=True,
        learning_objectives=["obj1", "obj2"],
        prerequisite_competencies=["comp1"],
        competency_tags=tags or ["tag_a", "tag_b"],
        initial_state="anamnez",
        states_json={},
        patient_info_json={},
        rules_json=[],
        source_payload={},
    )
    db.add(case)
    db.flush()
    return case


def _make_session(db, user_id: str, case_id: str, start_time: datetime.datetime | None = None) -> StudentSession:
    s = StudentSession(
        student_id=user_id,
        case_id=case_id,
        start_time=start_time or datetime.datetime.utcnow(),
    )
    db.add(s)
    db.flush()
    return s


# ---------------------------------------------------------------------------
# Feature column count
# ---------------------------------------------------------------------------

def test_feature_columns_count():
    assert len(FEATURE_COLUMNS) == 37, f"Expected 37 features, got {len(FEATURE_COLUMNS)}"


def test_feature_columns_no_duplicates():
    assert len(FEATURE_COLUMNS) == len(set(FEATURE_COLUMNS))


# ---------------------------------------------------------------------------
# Cold-start user
# ---------------------------------------------------------------------------

def test_cold_start_user_flag(db):
    feat = build_user_features(db, user_id="cold_user")
    assert feat["cold_start_flag"] == 1.0
    assert feat["n_sessions_total"] == 0.0
    assert feat["n_sessions_last_7d"] == 0.0
    assert feat["days_since_last_session"] == 999.0
    # Mastery defaults
    assert feat["mean_mastery_prob_all_topics"] == pytest.approx(0.20)
    assert feat["min_mastery_prob"] == pytest.approx(0.20)
    assert feat["n_topics_below_60pct"] == 0.0
    assert feat["n_topics_above_80pct"] == 0.0


def test_cold_start_candidate_row_shape(db):
    _make_case(db, "case_cold")
    row = build_candidate_row(db, user_id="cold_user2", case_id="case_cold")
    assert set(row.keys()) == set(FEATURE_COLUMNS)
    # No NaN values
    for k, v in row.items():
        assert v == v, f"Feature '{k}' is NaN"  # NaN != NaN


# ---------------------------------------------------------------------------
# User with sessions
# ---------------------------------------------------------------------------

def test_user_with_sessions(db):
    now = datetime.datetime.utcnow()
    _make_session(db, "stu_001", "case_A", start_time=now - datetime.timedelta(days=2))
    _make_session(db, "stu_001", "case_B", start_time=now - datetime.timedelta(days=10))
    _make_session(db, "stu_001", "case_C", start_time=now - datetime.timedelta(days=40))

    feat = build_user_features(db, "stu_001")

    assert feat["n_sessions_total"] == 3.0
    assert feat["n_sessions_last_7d"] == 1.0  # only the 2-day-old one
    assert feat["cold_start_flag"] == 0.0  # 3 sessions ≥ threshold


def test_days_since_last_session(db):
    ref = datetime.datetime.utcnow() - datetime.timedelta(days=5)
    _make_session(db, "stu_002", "case_A", start_time=ref)
    feat = build_user_features(db, "stu_002")
    assert 4.5 < feat["days_since_last_session"] < 5.5


# ---------------------------------------------------------------------------
# Mastery features
# ---------------------------------------------------------------------------

def test_mastery_features(db):
    states = [
        MasteryState(user_id="stu_m", topic_id="topic_1", mastery_prob=0.85, p_init=0.2, p_transit=0.1, p_slip=0.1, p_guess=0.2, n_observations=10),
        MasteryState(user_id="stu_m", topic_id="topic_2", mastery_prob=0.45, p_init=0.2, p_transit=0.1, p_slip=0.1, p_guess=0.2, n_observations=5),
        MasteryState(user_id="stu_m", topic_id="topic_3", mastery_prob=0.70, p_init=0.2, p_transit=0.1, p_slip=0.1, p_guess=0.2, n_observations=8),
    ]
    for s in states:
        db.add(s)
    db.flush()

    feat = build_user_features(db, "stu_m")
    expected_mean = (0.85 + 0.45 + 0.70) / 3
    assert feat["mean_mastery_prob_all_topics"] == pytest.approx(expected_mean, abs=1e-6)
    assert feat["min_mastery_prob"] == pytest.approx(0.45, abs=1e-6)
    assert feat["n_topics_below_60pct"] == 1.0   # 0.45 < 0.60
    assert feat["n_topics_above_80pct"] == 1.0   # 0.85 ≥ 0.80


# ---------------------------------------------------------------------------
# Case features
# ---------------------------------------------------------------------------

def test_case_difficulty_ordinal(db):
    _make_case(db, "case_easy", difficulty="beginner")
    _make_case(db, "case_mid", difficulty="intermediate")
    _make_case(db, "case_hard", difficulty="advanced")

    assert build_case_features(db, "case_easy")["case_difficulty_ordinal"] == 0.0
    assert build_case_features(db, "case_mid")["case_difficulty_ordinal"] == 1.0
    assert build_case_features(db, "case_hard")["case_difficulty_ordinal"] == 2.0


def test_case_n_competency_tags(db):
    _make_case(db, "case_tags", tags=["infection", "safety", "diagnosis"])
    feat = build_case_features(db, "case_tags")
    assert feat["n_competency_tags"] == 3.0
    assert feat["n_learning_objectives"] == 2.0   # from _make_case default
    assert feat["n_prerequisite_competencies"] == 1.0


def test_case_irt_features(db):
    case = _make_case(db, "case_irt")
    q = Question(
        question_id="q_irt_1",
        question_type=QuestionType.MCQ,
        question_text="Test?",
        topic_id="topic_irt",
        competency_areas=[],
        bloom_level="remember",
        difficulty="medium",
        safety_category="none",
        max_score=1,
    )
    db.add(q)
    db.flush()
    mapping = QuestionCaseMapping(
        question_id=q.id,
        case_id="case_irt",
        mapping_type=MappingType.ASSESSMENT_LINK,
        review_status=ReviewStatus.APPROVED,
    )
    db.add(mapping)
    irt = IRTParameters(
        question_id=q.id,
        model="2PL",
        difficulty_b=0.5,
        discrimination_a=1.2,
        sample_size=250,
        is_synthetic=False,
        calibration_run_id="run_001",
    )
    db.add(irt)
    db.flush()

    feat = build_case_features(db, "case_irt")
    assert feat["n_mapped_questions"] == 1.0
    assert feat["irt_mean_b_mapped_questions"] == pytest.approx(0.5)
    assert feat["irt_mean_a_mapped_questions"] == pytest.approx(1.2)


# ---------------------------------------------------------------------------
# Cross features
# ---------------------------------------------------------------------------

def test_cross_is_completed(db):
    _make_case(db, "case_done")
    _make_session(db, "stu_done", "case_done")
    db.add(ExamResult(user_id="stu_done", case_id="case_done", score=80, max_score=100))
    db.flush()

    row = build_candidate_row(db, "stu_done", "case_done")
    assert row["is_completed"] == 1.0
    assert row["is_in_progress"] == 0.0
    assert row["n_prior_attempts_on_case"] == 1.0


def test_cross_is_in_progress(db):
    _make_case(db, "case_prog")
    _make_session(db, "stu_prog", "case_prog")

    row = build_candidate_row(db, "stu_prog", "case_prog")
    assert row["is_completed"] == 0.0
    assert row["is_in_progress"] == 1.0


def test_cross_mastery_gap(db):
    _make_case(db, "case_gap", tags=["topic_x"])
    q = Question(
        question_id="q_gap_1",
        question_type=QuestionType.MCQ,
        question_text="Gap?",
        topic_id="topic_x",
        competency_areas=[],
        bloom_level="apply",
        difficulty="medium",
        safety_category="none",
        max_score=1,
    )
    db.add(q)
    db.flush()
    db.add(QuestionCaseMapping(
        question_id=q.id,
        case_id="case_gap",
        mapping_type=MappingType.ASSESSMENT_LINK,
        review_status=ReviewStatus.APPROVED,
    ))
    # Low mastery on topic_x
    db.add(MasteryState(
        user_id="stu_gap", topic_id="topic_x", mastery_prob=0.30,
        p_init=0.2, p_transit=0.1, p_slip=0.1, p_guess=0.2, n_observations=3,
    ))
    db.flush()

    row = build_candidate_row(db, "stu_gap", "case_gap")
    # gap = 1 - 0.30 = 0.70
    assert row["mastery_gap_on_case_topics"] == pytest.approx(0.70, abs=1e-6)


# ---------------------------------------------------------------------------
# materialise_training_frame
# ---------------------------------------------------------------------------

def test_materialise_training_frame_empty(db):
    import pandas as pd
    since = datetime.datetime(2020, 1, 1)
    until = datetime.datetime(2020, 6, 1)
    df = materialise_training_frame(db, since, until)
    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == _LABEL_COLUMNS + FEATURE_COLUMNS


def test_materialise_training_frame_columns(db):
    from db.database import RecommendationSnapshot
    import pandas as pd

    _make_case(db, "case_train")
    snap = RecommendationSnapshot(
        user_id="stu_train",
        case_id="case_train",
        reason_code="not_attempted",
        reason_text="test",
        priority_score=50,
        algorithm_version="v1_competency_based",
        created_at=datetime.datetime(2024, 1, 15),
    )
    db.add(snap)
    db.flush()

    since = datetime.datetime(2024, 1, 1)
    until = datetime.datetime(2024, 6, 1)
    df = materialise_training_frame(db, since, until)

    assert list(df.columns) == _LABEL_COLUMNS + FEATURE_COLUMNS
    assert len(df) == 1
    assert df.iloc[0]["user_id"] == "stu_train"
    assert df.iloc[0]["case_id"] == "case_train"
    assert df.iloc[0]["outcome_score"] == 0.0  # no completion in window
