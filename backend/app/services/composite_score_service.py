"""
Composite Score Service
=======================
Calculates the weighted overall score for a student across three source types:

  - MCQ answers         design weight: 35%
  - Open-ended answers  design weight: 40%
  - Case simulations    design weight: 25%

The composite is computed from published/graded data only.
Missing components do not raise errors — they are flagged as unavailable and
their design weight is redistributed proportionally across available components
so the composite still falls in [0, 100].

Usage example
-------------
from app.services.composite_score_service import calculate_composite_score

result = calculate_composite_score(user_id="stu_001", db=db_session)
print(result.composite_pct)   # e.g. 72.5 or None (cold start)
print(result.mcq.available)   # True / False
print(result.mcq.pct)         # 85.0 or None
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from db.database import (
    ExamResult,
    GradingStatus,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
)

# ── Design weights ──────────────────────────────────────────────────────────

from app.constants import COMPOSITE_WEIGHTS

_MCQ_WEIGHT: float = COMPOSITE_WEIGHTS["mcq"]
_OE_WEIGHT: float = COMPOSITE_WEIGHTS["oe"]
_CASE_WEIGHT: float = COMPOSITE_WEIGHTS["case"]

assert abs(_MCQ_WEIGHT + _OE_WEIGHT + _CASE_WEIGHT - 1.0) < 1e-9, (
    "Design weights must sum to exactly 1.0"
)


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class ComponentScore:
    """Score breakdown for one assessment component (MCQ, OE, or Case)."""

    available: bool
    """
    True when at least one published/graded record exists for this component.
    False means no attempt or no graded data yet — not that the student scored zero.
    """

    earned: int
    """Total earned score points across all published/graded records (0 when unavailable)."""

    max_possible: int
    """Total possible score points across all published/graded records (0 when unavailable)."""

    pct: Optional[float]
    """
    Score as a percentage in [0.0, 100.0].
    None  → unavailable (distinguish from 0.0 which means an attempt existed but scored zero).
    """

    design_weight: float
    """Intended weight for this component per the product spec (0.35 / 0.40 / 0.25)."""

    effective_weight: float
    """
    Actual weight applied in composite calculation for this request.
    Equals design_weight when all three components are available.
    Redistributed proportionally when one or more components are missing.
    """


@dataclass
class CompositeScoreResult:
    """Full composite score breakdown for one student."""

    mcq: ComponentScore
    open_ended: ComponentScore
    case: ComponentScore

    composite_pct: Optional[float]
    """
    Weighted composite percentage in [0.0, 100.0].
    None only when ALL three components are unavailable (true cold-start student).
    0.0 is a valid value meaning the student has history but earned zero points.
    """

    all_components_available: bool
    """True when all three components have at least one published/graded record."""

    computed_at: str
    """ISO-8601 UTC timestamp of when this result was computed."""


# ── Private query helpers ───────────────────────────────────────────────────

def _fetch_mcq_component(user_id: str, db: Session) -> tuple[int, int]:
    """
    Return (earned, max_possible) for all published MCQ answers belonging to *user_id*.

    Only QuizAnswer rows where:
      - The parent QuizAttempt belongs to this user
      - The linked Question is of type MCQ
      - grading_status is PUBLISHED
    are counted. auto_score is used as earned points.
    """
    rows = (
        db.query(QuizAnswer, Question)
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .join(Question, QuizAnswer.question_id == Question.id)
        .filter(
            QuizAttempt.user_id == user_id,
            Question.question_type == QuestionType.MCQ,
            QuizAnswer.grading_status == GradingStatus.PUBLISHED,
        )
        .all()
    )
    earned = sum((ans.auto_score or 0) for ans, _q in rows)
    max_possible = sum(_q.max_score for _ans, _q in rows)
    return earned, max_possible


def _fetch_oe_component(user_id: str, db: Session) -> tuple[int, int]:
    """
    Return (earned, max_possible) for all published open-ended answers belonging to *user_id*.

    Only QuizAnswer rows where:
      - The parent QuizAttempt belongs to this user
      - The linked Question is of type OPEN_ENDED
      - grading_status is PUBLISHED (instructor has graded and published)
    are counted. instructor_score is used as earned points.
    """
    rows = (
        db.query(QuizAnswer, Question)
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .join(Question, QuizAnswer.question_id == Question.id)
        .filter(
            QuizAttempt.user_id == user_id,
            Question.question_type == QuestionType.OPEN_ENDED,
            QuizAnswer.grading_status == GradingStatus.PUBLISHED,
        )
        .all()
    )
    earned = sum((ans.instructor_score or 0) for ans, _q in rows)
    max_possible = sum(_q.max_score for _ans, _q in rows)
    return earned, max_possible


def _fetch_case_component(user_id: str, db: Session) -> tuple[int, int]:
    """
    Return (earned, max_possible) for completed case simulation results.

    Uses ExamResult rows where:
      - user_id matches
      - max_score > 0 (guards against degenerate records)
      - case_id != 'quiz_global' (excludes legacy MCQ records written by the
        old quiz submit path before the S8B migration)
    """
    rows = (
        db.query(ExamResult)
        .filter(
            ExamResult.user_id == user_id,
            ExamResult.max_score > 0,
            ExamResult.case_id != "quiz_global",
        )
        .all()
    )
    earned = sum(r.score for r in rows)
    max_possible = sum(r.max_score for r in rows)
    return earned, max_possible


def _redistribute_weights(
    mcq_avail: bool,
    oe_avail: bool,
    case_avail: bool,
) -> tuple[float, float, float]:
    """
    Compute effective weights for (mcq, oe, case) given availability flags.

    Unavailable components receive effective weight 0.0.
    The remaining design weights are scaled so they sum to 1.0.
    Returns (0.0, 0.0, 0.0) only when all three components are unavailable.
    """
    pool: dict[str, float] = {}
    if mcq_avail:
        pool["mcq"] = _MCQ_WEIGHT
    if oe_avail:
        pool["oe"] = _OE_WEIGHT
    if case_avail:
        pool["case"] = _CASE_WEIGHT

    total = sum(pool.values())
    if total == 0.0:
        return 0.0, 0.0, 0.0

    scale = 1.0 / total
    return (
        round(pool.get("mcq", 0.0) * scale, 10),
        round(pool.get("oe", 0.0) * scale, 10),
        round(pool.get("case", 0.0) * scale, 10),
    )


def _make_component(
    earned: int,
    max_possible: int,
    design_weight: float,
    effective_weight: float,
) -> ComponentScore:
    available = max_possible > 0
    pct: Optional[float] = round((earned / max_possible) * 100.0, 2) if available else None
    return ComponentScore(
        available=available,
        earned=earned,
        max_possible=max_possible,
        pct=pct,
        design_weight=design_weight,
        effective_weight=effective_weight,
    )


# ── Public API ──────────────────────────────────────────────────────────────

def calculate_composite_score(user_id: str, db: Session) -> CompositeScoreResult:
    """
    Calculate and return the weighted composite score for *user_id*.

    Behaviour summary
    -----------------
    - Only published/graded records are counted.
    - A component is "available" when it has at least one published record.
    - If a component is unavailable its design weight is redistributed across
      the available components so the composite still sums to 100% max.
    - composite_pct is None only when ALL components are unavailable (cold start).
    - composite_pct is 0.0 when the student has history but scored zero everywhere.

    Parameters
    ----------
    user_id : str
        The user_id value stored in QuizAttempt.user_id and ExamResult.user_id.
    db : Session
        An active SQLAlchemy session.

    Returns
    -------
    CompositeScoreResult
        Full breakdown with per-component details and the composite percentage.
    """
    mcq_earned, mcq_max = _fetch_mcq_component(user_id, db)
    oe_earned, oe_max = _fetch_oe_component(user_id, db)
    case_earned, case_max = _fetch_case_component(user_id, db)

    mcq_avail = mcq_max > 0
    oe_avail = oe_max > 0
    case_avail = case_max > 0

    eff_mcq, eff_oe, eff_case = _redistribute_weights(mcq_avail, oe_avail, case_avail)

    mcq_comp = _make_component(mcq_earned, mcq_max, _MCQ_WEIGHT, eff_mcq)
    oe_comp = _make_component(oe_earned, oe_max, _OE_WEIGHT, eff_oe)
    case_comp = _make_component(case_earned, case_max, _CASE_WEIGHT, eff_case)

    any_available = mcq_avail or oe_avail or case_avail

    if any_available:
        composite_pct: Optional[float] = round(
            (mcq_comp.pct or 0.0) * eff_mcq
            + (oe_comp.pct or 0.0) * eff_oe
            + (case_comp.pct or 0.0) * eff_case,
            2,
        )
    else:
        composite_pct = None  # true cold start — student has no history at all

    return CompositeScoreResult(
        mcq=mcq_comp,
        open_ended=oe_comp,
        case=case_comp,
        composite_pct=composite_pct,
        all_components_available=mcq_avail and oe_avail and case_avail,
        computed_at=datetime.datetime.utcnow().isoformat() + "Z",
    )
