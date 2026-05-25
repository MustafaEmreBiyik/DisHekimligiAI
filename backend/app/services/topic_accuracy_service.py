"""
Topic Accuracy Service
======================
Calculates per-topic MCQ performance for a student.

Only **published** MCQ answers are counted — PENDING and GRADED are excluded.
Results are sorted weakest-first so callers can immediately surface the most
problematic topics at the top of a report.

Usage example
-------------
from app.services.topic_accuracy_service import get_topic_accuracy

result = get_topic_accuracy(user_id="stu_001", db=db_session)
print(result.has_any_data)          # True / False
for t in result.topics:
    print(t.topic_id, t.pct, t.is_weak)
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from db.database import (
    GradingStatus,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
)

# ── Configuration ─────────────────────────────────────────────────────────────

from app.constants import TOPIC_LABELS, WEAK_THRESHOLD_PCT

_WEAK_THRESHOLD_PCT: float = WEAK_THRESHOLD_PCT
_UNTAGGED_TOPIC_ID: str = "untagged"
_TOPIC_LABELS: dict[str, str] = TOPIC_LABELS


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class TopicAccuracy:
    """Per-topic MCQ accuracy breakdown for one student."""

    topic_id: str
    """
    Normalised topic identifier from Question.topic_id.
    Empty or None topic_id values are stored here as "untagged".
    """

    topic_label: str
    """
    Human-readable label.  Falls back to topic_id when no label is registered.
    """

    earned: int
    """Total auto_score points earned across all published MCQ answers in this topic."""

    max_possible: int
    """Total max_score points available across all published MCQ answers in this topic."""

    pct: Optional[float]
    """
    Accuracy percentage in [0.0, 100.0], rounded to 2 decimal places.
    None when max_possible == 0 (defensive; should not occur if the record is
    published with a question that has max_score > 0).
    """

    answered_count: int
    """Number of published MCQ answers in this topic."""

    correct_count: int
    """
    Answers where the student earned the full question max_score.
    For standard binary MCQ (max_score = 1) this is the same as earned.
    """

    is_weak: bool
    """
    True when pct is not None and pct < _WEAK_THRESHOLD_PCT (default 60 %).
    False for strong topics and for topics where pct is None.
    """


@dataclass
class TopicAccuracyResult:
    """Full topic accuracy breakdown for one student."""

    topics: list[TopicAccuracy] = field(default_factory=list)
    """
    Per-topic results.

    Sorted: weak topics first (ascending pct), then strong topics
    (ascending pct), then topics whose pct is None (should not appear
    in practice but included for safety).
    """

    has_any_data: bool = False
    """True when at least one published MCQ answer exists for this student."""

    computed_at: str = ""
    """ISO-8601 UTC timestamp when this result was computed."""


# ── Private helpers ────────────────────────────────────────────────────────────

def _normalise_topic_id(raw: Optional[str]) -> str:
    """Return the canonical topic identifier, mapping blanks/None to UNTAGGED."""
    if not raw or not raw.strip():
        return _UNTAGGED_TOPIC_ID
    return raw.strip()


def _resolve_label(topic_id: str) -> str:
    """Return the registered display label, falling back to topic_id itself."""
    return _TOPIC_LABELS.get(topic_id, topic_id)


def _sort_key(t: TopicAccuracy):
    """
    Sort order: weak topics first (lowest pct), strong topics next
    (still ascending so borderline topics appear before excellent ones),
    None pct at the very end.

    Returned tuple: (bucket, pct_or_inf)
      bucket 0 → weak
      bucket 1 → strong
      bucket 2 → pct is None
    """
    if t.pct is None:
        return (2, 0.0)
    if t.is_weak:
        return (0, t.pct)
    return (1, t.pct)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_topic_accuracy(user_id: str, db: Session) -> TopicAccuracyResult:
    """
    Calculate and return per-topic MCQ accuracy for *user_id*.

    Behaviour summary
    -----------------
    - Only QuizAnswer rows with grading_status == PUBLISHED are counted.
    - Only MCQ questions are included (Open-Ended answers are excluded).
    - Questions with an empty or missing topic_id are grouped under "untagged".
    - A topic is marked weak when pct < 60.0.
    - Topics are sorted weakest-first.
    - has_any_data is False when the student has no published MCQ answers at all.

    Parameters
    ----------
    user_id : str
        The user_id stored in QuizAttempt.user_id.
    db : Session
        An active SQLAlchemy session.

    Returns
    -------
    TopicAccuracyResult
        Full per-topic breakdown sorted weakest-first.
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

    computed_at = datetime.datetime.utcnow().isoformat() + "Z"

    if not rows:
        return TopicAccuracyResult(
            topics=[],
            has_any_data=False,
            computed_at=computed_at,
        )

    # ── Accumulate per-topic buckets ─────────────────────────────────────────

    # topic_id → {"earned": int, "max": int, "answered": int, "correct": int}
    buckets: dict[str, dict] = {}

    for ans, q in rows:
        topic_id = _normalise_topic_id(q.topic_id)
        if topic_id not in buckets:
            buckets[topic_id] = {"earned": 0, "max": 0, "answered": 0, "correct": 0}

        score = ans.auto_score or 0
        q_max = q.max_score  # always > 0 for published answers in practice

        buckets[topic_id]["earned"] += score
        buckets[topic_id]["max"] += q_max
        buckets[topic_id]["answered"] += 1
        if score >= q_max:
            buckets[topic_id]["correct"] += 1

    # ── Build TopicAccuracy objects ──────────────────────────────────────────

    topics: list[TopicAccuracy] = []

    for tid, b in buckets.items():
        earned = b["earned"]
        max_possible = b["max"]
        pct: Optional[float] = (
            round((earned / max_possible) * 100.0, 2) if max_possible > 0 else None
        )
        is_weak = pct is not None and pct < _WEAK_THRESHOLD_PCT

        topics.append(
            TopicAccuracy(
                topic_id=tid,
                topic_label=_resolve_label(tid),
                earned=earned,
                max_possible=max_possible,
                pct=pct,
                answered_count=b["answered"],
                correct_count=b["correct"],
                is_weak=is_weak,
            )
        )

    topics.sort(key=_sort_key)

    return TopicAccuracyResult(
        topics=topics,
        has_any_data=True,
        computed_at=computed_at,
    )
