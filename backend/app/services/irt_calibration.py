"""
IRT 2PL Calibration Pipeline — Sprint 11 T03
=============================================
Fits (or simulates) Item Response Theory 2-Parameter Logistic (2PL) parameters
for every active Question and persists results in the `irt_parameters` table.

Two operating modes selected automatically per item:
  - Real-data mode   : question has ≥ IRT_MIN_SAMPLE graded responses →
                       fit a 2PL model via scipy MLE, mark is_synthetic=False.
  - Synthetic-bootstrap: fewer responses → generate synthetic responses seeded
                       by instructor `difficulty` label as the `b` prior,
                       mark is_synthetic=True (never drives production
                       recommendations until replaced by real fits).

The fitting algorithm uses scipy.optimize L-BFGS-B maximisation of the 2PL
log-likelihood. py-irt (PyTorch/Pyro) is listed in requirements-ml.txt as the
production upgrade path; for now scipy MLE gives sufficient accuracy for the
recovery tests (|Δa| < 0.3, |Δb| < 0.3 within the standard regime).

CLI:
    python -m app.jobs.recalibrate_irt --since 90d --min-sample 200 --dry-run
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from sqlalchemy.orm import Session

from app.constants import IRT_MIN_SAMPLE, IRT_MODEL
from db.database import (
    GradingStatus,
    IRTParameters,
    Question,
    QuizAnswer,
    QuizAttempt,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DIFFICULTY_TO_B: dict[str, float] = {
    "beginner": -1.0,
    "easy":     -1.0,
    "medium":    0.0,
    "intermediate": 0.0,
    "advanced":  1.0,
    "hard":      1.0,
}

_A_PRIOR_DEFAULT = 1.0     # discrimination prior for synthetic bootstrap
_A_PRIOR_NOISE   = 0.25    # ± uniform noise around the prior
_SCIPY_BOUNDS    = [(0.05, 5.0), (-4.0, 4.0)]   # (a, b) bounds for MLE
_N_SIMULEES_DEFAULT = 300  # synthetic simulees per item when real data is sparse


# ---------------------------------------------------------------------------
# 2PL math helpers
# ---------------------------------------------------------------------------

def _icc_2pl(theta: np.ndarray, a: float, b: float) -> np.ndarray:
    """2PL Item Characteristic Curve: P(correct | θ) = σ(a·(θ − b))."""
    return expit(a * (theta - b))


def simulate_responses(
    a: float,
    b: float,
    n_simulees: int = _N_SIMULEES_DEFAULT,
    seed: Optional[int] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate synthetic (ability, response) pairs for a 2PL item.

    Abilities are sampled from N(0, 1) (the standard IRT ability scale).
    Responses are Bernoulli draws from the 2PL ICC.

    Returns
    -------
    abilities  : float array of shape (n_simulees,)
    responses  : int array of shape (n_simulees,) — 0 or 1
    """
    rng = np.random.default_rng(seed)
    abilities = rng.standard_normal(n_simulees)
    probs = _icc_2pl(abilities, a, b)
    responses = rng.binomial(1, probs).astype(float)
    return abilities, responses


def fit_2pl_mle(
    abilities: np.ndarray,
    responses: np.ndarray,
) -> tuple[float, float, float]:
    """
    Fit 2PL parameters via maximum likelihood estimation (scipy L-BFGS-B).

    Parameters
    ----------
    abilities  : student ability estimates θ (same scale as calibration)
    responses  : binary response vector (0/1)

    Returns
    -------
    (a_hat, b_hat, log_likelihood)
    """
    abilities = np.asarray(abilities, dtype=float)
    responses = np.asarray(responses, dtype=float)

    def neg_ll(params: np.ndarray) -> float:
        a, b = params
        p = _icc_2pl(abilities, a, b)
        p = np.clip(p, 1e-9, 1.0 - 1e-9)
        return -float(np.sum(responses * np.log(p) + (1.0 - responses) * np.log(1.0 - p)))

    # Multiple starting points to reduce risk of local optima
    best_result = None
    for a0, b0 in [(1.0, 0.0), (0.5, -0.5), (1.5, 0.5), (0.8, -1.0)]:
        result = minimize(
            neg_ll,
            x0=np.array([a0, b0]),
            method="L-BFGS-B",
            bounds=_SCIPY_BOUNDS,
            options={"maxiter": 500, "ftol": 1e-10},
        )
        if best_result is None or result.fun < best_result.fun:
            best_result = result

    a_hat, b_hat = best_result.x
    log_likelihood = -float(best_result.fun)
    return float(a_hat), float(b_hat), log_likelihood


# ---------------------------------------------------------------------------
# Student ability estimation
# ---------------------------------------------------------------------------

def _estimate_abilities(
    per_user_correct: dict[str, int],
    per_user_total: dict[str, int],
) -> dict[str, float]:
    """
    Estimate student ability θ as the logit of the overall proportion correct.

    Uses proportion-correct scoring as a rough MLE under the 1PL (Rasch) model.
    Clamped to [0.01, 0.99] to keep θ finite.
    """
    abilities: dict[str, float] = {}
    for uid in per_user_correct:
        total = per_user_total.get(uid, 0)
        if total == 0:
            abilities[uid] = 0.0
        else:
            p = np.clip(per_user_correct[uid] / total, 0.01, 0.99)
            abilities[uid] = float(np.log(p / (1.0 - p)))
    return abilities


# ---------------------------------------------------------------------------
# Real-data extraction
# ---------------------------------------------------------------------------

def _fetch_real_responses(
    db: Session,
    since_days: int,
) -> dict[int, dict[str, int]]:
    """
    Pull graded quiz answers and return {question_id: {user_id: is_correct}}.

    Correctness is binarized: score ≥ 50% of max_score → 1.
    """
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=since_days)

    rows = (
        db.query(
            QuizAnswer.question_id,
            QuizAttempt.user_id,
            QuizAnswer.auto_score,
            QuizAnswer.instructor_score,
            Question.max_score,
        )
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .join(Question, QuizAnswer.question_id == Question.id)
        .filter(
            QuizAnswer.grading_status.in_([GradingStatus.GRADED, GradingStatus.PUBLISHED]),
            QuizAttempt.created_at >= cutoff,
        )
        .all()
    )

    per_item: dict[int, dict[str, int]] = {}
    for q_id, u_id, auto_s, inst_s, max_s in rows:
        score = inst_s if inst_s is not None else auto_s
        if score is None or max_s is None or max_s == 0:
            continue
        is_correct = int(score >= max_s * 0.5)
        per_item.setdefault(q_id, {})[u_id] = is_correct

    return per_item


# ---------------------------------------------------------------------------
# Calibration pipeline
# ---------------------------------------------------------------------------

def _difficulty_to_b(difficulty: str) -> float:
    return _DIFFICULTY_TO_B.get(str(difficulty).lower().strip(), 0.0)


def calibrate_item(
    question: Question,
    real_responses: dict[str, int],   # {user_id: 0/1}
    abilities: dict[str, float],       # {user_id: theta}
    run_id: str,
    min_sample: int,
    seed: Optional[int] = None,
) -> dict:
    """
    Calibrate one item. Returns a result dict regardless of mode.
    Does NOT write to the database (caller handles persistence).
    """
    q_id = question.id
    rng = np.random.default_rng(seed if seed is not None else q_id)

    n_real = len(real_responses)
    use_real = n_real >= min_sample

    if use_real:
        valid_users = [uid for uid in real_responses if uid in abilities]
        if len(valid_users) < min_sample:
            use_real = False

    if use_real:
        valid_users = sorted(real_responses.keys(), key=lambda u: u)
        theta = np.array([abilities[u] for u in valid_users if u in abilities])
        resp  = np.array([real_responses[u] for u in valid_users if u in abilities], dtype=float)
        a_hat, b_hat, ll = fit_2pl_mle(theta, resp)
        is_synthetic = False
        sample_size = int(len(resp))
    else:
        # Synthetic bootstrap
        b_prior = _difficulty_to_b(question.difficulty)
        a_prior = _A_PRIOR_DEFAULT + float(rng.uniform(-_A_PRIOR_NOISE, _A_PRIOR_NOISE))
        sim_theta, sim_resp = simulate_responses(
            a=a_prior,
            b=b_prior,
            n_simulees=max(min_sample, _N_SIMULEES_DEFAULT),
            seed=int(rng.integers(0, 2**31)),
        )
        a_hat, b_hat, ll = fit_2pl_mle(sim_theta, sim_resp)
        is_synthetic = True
        sample_size = len(sim_resp)

    return {
        "question_id": question.id,
        "question_str_id": question.question_id,
        "model": IRT_MODEL,
        "difficulty_b": round(b_hat, 4),
        "discrimination_a": round(a_hat, 4),
        "sample_size": sample_size,
        "fit_log_likelihood": round(ll, 4),
        "is_synthetic": is_synthetic,
        "calibration_run_id": run_id,
    }


def run_calibration(
    db: Session,
    since_days: int = 90,
    min_sample: int = IRT_MIN_SAMPLE,
    dry_run: bool = False,
    seed: Optional[int] = None,
) -> dict:
    """
    Full calibration pipeline: fetch real data → estimate abilities → calibrate
    all active questions → upsert IRTParameters rows atomically.

    Parameters
    ----------
    db          : SQLAlchemy session
    since_days  : window for pulling real graded answers (default 90 days)
    min_sample  : minimum real responses per item to use real-data mode
    dry_run     : compute calibration but do not write to the database
    seed        : random seed for reproducibility (affects synthetic mode only)

    Returns
    -------
    dict with run_id, n_items_real, n_items_synthetic, n_items_total, results list
    """
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)

    logger.info(
        '{"job": "recalibrate_irt", "run_id": "%s", "since_days": %d, "min_sample": %d, "dry_run": %s}',
        run_id, since_days, min_sample, dry_run,
    )

    # 1. Pull real graded responses
    real_data = _fetch_real_responses(db, since_days)

    # 2. Estimate student abilities from real data
    per_user_correct: dict[str, int] = {}
    per_user_total: dict[str, int]   = {}
    for item_resps in real_data.values():
        for uid, is_correct in item_resps.items():
            per_user_correct[uid] = per_user_correct.get(uid, 0) + is_correct
            per_user_total[uid]   = per_user_total.get(uid, 0) + 1
    abilities = _estimate_abilities(per_user_correct, per_user_total)

    # 3. Load all active questions
    questions = (
        db.query(Question)
        .filter(Question.is_active.is_(True), Question.is_archived.is_(False))
        .all()
    )

    if not questions:
        logger.warning("recalibrate_irt: no active questions found — nothing to calibrate")
        return {
            "run_id": run_id,
            "n_items_total": 0,
            "n_items_real": 0,
            "n_items_synthetic": 0,
            "dry_run": dry_run,
            "results": [],
        }

    # 4. Calibrate each item
    results: list[dict] = []
    n_real = 0
    n_synthetic = 0

    for q in questions:
        item_resps = real_data.get(q.id, {})
        result = calibrate_item(
            question=q,
            real_responses=item_resps,
            abilities=abilities,
            run_id=run_id,
            min_sample=min_sample,
            seed=seed,
        )
        results.append(result)
        if result["is_synthetic"]:
            n_synthetic += 1
        else:
            n_real += 1

        logger.info(
            '{"question_id": "%s", "b": %.4f, "a": %.4f, "n": %d, "synthetic": %s, "run_id": "%s"}',
            result["question_str_id"],
            result["difficulty_b"],
            result["discrimination_a"],
            result["sample_size"],
            result["is_synthetic"],
            run_id,
        )

    # 5. Upsert to database (atomically)
    if not dry_run:
        _upsert_results(db, results)

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    summary = {
        "run_id": run_id,
        "n_items_total": len(results),
        "n_items_real": n_real,
        "n_items_synthetic": n_synthetic,
        "dry_run": dry_run,
        "duration_ms": duration_ms,
        "results": results,
    }
    logger.info(
        '{"job": "recalibrate_irt", "run_id": "%s", "total": %d, "real": %d, "synthetic": %d, "duration_ms": %d}',
        run_id, len(results), n_real, n_synthetic, duration_ms,
    )
    return summary


def _upsert_results(db: Session, results: list[dict]) -> None:
    """Atomically upsert IRTParameters rows for one calibration run."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for r in results:
        existing = (
            db.query(IRTParameters)
            .filter(IRTParameters.question_id == r["question_id"])
            .first()
        )
        if existing is not None:
            existing.model = r["model"]
            existing.difficulty_b = r["difficulty_b"]
            existing.discrimination_a = r["discrimination_a"]
            existing.sample_size = r["sample_size"]
            existing.fit_log_likelihood = r["fit_log_likelihood"]
            existing.is_synthetic = r["is_synthetic"]
            existing.calibrated_at = now
            existing.calibration_run_id = r["calibration_run_id"]
        else:
            db.add(IRTParameters(
                question_id=r["question_id"],
                model=r["model"],
                difficulty_b=r["difficulty_b"],
                discrimination_a=r["discrimination_a"],
                sample_size=r["sample_size"],
                fit_log_likelihood=r["fit_log_likelihood"],
                is_synthetic=r["is_synthetic"],
                calibrated_at=now,
                calibration_run_id=r["calibration_run_id"],
            ))

    db.flush()
