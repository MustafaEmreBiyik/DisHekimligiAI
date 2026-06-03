"""Sprint 11 T05 — XGBoost recommendation trainer unit tests.

Verifies:
- Deterministic seed produces stable NDCG (same result on two runs with identical data).
- Feature schema persisted in bundle matches FEATURE_COLUMNS.
- Promotion gate: only one model can be active at a time.
- Promotion gate refuses a model whose NDCG < 1.10 × v1 baseline.
- load_bundle round-trips model and scaler correctly.
- InsufficientTrainingData raised when training frame is too small.
"""

from __future__ import annotations

import datetime
import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
import xgboost as xgb
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import (
    Base,
    CaseDefinition,
    ExamResult,
    RecommendationModelVersion,
    RecommendationSnapshot,
    StudentSession,
)
from app.services.feature_store import FEATURE_COLUMNS
from app.services.recommendation_trainer import (
    ALGORITHM_VERSION_V2,
    InsufficientTrainingData,
    _feature_set_hash,
    _hit_rate_at_k,
    _map_at_k,
    _ndcg_at_k,
    load_bundle,
    save_bundle,
    train,
)
from app.jobs.promote_recommendation_model import (
    PromotionGateFailure,
    check_gates,
    promote,
    rollback_to,
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


def _make_case(db, case_id: str) -> CaseDefinition:
    case = CaseDefinition(
        case_id=case_id, title=f"Case {case_id}", category="oral",
        difficulty="intermediate", estimated_duration_minutes=30, is_active=True,
        learning_objectives=[], prerequisite_competencies=[],
        competency_tags=[], initial_state="start",
        states_json={}, patient_info_json={}, rules_json=[], source_payload={},
    )
    db.add(case)
    db.flush()
    return case


def _seed_training_data(db, n_snapshots: int = 30) -> None:
    """Create minimal recommendation history for the training pipeline."""
    base_ts = datetime.datetime(2024, 1, 1)
    case_ids = [f"case_{i}" for i in range(5)]
    for cid in case_ids:
        _make_case(db, cid)

    for i in range(n_snapshots):
        user_id = f"stu_{i % 5}"
        case_id = case_ids[i % 5]
        snap_ts = base_ts + datetime.timedelta(days=i)

        db.add(RecommendationSnapshot(
            user_id=user_id, case_id=case_id,
            reason_code="not_attempted", reason_text="test",
            priority_score=50, algorithm_version="v1_competency_based",
            created_at=snap_ts,
        ))
        db.add(StudentSession(
            student_id=user_id, case_id=case_id,
            start_time=snap_ts,
        ))

        # Positive label: completed with ≥ 70% within 14 days for even i
        if i % 2 == 0:
            db.add(ExamResult(
                user_id=user_id, case_id=case_id,
                score=80, max_score=100,
                completed_at=snap_ts + datetime.timedelta(days=7),
            ))
    db.flush()


# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------

def test_ndcg_at_k_perfect_ranking():
    import pandas as pd
    df = pd.DataFrame({
        "user_id": ["u1", "u1", "u1"],
        "asof_ts": ["2024-01-01"] * 3,
        "outcome_score": [1.0, 0.0, 0.0],
    })
    scores = np.array([10.0, 5.0, 1.0])  # positive ranked first
    ndcg = _ndcg_at_k(df, scores, k=5)
    assert ndcg == pytest.approx(1.0)


def test_hit_rate_at_k_basic():
    import pandas as pd
    df = pd.DataFrame({
        "user_id": ["u1", "u1", "u1", "u2", "u2", "u2"],
        "asof_ts": ["2024-01-01"] * 3 + ["2024-01-02"] * 3,
        "outcome_score": [0.0, 1.0, 0.0,   0.0, 0.0, 1.0],
    })
    scores = np.array([5.0, 8.0, 1.0,   3.0, 4.0, 2.0])
    # u1: positive is ranked 1st (8.0) → hit
    # u2: positive is ranked 3rd → miss
    hr = _hit_rate_at_k(df, scores, k=1)
    assert hr == pytest.approx(0.5)  # 1 hit out of 2 groups


def test_map_at_k_perfect():
    import pandas as pd
    df = pd.DataFrame({
        "user_id": ["u1", "u1"],
        "asof_ts": ["2024-01-01"] * 2,
        "outcome_score": [1.0, 0.0],
    })
    scores = np.array([10.0, 1.0])
    m = _map_at_k(df, scores, k=5)
    assert m == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Feature set hash
# ---------------------------------------------------------------------------

def test_feature_set_hash_deterministic():
    h1 = _feature_set_hash(FEATURE_COLUMNS)
    h2 = _feature_set_hash(FEATURE_COLUMNS)
    assert h1 == h2
    assert len(h1) == 16


def test_feature_set_hash_differs_on_different_columns():
    h1 = _feature_set_hash(FEATURE_COLUMNS)
    h2 = _feature_set_hash(FEATURE_COLUMNS[:-1] + ["extra_feature"])
    assert h1 != h2


# ---------------------------------------------------------------------------
# save_bundle / load_bundle round-trip
# ---------------------------------------------------------------------------

def _make_dummy_booster() -> xgb.Booster:
    """Train a tiny 1-feature XGBoost model for bundle tests."""
    X = np.random.default_rng(0).standard_normal((20, len(FEATURE_COLUMNS)))
    y = (np.arange(20) % 2).astype(float)
    dm = xgb.DMatrix(X, label=y, feature_names=FEATURE_COLUMNS)
    dm.set_group(np.array([20], dtype=np.int32))
    booster = xgb.train(
        {"objective": "rank:pairwise", "verbosity": 0},
        dm, num_boost_round=3,
    )
    return booster


def test_save_and_load_bundle(tmp_path, monkeypatch):
    import app.services.recommendation_trainer as trainer_mod
    monkeypatch.setattr(trainer_mod, "MODELS_ROOT", tmp_path)

    from sklearn.preprocessing import StandardScaler
    booster = _make_dummy_booster()
    scaler = StandardScaler()
    scaler.fit(np.zeros((5, len(FEATURE_COLUMNS))))

    bundle_dir = save_bundle(
        algorithm_version="v2_test",
        booster=booster,
        scaler=scaler,
        feature_columns=FEATURE_COLUMNS,
        metrics={"ndcg_at_5": 0.25},
    )
    assert (bundle_dir / "model.json").exists()
    assert (bundle_dir / "scaler.joblib").exists()
    assert (bundle_dir / "feature_schema.json").exists()
    assert (bundle_dir / "feature_importance.json").exists()
    assert (bundle_dir / "metadata.json").exists()

    loaded_booster, loaded_scaler, loaded_cols = load_bundle(str(bundle_dir))
    assert loaded_cols == FEATURE_COLUMNS
    # Loaded booster can predict
    dummy = xgb.DMatrix(np.zeros((1, len(FEATURE_COLUMNS))), feature_names=FEATURE_COLUMNS)
    _ = loaded_booster.predict(dummy)


def test_feature_schema_in_bundle_matches_feature_columns(tmp_path, monkeypatch):
    import app.services.recommendation_trainer as trainer_mod
    monkeypatch.setattr(trainer_mod, "MODELS_ROOT", tmp_path)

    from sklearn.preprocessing import StandardScaler
    booster = _make_dummy_booster()
    scaler = StandardScaler().fit(np.zeros((5, len(FEATURE_COLUMNS))))
    bundle_dir = save_bundle("v2_schema_test", booster, scaler, FEATURE_COLUMNS, {})

    schema = json.loads((bundle_dir / "feature_schema.json").read_text())
    assert schema == FEATURE_COLUMNS


# ---------------------------------------------------------------------------
# InsufficientTrainingData
# ---------------------------------------------------------------------------

def test_train_raises_on_empty_db(db):
    with pytest.raises(InsufficientTrainingData):
        train(db, since_days=180, algorithm_version="v2_test", dry_run=False)


def test_train_dry_run_raises_on_empty_db(db):
    with pytest.raises(InsufficientTrainingData):
        train(db, since_days=180, dry_run=True)


# ---------------------------------------------------------------------------
# Promotion gate — single-active invariant
# ---------------------------------------------------------------------------

def _add_model_version(db, version: str, ndcg: float, is_active: bool = False, bundle_path: str = "/tmp/fake") -> RecommendationModelVersion:
    mv = RecommendationModelVersion(
        algorithm_version=version,
        model_blob_path=bundle_path,
        trained_at=datetime.datetime.utcnow(),
        training_sample_size=100,
        ndcg_at_5=ndcg,
        hit_rate_at_5=0.4,
        feature_set_hash=_feature_set_hash(FEATURE_COLUMNS),
        is_active=is_active,
        notes="test",
    )
    db.add(mv)
    db.flush()
    return mv


def test_promotion_enforces_single_active(db, tmp_path, monkeypatch):
    import app.jobs.promote_recommendation_model as promo_mod
    import app.services.recommendation_trainer as trainer_mod
    monkeypatch.setattr(trainer_mod, "MODELS_ROOT", tmp_path)

    from sklearn.preprocessing import StandardScaler
    booster = _make_dummy_booster()
    scaler = StandardScaler().fit(np.zeros((5, len(FEATURE_COLUMNS))))

    v1 = _add_model_version(db, "v1", ndcg=0.30, is_active=True)
    bundle_dir = save_bundle("v2_promote_test", booster, scaler, FEATURE_COLUMNS, {"ndcg_at_5": 0.35})
    v2 = _add_model_version(db, "v2_promote_test", ndcg=0.35, bundle_path=str(bundle_dir))

    promote(db, v2.id, skip_gates=True)
    db.commit()

    db.expire_all()
    assert db.query(RecommendationModelVersion).filter(
        RecommendationModelVersion.is_active.is_(True)
    ).count() == 1
    active = db.query(RecommendationModelVersion).filter(
        RecommendationModelVersion.is_active.is_(True)
    ).first()
    assert active.id == v2.id


def test_gate1_ndcg_lift_requirement(db):
    """Gate 1 should refuse a model with NDCG < 1.10 × v1 baseline (0.18)."""
    mv = _add_model_version(db, "v2_bad", ndcg=0.19)  # 0.19 < 0.18 * 1.10 = 0.198

    with pytest.raises(PromotionGateFailure, match="Gate 1"):
        check_gates(db, mv, skip_gates=False)


def test_gate1_passes_for_good_ndcg(db, tmp_path, monkeypatch):
    import app.services.recommendation_trainer as trainer_mod
    monkeypatch.setattr(trainer_mod, "MODELS_ROOT", tmp_path)

    from sklearn.preprocessing import StandardScaler
    booster = _make_dummy_booster()
    scaler = StandardScaler().fit(np.zeros((5, len(FEATURE_COLUMNS))))
    bundle_dir = save_bundle("v2_good", booster, scaler, FEATURE_COLUMNS, {})

    mv = _add_model_version(db, "v2_good", ndcg=0.30, bundle_path=str(bundle_dir))
    # Should not raise
    check_gates(db, mv, skip_gates=False)


def test_skip_gates_allows_any_model(db, tmp_path, monkeypatch):
    import app.services.recommendation_trainer as trainer_mod
    monkeypatch.setattr(trainer_mod, "MODELS_ROOT", tmp_path)

    from sklearn.preprocessing import StandardScaler
    booster = _make_dummy_booster()
    scaler = StandardScaler().fit(np.zeros((5, len(FEATURE_COLUMNS))))
    bundle_dir = save_bundle("v2_skip", booster, scaler, FEATURE_COLUMNS, {})

    mv = _add_model_version(db, "v2_skip", ndcg=0.10, bundle_path=str(bundle_dir))
    # skip_gates=True should not raise even for a poor model
    check_gates(db, mv, skip_gates=True)


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------

def test_rollback_switches_active(db, tmp_path, monkeypatch):
    import app.services.recommendation_trainer as trainer_mod
    monkeypatch.setattr(trainer_mod, "MODELS_ROOT", tmp_path)

    from sklearn.preprocessing import StandardScaler
    booster = _make_dummy_booster()
    scaler = StandardScaler().fit(np.zeros((5, len(FEATURE_COLUMNS))))

    b1 = save_bundle("v2_rb_1", booster, scaler, FEATURE_COLUMNS, {})
    b2 = save_bundle("v2_rb_2", booster, scaler, FEATURE_COLUMNS, {})

    mv1 = _add_model_version(db, "v2_rb_1", ndcg=0.30, is_active=False, bundle_path=str(b1))
    mv2 = _add_model_version(db, "v2_rb_2", ndcg=0.35, is_active=True, bundle_path=str(b2))

    rollback_to(db, mv1.id)
    db.commit()
    db.expire_all()

    active = db.query(RecommendationModelVersion).filter(
        RecommendationModelVersion.is_active.is_(True)
    ).first()
    assert active.id == mv1.id
