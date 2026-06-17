"""
BKT Prior EM-Fitting Service — Sprint 14 T07
=============================================
Fits Bayesian Knowledge Tracing priors (P_INIT, P_TRANSIT, P_SLIP, P_GUESS)
per topic from accumulated student observation sequences using the
Expectation-Maximization (EM) algorithm described in:

  Corbett & Anderson (1995). Knowledge tracing: Modeling the acquisition
  of procedural knowledge. User Modeling and User-Adapted Interaction.

Algorithm (Baum-Welch / EM for HMM):
  Latent state: L_t ∈ {0=unmastered, 1=mastered}
  Observed: y_t ∈ {0=incorrect, 1=correct}

  E-step: Forward-backward pass → γ_t = P(L_t=1 | y_1..y_T, θ)
           and ξ_t = P(L_t=0→1 transition at t | observations, θ)
  M-step: Update θ from sufficient statistics

  Repeat until log-likelihood converges (|ΔLL| < tol) or max_iter reached.

Persistence:
  Fitted priors are written to the `bkt_topic_priors` table (BKTTopicPrior model).
  Per-(student, topic) MasteryState rows are NOT rewritten here — a separate
  nightly refresh using bkt_service.recompute_for_user() applies updated priors.

Usage:
  from app.services.bkt_em_service import run_em_fitting, fit_topic_em

  result = run_em_fitting(db, min_observations=20, min_students=5, dry_run=False)
"""

from __future__ import annotations

import logging
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.constants import (
    BKT_P_GUESS,
    BKT_P_INIT,
    BKT_P_SLIP,
    BKT_P_TRANSIT,
    BKT_MIN_OBSERVATIONS_PER_TOPIC,
)
from db.database import (
    BKTTopicPrior,
    GradingStatus,
    MasteryState,
    Question,
    QuizAnswer,
    QuizAttempt,
)

logger = logging.getLogger(__name__)

# ── defaults ────────────────────────────────────────────────────────────────

EM_MAX_ITER: int = 100
EM_TOL: float = 1e-6
EM_MIN_STUDENTS: int = 5      # minimum distinct students per topic for EM
EM_MIN_OBSERVATIONS: int = 20  # minimum total observations per topic for EM

# Parameter bounds — hard floors/ceilings for numerical stability
_P_MIN = 1e-4
_P_MAX = 1.0 - 1e-4


# ── data classes ─────────────────────────────────────────────────────────────

@dataclass
class EMParams:
    """BKT parameters for a single topic."""
    p_init: float = BKT_P_INIT
    p_transit: float = BKT_P_TRANSIT
    p_slip: float = BKT_P_SLIP
    p_guess: float = BKT_P_GUESS


@dataclass
class EMFitResult:
    """Outcome of EM fitting for one topic."""
    topic_id: str
    p_init: float
    p_transit: float
    p_slip: float
    p_guess: float
    n_students: int
    n_observations: int
    log_likelihood: float
    converged: bool
    n_iterations: int
    is_synthetic: bool  # True when below data threshold → global defaults used


@dataclass
class RunSummary:
    """Aggregate summary returned by run_em_fitting()."""
    run_id: str
    n_topics_total: int
    n_topics_fitted: int
    n_topics_synthetic: int
    dry_run: bool
    results: list[EMFitResult] = field(default_factory=list)


# ── core EM math ─────────────────────────────────────────────────────────────

def _clip(v: float) -> float:
    return max(_P_MIN, min(_P_MAX, v))


def _emission(y: int, is_mastered: bool, p_slip: float, p_guess: float) -> float:
    """P(y | L=is_mastered) for one binary observation."""
    if is_mastered:
        return (1.0 - p_slip) if y == 1 else p_slip
    else:
        return p_guess if y == 1 else (1.0 - p_guess)


def _forward_backward(
    sequence: list[int],
    p_init: float,
    p_transit: float,
    p_slip: float,
    p_guess: float,
) -> tuple[list[float], float]:
    """
    Forward-backward pass for one student's observation sequence.

    Returns:
        gamma   list of P(L_t=1 | y_{1..T}, θ) for each time step
        log_lik log P(y_{1..T} | θ) for this sequence
    """
    T = len(sequence)
    if T == 0:
        return [], 0.0

    # Forward pass: alpha[t] = P(L_t=1, y_{1..t})
    alpha_1 = [0.0] * T  # state=mastered
    alpha_0 = [0.0] * T  # state=unmastered

    # t=0
    e1 = _emission(sequence[0], True, p_slip, p_guess)
    e0 = _emission(sequence[0], False, p_slip, p_guess)
    alpha_1[0] = p_init * e1
    alpha_0[0] = (1.0 - p_init) * e0

    # t>0  — BKT transition: once mastered, always mastered
    for t in range(1, T):
        e1 = _emission(sequence[t], True, p_slip, p_guess)
        e0 = _emission(sequence[t], False, p_slip, p_guess)
        # P(L_t=1) = P(L_{t-1}=1)*1 + P(L_{t-1}=0)*p_transit
        prior_1 = alpha_1[t - 1] + alpha_0[t - 1] * p_transit
        # P(L_t=0) = P(L_{t-1}=0)*(1-p_transit)
        prior_0 = alpha_0[t - 1] * (1.0 - p_transit)
        alpha_1[t] = prior_1 * e1
        alpha_0[t] = prior_0 * e0

    # Sequence likelihood
    seq_lik = alpha_1[-1] + alpha_0[-1]
    if seq_lik <= 0.0:
        return [0.5] * T, -math.inf

    log_lik = math.log(seq_lik)

    # Backward pass: beta[t] = P(y_{t+1..T} | L_t)
    beta_1 = [1.0] * T
    beta_0 = [1.0] * T
    for t in range(T - 2, -1, -1):
        e1_next = _emission(sequence[t + 1], True, p_slip, p_guess)
        e0_next = _emission(sequence[t + 1], False, p_slip, p_guess)
        # beta_1[t] = P(y_{t+1..T} | L_t=1)
        # From mastered: stay mastered (prob 1)
        beta_1[t] = e1_next * beta_1[t + 1] + 0.0  # can't go to 0
        # From unmastered: transit (p_transit → mastered) or stay (→ unmastered)
        beta_0[t] = (
            p_transit * e1_next * beta_1[t + 1]
            + (1.0 - p_transit) * e0_next * beta_0[t + 1]
        )

    # gamma[t] = P(L_t=1 | y, θ)
    gamma = []
    for t in range(T):
        num = alpha_1[t] * beta_1[t]
        denom = num + alpha_0[t] * beta_0[t]
        gamma.append(num / denom if denom > 1e-15 else 0.5)

    return gamma, log_lik


def fit_topic_em(
    sequences: list[list[int]],
    *,
    init_params: Optional[EMParams] = None,
    max_iter: int = EM_MAX_ITER,
    tol: float = EM_TOL,
) -> tuple[EMParams, float, bool, int]:
    """
    Run EM on a collection of binary observation sequences for one topic.

    Parameters
    ----------
    sequences : list[list[int]]
        Each inner list is one student's chronological 0/1 response sequence.
    init_params : EMParams | None
        Starting parameters. Defaults to global BKT constants.
    max_iter : int
        Maximum EM iterations.
    tol : float
        Convergence threshold on log-likelihood delta.

    Returns
    -------
    (params, log_likelihood, converged, n_iterations)
    """
    if init_params is None:
        init_params = EMParams()

    p_init = _clip(init_params.p_init)
    p_transit = _clip(init_params.p_transit)
    p_slip = _clip(init_params.p_slip)
    p_guess = _clip(init_params.p_guess)

    prev_ll = -math.inf
    converged = False
    n_iter = 0

    for iteration in range(max_iter):
        n_iter = iteration + 1
        total_ll = 0.0

        # Sufficient statistics
        ss_gamma0 = 0.0   # Σ γ_0  (initial mastery)
        ss_n_seqs = 0.0   # number of sequences (denominator for p_init)

        ss_trans_num = 0.0  # Σ γ_t * (1-γ_{t-1}) — weighted transitions
        ss_trans_den = 0.0  # Σ (1-γ_{t-1})

        # Emission sufficient statistics
        ss_slip_num = 0.0    # Σ_t γ_t * [y_t=0]   (mastered but wrong)
        ss_slip_den = 0.0    # Σ_t γ_t
        ss_guess_num = 0.0   # Σ_t (1-γ_t) * [y_t=1]  (unmastered but right)
        ss_guess_den = 0.0   # Σ_t (1-γ_t)

        for seq in sequences:
            if not seq:
                continue
            gamma, log_lik = _forward_backward(seq, p_init, p_transit, p_slip, p_guess)
            if not math.isfinite(log_lik):
                continue
            total_ll += log_lik

            ss_gamma0 += gamma[0]
            ss_n_seqs += 1.0

            for t, (obs, g) in enumerate(zip(seq, gamma)):
                ss_slip_den += g
                ss_guess_den += (1.0 - g)
                if obs == 0:
                    ss_slip_num += g
                else:
                    ss_guess_num += (1.0 - g)
                if t > 0:
                    ss_trans_den += (1.0 - gamma[t - 1])
                    # Expected transitions from 0→1
                    ss_trans_num += gamma[t] * (1.0 - gamma[t - 1])

        # M-step: update parameters from sufficient statistics
        if ss_n_seqs > 0:
            p_init = _clip(ss_gamma0 / ss_n_seqs)
        if ss_trans_den > 0:
            p_transit = _clip(ss_trans_num / ss_trans_den)
        if ss_slip_den > 0:
            p_slip = _clip(ss_slip_num / ss_slip_den)
        if ss_guess_den > 0:
            p_guess = _clip(ss_guess_num / ss_guess_den)

        # Convergence check
        delta_ll = total_ll - prev_ll
        if abs(delta_ll) < tol and iteration > 0:
            converged = True
            break
        prev_ll = total_ll

    return EMParams(p_init, p_transit, p_slip, p_guess), prev_ll, converged, n_iter


# ── data loading ─────────────────────────────────────────────────────────────

def _fetch_sequences(db: Session) -> dict[str, dict[str, list[int]]]:
    """
    Load graded observation sequences from DB.

    Returns:
        {topic_id: {user_id: [0/1, ...]}}  — chronological per student
    """
    rows = (
        db.query(
            QuizAttempt.user_id,
            Question.topic_id,
            QuizAnswer.auto_score,
            QuizAnswer.instructor_score,
            Question.max_score,
            QuizAnswer.id.label("answer_id"),
        )
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .join(Question, QuizAnswer.question_id == Question.id)
        .filter(
            QuizAnswer.grading_status.in_([GradingStatus.GRADED, GradingStatus.PUBLISHED]),
            Question.topic_id.isnot(None),
            Question.topic_id != "",
        )
        .order_by(QuizAnswer.id)
        .all()
    )

    data: dict[str, dict[str, list[int]]] = {}
    for row in rows:
        topic_id = row.topic_id.strip().lower()
        user_id = row.user_id
        score = row.instructor_score if row.instructor_score is not None else row.auto_score
        if score is None:
            continue
        max_score = row.max_score or 1.0
        correct = int(score >= max_score * 0.5)

        data.setdefault(topic_id, {}).setdefault(user_id, []).append(correct)

    return data


# ── upsert ────────────────────────────────────────────────────────────────────

def _upsert_prior(db: Session, result: EMFitResult, run_id: str) -> None:
    """Insert or update BKTTopicPrior row for this topic."""
    existing = (
        db.query(BKTTopicPrior)
        .filter(BKTTopicPrior.topic_id == result.topic_id)
        .first()
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if existing is not None:
        existing.p_init = result.p_init
        existing.p_transit = result.p_transit
        existing.p_slip = result.p_slip
        existing.p_guess = result.p_guess
        existing.n_students = result.n_students
        existing.n_observations = result.n_observations
        existing.log_likelihood = result.log_likelihood
        existing.converged = result.converged
        existing.is_synthetic = result.is_synthetic
        existing.calibration_run_id = run_id
        existing.fitted_at = now
    else:
        db.add(
            BKTTopicPrior(
                topic_id=result.topic_id,
                p_init=result.p_init,
                p_transit=result.p_transit,
                p_slip=result.p_slip,
                p_guess=result.p_guess,
                n_students=result.n_students,
                n_observations=result.n_observations,
                log_likelihood=result.log_likelihood,
                converged=result.converged,
                is_synthetic=result.is_synthetic,
                calibration_run_id=run_id,
                fitted_at=now,
            )
        )


# ── public API ────────────────────────────────────────────────────────────────

def run_em_fitting(
    db: Session,
    *,
    min_students: int = EM_MIN_STUDENTS,
    min_observations: int = EM_MIN_OBSERVATIONS,
    max_iter: int = EM_MAX_ITER,
    tol: float = EM_TOL,
    dry_run: bool = False,
) -> RunSummary:
    """
    Run EM fitting for all topics that have enough real data.

    Topics below threshold receive `is_synthetic=True` and keep global defaults.
    Results are upserted into `bkt_topic_priors` (unless dry_run=True).

    Returns a RunSummary with per-topic EMFitResult objects.
    """
    run_id = str(uuid.uuid4())
    topic_data = _fetch_sequences(db)

    results: list[EMFitResult] = []
    n_fitted = 0
    n_synthetic = 0

    for topic_id, student_seqs in sorted(topic_data.items()):
        n_students = len(student_seqs)
        sequences = list(student_seqs.values())
        n_observations = sum(len(s) for s in sequences)

        has_enough_data = (
            n_students >= min_students and n_observations >= min_observations
        )

        if has_enough_data:
            params, ll, converged, n_iter = fit_topic_em(
                sequences, max_iter=max_iter, tol=tol
            )
            result = EMFitResult(
                topic_id=topic_id,
                p_init=params.p_init,
                p_transit=params.p_transit,
                p_slip=params.p_slip,
                p_guess=params.p_guess,
                n_students=n_students,
                n_observations=n_observations,
                log_likelihood=ll,
                converged=converged,
                n_iterations=n_iter,
                is_synthetic=False,
            )
            n_fitted += 1
            logger.info(
                "EM fitted: topic=%s students=%d obs=%d ll=%.4f converged=%s iter=%d",
                topic_id, n_students, n_observations, ll, converged, n_iter,
            )
        else:
            result = EMFitResult(
                topic_id=topic_id,
                p_init=BKT_P_INIT,
                p_transit=BKT_P_TRANSIT,
                p_slip=BKT_P_SLIP,
                p_guess=BKT_P_GUESS,
                n_students=n_students,
                n_observations=n_observations,
                log_likelihood=float("nan"),
                converged=False,
                n_iterations=0,
                is_synthetic=True,
            )
            n_synthetic += 1
            logger.info(
                "EM skipped (insufficient data): topic=%s students=%d obs=%d (need %d/%d)",
                topic_id, n_students, n_observations, min_students, min_observations,
            )

        results.append(result)

        if not dry_run:
            _upsert_prior(db, result, run_id)

    return RunSummary(
        run_id=run_id,
        n_topics_total=len(topic_data),
        n_topics_fitted=n_fitted,
        n_topics_synthetic=n_synthetic,
        dry_run=dry_run,
        results=results,
    )


def get_topic_prior(db: Session, topic_id: str) -> EMParams:
    """
    Return the fitted prior for a topic, falling back to global defaults.

    Used by bkt_service.observe() to seed new MasteryState rows with
    topic-specific priors instead of the global constants.
    """
    topic_id = topic_id.strip().lower()
    row = (
        db.query(BKTTopicPrior)
        .filter(BKTTopicPrior.topic_id == topic_id, BKTTopicPrior.is_synthetic.is_(False))
        .first()
    )
    if row is None:
        return EMParams()
    return EMParams(
        p_init=row.p_init,
        p_transit=row.p_transit,
        p_slip=row.p_slip,
        p_guess=row.p_guess,
    )
