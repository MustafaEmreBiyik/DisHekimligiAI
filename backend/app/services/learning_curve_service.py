"""
Learning Curve Service — Sprint 14B S14B-2
==========================================
Fits a parametric learning curve to a student's per-topic accuracy trajectory
and projects the estimated number of trials needed to reach mastery.

Two models are attempted; the better fit (higher R²) is returned:

  Exponential saturation (Anderson 1982):
      acc(n) = L - (L - p0) * exp(-k * n)
      L  = asymptotic accuracy  [0, 1]
      p0 = initial accuracy     [0, 1]
      k  = learning rate        (> 0)

  Power-law of learning (Newell & Rosenbloom 1981):
      acc(n) = L - b * n^(-c)
      L = asymptote, b = initial gap, c = decay exponent

Mastery projection: smallest integer n_proj such that fitted acc(n_proj) ≥
MASTERY_THRESHOLD (default 0.70).  Capped at MAX_PROJECTION_TRIALS when the
curve never crosses the threshold.

Usage
-----
from app.services.learning_curve_service import build_learning_curves

result = build_learning_curves(user_id="stu_001", db=db_session)
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

import numpy as np
from scipy.optimize import curve_fit
from sqlalchemy.orm import Session

from app.constants import TOPIC_LABELS
from app.services.bkt_service import _canonicalise_topic_id
from app.services.mastery_trajectory_service import build_trajectory

MASTERY_THRESHOLD = 0.70
MAX_PROJECTION_TRIALS = 200
MIN_POINTS_FOR_FIT = 3   # need at least this many observations to fit


# ── Learning curve models ──────────────────────────────────────────────────────

def _exp_model(n: np.ndarray, L: float, p0: float, k: float) -> np.ndarray:
    """Exponential saturation: acc(n) = L - (L - p0) * exp(-k * n)."""
    return L - (L - p0) * np.exp(-k * n)


def _power_model(n: np.ndarray, L: float, b: float, c: float) -> np.ndarray:
    """Power-law: acc(n) = L - b * n^(-c)."""
    return L - b * np.power(np.maximum(n, 1e-9), -c)


def _r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot < 1e-12:
        return 1.0  # constant signal → perfect fit by convention
    return float(1.0 - ss_res / ss_tot)


def _project_mastery(model_fn, params: tuple, current_n: int) -> Optional[int]:
    """Return first n > current_n where model crosses MASTERY_THRESHOLD, or None."""
    for n in range(current_n + 1, MAX_PROJECTION_TRIALS + 1):
        if model_fn(np.array([float(n)]), *params)[0] >= MASTERY_THRESHOLD:
            return n
    return None


def _fit_topic(
    points: list[dict],
) -> dict:
    """
    Fit learning curves to a topic's trajectory points.

    Parameters
    ----------
    points : list of trajectory point dicts (must have 'n', 'correct')

    Returns
    -------
    fit dict with model name, params, R², projected mastery trial, fitted curve.
    """
    ns = np.array([p["n"] for p in points], dtype=float)
    # Cumulative accuracy at each trial n
    cumulative_correct = np.cumsum([1.0 if p["correct"] else 0.0 for p in points])
    acc = cumulative_correct / ns

    if len(ns) < MIN_POINTS_FOR_FIT:
        return {
            "model": None,
            "params": {},
            "r_squared": None,
            "projected_trials_to_mastery": None,
            "fitted_curve": [],
            "note": f"Yetersiz veri ({len(ns)}/{MIN_POINTS_FOR_FIT} gözlem gerekli)",
        }

    best: dict = {"r2": -np.inf}

    # --- Exponential saturation ---
    try:
        popt_e, _ = curve_fit(
            _exp_model,
            ns,
            acc,
            p0=[0.85, float(acc[0]), 0.3],
            bounds=([0, 0, 1e-4], [1, 1, 10]),
            maxfev=2000,
        )
        r2_e = _r_squared(acc, _exp_model(ns, *popt_e))
        if r2_e > best["r2"]:
            best = {
                "model": "exponential",
                "params": {"L": popt_e[0], "p0": popt_e[1], "k": popt_e[2]},
                "fn": _exp_model,
                "popt": popt_e,
                "r2": r2_e,
            }
    except Exception:
        pass

    # --- Power-law ---
    try:
        popt_p, _ = curve_fit(
            _power_model,
            ns,
            acc,
            p0=[0.85, 0.5, 0.5],
            bounds=([0, 0, 1e-4], [1, 2, 5]),
            maxfev=2000,
        )
        r2_p = _r_squared(acc, _power_model(ns, *popt_p))
        if r2_p > best["r2"]:
            best = {
                "model": "power_law",
                "params": {"L": popt_p[0], "b": popt_p[1], "c": popt_p[2]},
                "fn": _power_model,
                "popt": popt_p,
                "r2": r2_p,
            }
    except Exception:
        pass

    if best["r2"] == -np.inf:
        return {
            "model": None,
            "params": {},
            "r_squared": None,
            "projected_trials_to_mastery": None,
            "fitted_curve": [],
            "note": "Eğri uydurulamadı",
        }

    current_n = int(ns[-1])
    projection = _project_mastery(best["fn"], best["popt"], current_n)

    # Fitted curve points — observed range + projection horizon
    plot_end = max(current_n + 10, projection or 0, 20)
    fitted_curve = [
        {
            "n": i,
            "predicted": round(
                float(np.clip(best["fn"](np.array([float(i)]), *best["popt"])[0], 0, 1)), 4
            ),
        }
        for i in range(1, plot_end + 1)
    ]

    return {
        "model": best["model"],
        "params": {k: round(v, 4) for k, v in best["params"].items()},
        "r_squared": round(best["r2"], 4),
        "projected_trials_to_mastery": projection,
        "mastery_threshold": MASTERY_THRESHOLD,
        "fitted_curve": fitted_curve,
    }


# ── Public API ─────────────────────────────────────────────────────────────────

def build_learning_curves(
    user_id: str,
    db: Session,
    topic_id: Optional[str] = None,
) -> dict:
    """
    Build learning curve fits for all (or one) topic for *user_id*.

    Reuses the trajectory from mastery_trajectory_service so there is a single
    source of truth for observation replay.

    Returns
    -------
    {
      "user_id": str,
      "topics": [
        {
          "topic_id": str,
          "label": str,
          "n_observations": int,
          "observed_accuracy": [{"n": int, "cumulative_accuracy": float}, ...],
          "fit": {
            "model": "exponential" | "power_law" | null,
            "params": {...},
            "r_squared": float | null,
            "projected_trials_to_mastery": int | null,
            "mastery_threshold": float,
            "fitted_curve": [{"n": int, "predicted": float}, ...]
          }
        },
        ...
      ],
      "computed_at": str
    }
    """
    trajectory = build_trajectory(user_id=user_id, db=db, topic_id=topic_id)

    result_topics = []
    for traj_topic in trajectory["topics"]:
        points = traj_topic["points"]
        ns = [p["n"] for p in points]
        cumulative_correct = 0.0
        observed_accuracy = []
        for p in points:
            cumulative_correct += 1.0 if p["correct"] else 0.0
            observed_accuracy.append({
                "n": p["n"],
                "cumulative_accuracy": round(cumulative_correct / p["n"], 4),
            })

        fit = _fit_topic(points)

        result_topics.append({
            "topic_id": traj_topic["topic_id"],
            "label": traj_topic["label"],
            "n_observations": traj_topic["n_observations"],
            "observed_accuracy": observed_accuracy,
            "fit": fit,
        })

    return {
        "user_id": user_id,
        "topics": result_topics,
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }
