"""SM-2 spaced repetition scheduler service (S10-C).

Implements the SuperMemo-2 algorithm for scheduling question reviews.
Rating scale: 0 (complete blackout) to 5 (perfect recall).

    0-2: Failed recall  → reset to day 1
    3:   Hard but pass  → advance with reduced ease
    4:   Correct        → normal advance
    5:   Easy           → normal advance + ease bonus
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

_MIN_EASE = 1.3
_EASE_BONUS = 0.1
_EASE_PENALTY = 0.2


@dataclass
class SM2State:
    repetitions: int
    interval_days: int
    ease_factor: float
    due_date: datetime.datetime


def next_review_state(
    *,
    repetitions: int,
    interval_days: int,
    ease_factor: float,
    rating: int,
    reviewed_at: Optional[datetime.datetime] = None,
) -> SM2State:
    """Compute the next SM-2 state given a review outcome.

    Args:
        repetitions: Number of successful consecutive reviews so far.
        interval_days: Current interval in days.
        ease_factor: Current ease factor (EF ≥ 1.3).
        rating: Student self-assessment 0–5.
        reviewed_at: Timestamp of the review (defaults to utcnow).

    Returns:
        Updated SM2State with new interval, ease factor, repetitions and due date.
    """
    if rating < 0 or rating > 5:
        raise ValueError(f"Rating must be 0–5, got {rating}")

    now = reviewed_at or datetime.datetime.utcnow()

    if rating < 3:
        # Failed recall: restart from day 1
        new_repetitions = 0
        new_interval = 1
        new_ease = max(_MIN_EASE, ease_factor - _EASE_PENALTY)
    else:
        # Passed: apply SM-2 spacing
        new_repetitions = repetitions + 1
        if new_repetitions == 1:
            new_interval = 1
        elif new_repetitions == 2:
            new_interval = 6
        else:
            new_interval = round(interval_days * ease_factor)

        # Adjust ease factor based on rating
        delta_ease = _EASE_BONUS * (rating - 3)
        new_ease = max(_MIN_EASE, ease_factor + delta_ease)

    new_due = now + datetime.timedelta(days=new_interval)
    return SM2State(
        repetitions=new_repetitions,
        interval_days=new_interval,
        ease_factor=round(new_ease, 4),
        due_date=new_due,
    )
