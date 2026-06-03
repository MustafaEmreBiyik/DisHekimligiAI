"""
XGBoost Learning-to-Rank Trainer — Sprint 11 T05
=================================================
Trains, evaluates and persists an XGBoost ranker that scores (user, case)
candidates. The model is the heart of v2 ranking.

Training approach: XGBRanker with `objective="rank:pairwise"`, grouped by
(user_id, asof_ts) — one recommendation context per group.

Label: binary `outcome_score = 1` when the student completed the recommended
case within 14 days with score ≥ 70% of max_score. See
docs/architecture/RECOMMENDATION_LABELS.md for the full definition.

Evaluation: NDCG@5, hit-rate@5, MAP@10 on the chronological validation set.

Model bundle layout (persisted under models/recommendation/<algorithm_version>/):
  model.json            — XGBoost booster (portable format)
  scaler.joblib         — sklearn StandardScaler fitted on train split only
  feature_schema.json   — list of 37 feature column names
  feature_importance.json — top-10 features by total gain (for monitoring)
  metadata.json         — training metadata (date, sample_size, metrics)

Promotion: see promote_recommendation_model.py.

CLI:
    python -m app.jobs.retrain_ranker
    python -m app.jobs.retrain_ranker --since 180d --algorithm-version v2_hybrid_xgb_irt_bkt
    python -m app.jobs.retrain_ranker --dry-run
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import ndcg_score
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.services.feature_store import (
    FEATURE_COLUMNS,
    materialise_training_frame,
)
from db.database import RecommendationModelVersion

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALGORITHM_VERSION_V2 = "v2_hybrid_xgb_irt_bkt"
MODELS_ROOT = Path(__file__).resolve().parents[3] / "models" / "recommendation"

_DEFAULT_XGB_PARAMS: dict = {
    "objective": "rank:pairwise",
    "n_estimators": 500,
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "early_stopping_rounds": 30,
    "random_state": 42,
    "verbosity": 0,
    "tree_method": "hist",
    "device": "cpu",
}

_VAL_DAYS = 21       # last N days of data → validation set
_LABEL_COL = "outcome_score"
_META_COLS = ["user_id", "case_id", "asof_ts", _LABEL_COL]


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def _make_groups(df: pd.DataFrame) -> np.ndarray:
    """Return XGBoost group array: count of rows per (user_id, asof_ts) group."""
    return (
        df.groupby(["user_id", "asof_ts"], sort=False)
        .size()
        .values.astype(np.int32)
    )


def _ndcg_at_k(df: pd.DataFrame, scores: np.ndarray, k: int = 5) -> float:
    """Compute NDCG@k averaged over all (user_id, asof_ts) query groups."""
    df = df.copy()
    df["_score"] = scores
    groups = df.groupby(["user_id", "asof_ts"], sort=False)

    ndcg_vals: list[float] = []
    for _, grp in groups:
        true_rel = grp[_LABEL_COL].values.reshape(1, -1)
        pred_scores = grp["_score"].values.reshape(1, -1)
        if true_rel.max() == 0:
            continue  # no positive in this group — skip (undefined NDCG)
        ndcg_vals.append(float(ndcg_score(true_rel, pred_scores, k=k)))

    return float(np.mean(ndcg_vals)) if ndcg_vals else 0.0


def _hit_rate_at_k(df: pd.DataFrame, scores: np.ndarray, k: int = 5) -> float:
    """Fraction of query groups where the positive item is in the top-k predictions."""
    df = df.copy()
    df["_score"] = scores
    groups = df.groupby(["user_id", "asof_ts"], sort=False)

    hits = 0
    total = 0
    for _, grp in groups:
        if grp[_LABEL_COL].max() == 0:
            continue
        total += 1
        top_k_idx = grp["_score"].nlargest(k).index
        if grp.loc[top_k_idx, _LABEL_COL].max() > 0:
            hits += 1

    return float(hits / total) if total > 0 else 0.0


def _map_at_k(df: pd.DataFrame, scores: np.ndarray, k: int = 10) -> float:
    """Mean Average Precision @ k across query groups."""
    df = df.copy()
    df["_score"] = scores
    groups = df.groupby(["user_id", "asof_ts"], sort=False)

    aps: list[float] = []
    for _, grp in groups:
        if grp[_LABEL_COL].max() == 0:
            continue
        ranked = grp.sort_values("_score", ascending=False).head(k)
        labels = ranked[_LABEL_COL].values
        n_relevant = labels.sum()
        if n_relevant == 0:
            continue
        precisions = [
            labels[: i + 1].sum() / (i + 1)
            for i in range(len(labels))
            if labels[i] == 1
        ]
        aps.append(float(np.mean(precisions)))

    return float(np.mean(aps)) if aps else 0.0


# ---------------------------------------------------------------------------
# Model bundle I/O
# ---------------------------------------------------------------------------

def _bundle_path(algorithm_version: str) -> Path:
    return MODELS_ROOT / algorithm_version


def save_bundle(
    algorithm_version: str,
    booster: xgb.Booster,
    scaler: StandardScaler,
    feature_columns: list[str],
    metrics: dict,
) -> Path:
    """Persist model artefacts and return the bundle directory path."""
    bundle_dir = _bundle_path(algorithm_version)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    booster.save_model(str(bundle_dir / "model.json"))
    joblib.dump(scaler, bundle_dir / "scaler.joblib")

    (bundle_dir / "feature_schema.json").write_text(
        json.dumps(feature_columns, indent=2), encoding="utf-8"
    )

    # Feature importance (top-10 by total gain)
    importance = booster.get_score(importance_type="total_gain")
    top10 = sorted(importance.items(), key=lambda kv: kv[1], reverse=True)[:10]
    (bundle_dir / "feature_importance.json").write_text(
        json.dumps(dict(top10), indent=2), encoding="utf-8"
    )

    metadata = {
        "algorithm_version": algorithm_version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        **metrics,
        "feature_columns": feature_columns,
    }
    (bundle_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    logger.info("Model bundle saved to %s", bundle_dir)
    return bundle_dir


def load_bundle(bundle_path: str) -> tuple[xgb.Booster, StandardScaler, list[str]]:
    """Load model, scaler and feature schema from a bundle directory."""
    p = Path(bundle_path)
    booster = xgb.Booster()
    booster.load_model(str(p / "model.json"))
    scaler: StandardScaler = joblib.load(p / "scaler.joblib")
    feature_columns: list[str] = json.loads((p / "feature_schema.json").read_text())
    return booster, scaler, feature_columns


def _feature_set_hash(feature_columns: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(feature_columns)).encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Training pipeline
# ---------------------------------------------------------------------------

class InsufficientTrainingData(Exception):
    """Raised when the training frame is too small to fit a meaningful model."""


def train(
    db: Session,
    since_days: int = 180,
    algorithm_version: str = ALGORITHM_VERSION_V2,
    xgb_params: Optional[dict] = None,
    dry_run: bool = False,
    seed: int = 42,
) -> dict:
    """
    Full training pipeline: materialise features → split → scale → fit →
    evaluate → persist model bundle → insert RecommendationModelVersion row.

    Parameters
    ----------
    db                 : SQLAlchemy session
    since_days         : How far back to pull recommendation snapshots
    algorithm_version  : Version string; also the bundle directory name
    xgb_params         : Override default XGB hyperparameters
    dry_run            : Skip saving to disk and DB; still compute metrics
    seed               : Random seed (passed to XGB for reproducibility)

    Returns
    -------
    dict with run metadata and evaluation metrics
    """
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    since = now - timedelta(days=since_days)
    until = now - timedelta(days=14)   # 14-day label observation lag

    if since >= until:
        raise InsufficientTrainingData(
            f"since={since.date()} must be before until={until.date()} (14-day lag)"
        )

    logger.info(
        '{"job":"retrain_ranker","run_id":"%s","since":"%s","until":"%s"}',
        run_id, since.date(), until.date(),
    )

    # 1. Materialise training frame
    df = materialise_training_frame(db, since=since, until=until)

    if len(df) < 10:
        raise InsufficientTrainingData(
            f"Only {len(df)} training rows found. Need at least 10 to train a ranker. "
            "Run more recommendation cycles first, or use --dry-run to inspect features."
        )

    # 2. Chronological train/val split (no shuffle — temporal leakage protection)
    df = df.sort_values("asof_ts").reset_index(drop=True)
    val_cutoff = df["asof_ts"].max() - timedelta(days=_VAL_DAYS)
    train_df = df[df["asof_ts"] < val_cutoff].copy()
    val_df   = df[df["asof_ts"] >= val_cutoff].copy()

    if len(train_df) < 5 or len(val_df) < 5:
        raise InsufficientTrainingData(
            f"Not enough data after train/val split: train={len(train_df)}, val={len(val_df)}. "
            f"Need at least 5 rows each. Try --since with a larger window."
        )

    X_train = train_df[FEATURE_COLUMNS].values.astype(float)
    y_train = train_df[_LABEL_COL].values.astype(float)
    X_val   = val_df[FEATURE_COLUMNS].values.astype(float)
    y_val   = val_df[_LABEL_COL].values.astype(float)

    # 3. Standardise features (fit on train only)
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled   = scaler.transform(X_val)

    # 4. Build XGBoost DMatrix with group info
    train_groups = _make_groups(train_df)
    val_groups   = _make_groups(val_df)

    dtrain = xgb.DMatrix(X_train_scaled, label=y_train, feature_names=FEATURE_COLUMNS)
    dtrain.set_group(train_groups)

    dval = xgb.DMatrix(X_val_scaled, label=y_val, feature_names=FEATURE_COLUMNS)
    dval.set_group(val_groups)

    # 5. Fit XGBRanker
    params = dict(_DEFAULT_XGB_PARAMS)
    if xgb_params:
        params.update(xgb_params)
    params["seed"] = seed

    n_estimators = params.pop("n_estimators", 500)
    early_stopping = params.pop("early_stopping_rounds", 30)

    booster = xgb.train(
        params=params,
        dtrain=dtrain,
        num_boost_round=n_estimators,
        evals=[(dval, "val")],
        early_stopping_rounds=early_stopping,
        verbose_eval=False,
    )

    # 6. Evaluate
    val_scores  = booster.predict(dval)
    ndcg_at_5   = _ndcg_at_k(val_df, val_scores, k=5)
    hit_rate_at_5 = _hit_rate_at_k(val_df, val_scores, k=5)
    map_at_10   = _map_at_k(val_df, val_scores, k=10)

    metrics = {
        "ndcg_at_5": round(ndcg_at_5, 4),
        "hit_rate_at_5": round(hit_rate_at_5, 4),
        "map_at_10": round(map_at_10, 4),
        "training_sample_size": len(train_df),
        "validation_sample_size": len(val_df),
        "best_iteration": int(getattr(booster, "best_iteration", n_estimators)),
    }

    logger.info(
        '{"run_id":"%s","ndcg_at_5":%.4f,"hit_rate_at_5":%.4f,"map_at_10":%.4f,"train_n":%d,"val_n":%d}',
        run_id, ndcg_at_5, hit_rate_at_5, map_at_10, len(train_df), len(val_df),
    )

    if dry_run:
        return {"run_id": run_id, "dry_run": True, **metrics}

    # 7. Save model bundle
    bundle_dir = save_bundle(
        algorithm_version=algorithm_version,
        booster=booster,
        scaler=scaler,
        feature_columns=FEATURE_COLUMNS,
        metrics=metrics,
    )

    # 8. Insert RecommendationModelVersion row (is_active=False by default)
    importance = booster.get_score(importance_type="total_gain")
    top10 = sorted(importance.items(), key=lambda kv: kv[1], reverse=True)[:10]
    notes = f"Top features by gain: {json.dumps(dict(top10))}"

    model_version = RecommendationModelVersion(
        algorithm_version=algorithm_version,
        model_blob_path=str(bundle_dir),
        trained_at=now,
        training_sample_size=len(train_df),
        ndcg_at_5=ndcg_at_5,
        hit_rate_at_5=hit_rate_at_5,
        feature_set_hash=_feature_set_hash(FEATURE_COLUMNS),
        is_active=False,
        notes=notes,
    )
    db.add(model_version)
    db.flush()

    return {
        "run_id": run_id,
        "algorithm_version": algorithm_version,
        "model_version_id": model_version.id,
        "bundle_path": str(bundle_dir),
        "dry_run": False,
        **metrics,
    }
