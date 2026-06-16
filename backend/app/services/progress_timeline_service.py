"""T07: Longitudinal student progress timeline service.

Computes a 12-week weekly breakdown of:
  - quiz_score_avg    : avg score % from QuizAttempt rows
  - quiz_attempts     : count of QuizAttempt rows
  - cases_completed   : count of ExamResult rows
  - recommendations_received: count of RecommendationSnapshot rows

Plus current mastery snapshot (MasteryState) and derived IRT theta.
No new DB tables required — reads from existing models.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.constants import TOPIC_LABELS
from db.database import ExamResult, MasteryState, QuizAttempt, RecommendationSnapshot

_MONTHS_TR = [
    "Oca", "Şub", "Mar", "Nis", "May", "Haz",
    "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara",
]


def _week_starts(n_weeks: int = 12) -> List[datetime.datetime]:
    """Return list of UTC Monday-midnight datetimes for the last n_weeks, oldest first."""
    today = datetime.datetime.utcnow().date()
    monday = today - datetime.timedelta(days=today.weekday())
    return [
        datetime.datetime.combine(monday - datetime.timedelta(weeks=i), datetime.time.min)
        for i in range(n_weeks - 1, -1, -1)
    ]


def _week_label(dt: datetime.datetime) -> str:
    return f"{dt.day} {_MONTHS_TR[dt.month - 1]}"


def _week_index(dt: datetime.datetime | None, starts: List[datetime.datetime]) -> int:
    if dt is None:
        return -1
    week = datetime.timedelta(weeks=1)
    for i, ws in enumerate(starts):
        if ws <= dt < ws + week:
            return i
    return -1


def build_timeline(user_id: str, db: Session, n_weeks: int = 12) -> Dict[str, Any]:
    """Return the full progress timeline payload for one student."""
    starts = _week_starts(n_weeks)
    window_start = starts[0]
    window_end = starts[-1] + datetime.timedelta(weeks=1)

    quiz_attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAttempt.created_at >= window_start,
            QuizAttempt.created_at < window_end,
        )
        .all()
    )

    exam_results = (
        db.query(ExamResult)
        .filter(
            ExamResult.user_id == user_id,
            ExamResult.completed_at >= window_start,
            ExamResult.completed_at < window_end,
        )
        .all()
    )

    rec_snapshots = (
        db.query(RecommendationSnapshot)
        .filter(
            RecommendationSnapshot.user_id == user_id,
            RecommendationSnapshot.created_at >= window_start,
            RecommendationSnapshot.created_at < window_end,
        )
        .all()
    )

    mastery_rows = (
        db.query(MasteryState)
        .filter(MasteryState.user_id == user_id)
        .all()
    )

    # Per-week accumulators
    wk_scores: Dict[int, List[float]] = {i: [] for i in range(n_weeks)}
    wk_attempts: Dict[int, int] = {i: 0 for i in range(n_weeks)}
    wk_cases: Dict[int, int] = {i: 0 for i in range(n_weeks)}
    wk_recs: Dict[int, int] = {i: 0 for i in range(n_weeks)}

    for qa in quiz_attempts:
        idx = _week_index(qa.created_at, starts)
        if idx < 0:
            continue
        wk_attempts[idx] += 1
        if qa.max_score and qa.max_score > 0:
            wk_scores[idx].append(qa.total_score / qa.max_score * 100)

    for er in exam_results:
        idx = _week_index(er.completed_at, starts)
        if idx >= 0:
            wk_cases[idx] += 1

    for rs in rec_snapshots:
        idx = _week_index(rs.created_at, starts)
        if idx >= 0:
            wk_recs[idx] += 1

    weeks: List[Dict[str, Any]] = []
    for i, ws in enumerate(starts):
        scores = wk_scores[i]
        weeks.append({
            "week_start": ws.date().isoformat(),
            "week_label": _week_label(ws),
            "quiz_score_avg": round(sum(scores) / len(scores), 1) if scores else None,
            "quiz_attempts": wk_attempts[i],
            "cases_completed": wk_cases[i],
            "recommendations_received": wk_recs[i],
        })

    # Current mastery snapshot
    mastery_by_topic: Dict[str, Dict[str, Any]] = {}
    total_mastery = 0.0
    for m in mastery_rows:
        label = TOPIC_LABELS.get(m.topic_id, m.topic_id)
        mastery_by_topic[m.topic_id] = {
            "label": label,
            "mastery_pct": round(m.mastery_prob * 100),
            "n_observations": m.n_observations,
            "last_observation_at": (
                m.last_observation_at.isoformat() if m.last_observation_at else None
            ),
        }
        total_mastery += m.mastery_prob

    avg_mastery = total_mastery / len(mastery_rows) if mastery_rows else 0.0
    irt_theta = round(4.0 * avg_mastery - 2.0, 3)

    all_scores = [s for bucket in wk_scores.values() for s in bucket]
    summary = {
        "total_quiz_attempts": sum(wk_attempts.values()),
        "total_cases_completed": sum(wk_cases.values()),
        "avg_quiz_score_pct": (
            round(sum(all_scores) / len(all_scores), 1) if all_scores else None
        ),
        "avg_mastery_pct": round(avg_mastery * 100),
        "irt_theta_current": irt_theta,
    }

    return {
        "user_id": user_id,
        "weeks": weeks,
        "mastery_by_topic": mastery_by_topic,
        "irt_theta_current": irt_theta,
        "summary": summary,
    }
