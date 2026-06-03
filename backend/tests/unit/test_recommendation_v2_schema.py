"""Sprint 11 T01 — schema tests for the recommendation v2 tables.

Covers table creation, defaults, unique constraints, FK relationships and
JSON round-trips for the four new models added to support IRT calibration,
BKT mastery tracking and the XGBoost ranker registry.
"""

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from db.database import (
    Base,
    IRTParameters,
    MasteryState,
    Question,
    QuestionType,
    RecommendationFeatureLog,
    RecommendationModelVersion,
    RecommendationSnapshot,
)


@pytest.fixture()
def schema_db():
    """Fresh in-memory SQLite per test to keep IntegrityError tests isolated."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def _make_question(session, question_id: str = "irt_q_001") -> Question:
    q = Question(
        question_id=question_id,
        question_type=QuestionType.MCQ,
        question_text="Sample item for IRT calibration",
        topic_id="oral_lichen_planus",
        bloom_level="apply",
        difficulty="medium",
        safety_category="none",
        options_json=["A", "B", "C", "D"],
        correct_option="B",
        max_score=1,
    )
    session.add(q)
    session.commit()
    return q


def test_irt_parameters_basic_persistence_and_relationship(schema_db):
    q = _make_question(schema_db)

    irt = IRTParameters(
        question_id=q.id,
        difficulty_b=0.42,
        discrimination_a=1.15,
        sample_size=250,
        fit_log_likelihood=-312.5,
        calibration_run_id="run_2026_06_02_abc",
        calibrated_at=datetime.datetime.utcnow(),
    )
    schema_db.add(irt)
    schema_db.commit()

    fetched = schema_db.query(IRTParameters).filter_by(question_id=q.id).one()
    assert fetched.model == "2PL", "default model should be 2PL"
    assert fetched.is_synthetic is False, "default is_synthetic should be False"
    assert fetched.guessing_c is None, "2PL row should not carry a guessing parameter"
    assert fetched.question.question_id == "irt_q_001"


def test_irt_parameters_unique_question_id(schema_db):
    q = _make_question(schema_db)
    schema_db.add(
        IRTParameters(
            question_id=q.id,
            difficulty_b=0.0,
            discrimination_a=1.0,
            sample_size=200,
            calibration_run_id="run_a",
            calibrated_at=datetime.datetime.utcnow(),
        )
    )
    schema_db.commit()

    schema_db.add(
        IRTParameters(
            question_id=q.id,
            difficulty_b=0.5,
            discrimination_a=1.2,
            sample_size=300,
            calibration_run_id="run_b",
            calibrated_at=datetime.datetime.utcnow(),
        )
    )
    with pytest.raises(IntegrityError):
        schema_db.commit()
    schema_db.rollback()


def test_mastery_state_defaults_and_unique_user_topic(schema_db):
    schema_db.add(
        MasteryState(
            user_id="student_001",
            topic_id="oral_lichen_planus",
            mastery_prob=0.42,
            updated_at=datetime.datetime.utcnow(),
        )
    )
    schema_db.commit()

    fetched = schema_db.query(MasteryState).one()
    assert fetched.p_init == pytest.approx(0.20)
    assert fetched.p_transit == pytest.approx(0.10)
    assert fetched.p_slip == pytest.approx(0.10)
    assert fetched.p_guess == pytest.approx(0.20)
    assert fetched.n_observations == 0
    assert fetched.last_observation_at is None

    # Same (user, topic) duplicate is rejected
    schema_db.add(
        MasteryState(
            user_id="student_001",
            topic_id="oral_lichen_planus",
            mastery_prob=0.55,
            updated_at=datetime.datetime.utcnow(),
        )
    )
    with pytest.raises(IntegrityError):
        schema_db.commit()
    schema_db.rollback()

    # Different topic, same user is fine
    schema_db.add(
        MasteryState(
            user_id="student_001",
            topic_id="herpes_simplex",
            mastery_prob=0.30,
            updated_at=datetime.datetime.utcnow(),
        )
    )
    schema_db.commit()
    assert schema_db.query(MasteryState).count() == 2


def test_recommendation_model_version_defaults_and_unique_algorithm(schema_db):
    schema_db.add(
        RecommendationModelVersion(
            algorithm_version="v2_hybrid_xgb_irt_bkt",
            model_blob_path="models/recommendation/v2_hybrid_xgb_irt_bkt/xgb.json",
            training_sample_size=4280,
            feature_set_hash="sha256:abc123",
            trained_at=datetime.datetime.utcnow(),
        )
    )
    schema_db.commit()

    fetched = schema_db.query(RecommendationModelVersion).one()
    assert fetched.is_active is False, "new model versions must default to inactive"
    assert fetched.ndcg_at_5 is None
    assert fetched.hit_rate_at_5 is None
    assert fetched.map_at_10 is None

    schema_db.add(
        RecommendationModelVersion(
            algorithm_version="v2_hybrid_xgb_irt_bkt",
            model_blob_path="models/recommendation/v2_hybrid_xgb_irt_bkt/xgb_v2.json",
            training_sample_size=5100,
            feature_set_hash="sha256:def456",
            trained_at=datetime.datetime.utcnow(),
        )
    )
    with pytest.raises(IntegrityError):
        schema_db.commit()
    schema_db.rollback()


def test_recommendation_feature_log_fk_and_json_roundtrip(schema_db):
    snapshot = RecommendationSnapshot(
        user_id="student_001",
        case_id="olp_001",
        reason_code="weak_competency",
        reason_text="oral_pathology alaninda eksiklik tespit edildi.",
        priority_score=85,
        algorithm_version="v2_hybrid_xgb_irt_bkt",
    )
    schema_db.add(snapshot)

    model_version = RecommendationModelVersion(
        algorithm_version="v2_hybrid_xgb_irt_bkt",
        model_blob_path="models/recommendation/v2_hybrid_xgb_irt_bkt/xgb.json",
        training_sample_size=4280,
        feature_set_hash="sha256:abc123",
        trained_at=datetime.datetime.utcnow(),
    )
    schema_db.add(model_version)
    schema_db.commit()

    feature_vector = {
        "cold_start_flag": 0.0,
        "mastery_gap_on_case_topics": 1.42,
        "case_difficulty_ordinal": 1.0,
        "irt_mean_b_mapped_questions": 0.31,
    }
    shap_values = [
        {"name": "mastery_gap_on_case_topics", "contribution": 0.41, "direction": "up"},
        {"name": "case_difficulty_ordinal", "contribution": -0.12, "direction": "down"},
        {"name": "cold_start_flag", "contribution": 0.05, "direction": "up"},
    ]

    log = RecommendationFeatureLog(
        snapshot_id=snapshot.id,
        model_version_id=model_version.id,
        feature_vector_json=feature_vector,
        shap_values_json=shap_values,
    )
    schema_db.add(log)
    schema_db.commit()

    fetched = schema_db.query(RecommendationFeatureLog).one()
    assert fetched.snapshot.case_id == "olp_001"
    assert fetched.model_version.algorithm_version == "v2_hybrid_xgb_irt_bkt"
    assert fetched.feature_vector_json["mastery_gap_on_case_topics"] == pytest.approx(1.42)
    assert len(fetched.shap_values_json) == 3
    assert fetched.shap_values_json[0]["direction"] == "up"
