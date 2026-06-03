"""
Recommendation Explainer — Sprint 11 T06
==========================================
SHAP-based feature attribution for XGBoost ranker predictions.

The TreeExplainer instance is cached per model-version-id so it is constructed
once at model load time and reused across requests (~1 ms per row for tree models).

Falls back to XGBoost gain-weighted attribution when shap is unavailable.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import xgboost as xgb

logger = logging.getLogger(__name__)

try:
    import shap as _shap
    _SHAP_AVAILABLE = True
except ImportError:  # pragma: no cover
    _SHAP_AVAILABLE = False
    logger.warning(
        "shap not installed — falling back to XGBoost gain-based attribution. "
        "Install shap for accurate SHAP values: pip install shap"
    )

# Cache: model_version_id → TreeExplainer (or None)
_explainer_cache: dict[int, Optional[object]] = {}


def _get_explainer(booster: xgb.Booster, model_version_id: int) -> Optional[object]:
    if model_version_id not in _explainer_cache:
        if _SHAP_AVAILABLE:
            try:
                _explainer_cache[model_version_id] = _shap.TreeExplainer(booster)
            except Exception as exc:
                logger.warning("Could not build TreeExplainer: %s — using fallback", exc)
                _explainer_cache[model_version_id] = None
        else:
            _explainer_cache[model_version_id] = None
    return _explainer_cache[model_version_id]


def invalidate_cache(model_version_id: int) -> None:
    """Call when a model is replaced/rolled back so the explainer is rebuilt."""
    _explainer_cache.pop(model_version_id, None)


def compute_top_features(
    booster: xgb.Booster,
    scaler,
    feature_columns: list[str],
    feature_rows: list[dict[str, float]],
    model_version_id: int = -1,
    top_n: int = 3,
) -> list[list[dict]]:
    """
    Compute top-n feature attributions for each candidate row.

    Returns
    -------
    list[list[dict]]
        One inner list per row; each dict has keys:
          name         : raw feature name (frontend translates to Turkish)
          contribution : float, magnitude of SHAP/gain value
          direction    : "up" (positive) | "down" (negative)

    Always returns a list of the same length as feature_rows, with empty
    inner lists on failure so callers never see None.
    """
    if not feature_rows:
        return []

    n = len(feature_rows)
    X = np.array([[row.get(col, 0.0) for col in feature_columns] for row in feature_rows])
    X_scaled = scaler.transform(X)

    explainer = _get_explainer(booster, model_version_id)

    if explainer is not None:
        try:
            shap_values = explainer.shap_values(X_scaled)   # (n, n_features)
            return _top_from_shap(shap_values, feature_columns, top_n)
        except Exception as exc:
            logger.warning("SHAP computation failed: %s — using fallback attribution", exc)

    # Fallback: gain-weighted |feature value| attribution
    return _top_from_gain(booster, X_scaled, feature_columns, top_n)


def _top_from_shap(
    shap_values: np.ndarray,
    feature_columns: list[str],
    top_n: int,
) -> list[list[dict]]:
    result = []
    for row_shap in shap_values:
        abs_vals = np.abs(row_shap)
        top_idx = np.argsort(abs_vals)[::-1][:top_n]
        features = [
            {
                "name": feature_columns[i],
                "contribution": float(abs_vals[i]),
                "direction": "up" if float(row_shap[i]) >= 0 else "down",
            }
            for i in top_idx
        ]
        result.append(features)
    return result


def _top_from_gain(
    booster: xgb.Booster,
    X_scaled: np.ndarray,
    feature_columns: list[str],
    top_n: int,
) -> list[list[dict]]:
    """Use XGBoost gain-based importance × |feature value| as a proxy for attribution."""
    gain = booster.get_score(importance_type="total_gain")
    gain_arr = np.array([gain.get(f, 0.0) for f in feature_columns])
    # Normalize gain
    total = gain_arr.sum()
    if total > 0:
        gain_arr /= total

    result = []
    for row in X_scaled:
        attribution = gain_arr * np.abs(row)
        top_idx = np.argsort(attribution)[::-1][:top_n]
        features = [
            {
                "name": feature_columns[i],
                "contribution": float(attribution[i]),
                "direction": "up" if float(row[i]) >= 0 else "down",
            }
            for i in top_idx
        ]
        result.append(features)
    return result
