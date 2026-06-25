"""
Mastery Trajectory Service — Sprint 14B S14B-1
===============================================
Reconstructs the BKT posterior P(L_n) time series for each (user, topic) pair
by replaying graded QuizAnswer observations in chronological order.

Confidence intervals are computed per observation using the Wilson-score
approximation:

    CI_half = 1.96 × √( p × (1−p) / max(1, n) )
    lower   = max(0,  p − CI_half)
    upper   = min(1,  p + CI_half)

This is interpretable as the uncertainty band around the BKT point estimate
after n observations and is appropriate for publication in JDE / Wiley venues.

Usage
-----
from app.services.mastery_trajectory_service import build_trajectory

result = build_trajectory(user_id="stu_001", db=db_session)
# result = {"user_id": ..., "topics": [...], "computed_at": "..."}
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.constants import BKT_P_GUESS, BKT_P_INIT, BKT_P_SLIP, BKT_P_TRANSIT, TOPIC_LABELS
from app.services.bkt_service import _bkt_update, _canonicalise_topic_id
from db.database import GradingStatus, MasteryState, Question, QuizAnswer, QuizAttempt

_Z95 = 1.96  # z-score for 95% CI


def _ci(mastery: float, n: int) -> tuple[float, float]:
    """Wilson-score CI half-width around BKT point estimate."""
    if n < 1:
        return 0.0, 1.0
    half = _Z95 * math.sqrt(mastery * (1.0 - mastery) / n)
    return max(0.0, mastery - half), min(1.0, mastery + half)


def build_trajectory(
    user_id: str,
    db: Session,
    topic_id: Optional[str] = None,
) -> dict:
    """
    Replay all graded observations for *user_id* and return per-topic
    mastery trajectories with 95% CI bands.

    Parameters
    ----------
    user_id  : str
    db       : Session
    topic_id : str | None
        If provided, only return trajectory for that topic.

    Returns
    -------
    {
      "user_id": str,
      "topics": [
        {
          "topic_id": str,
          "label": str,
          "current_mastery": float,
          "n_observations": int,
          "points": [
            {
              "n": int,
              "mastery": float,   # P(L_n)
              "ci_lower": float,
              "ci_upper": float,
              "correct": bool,
              "timestamp": str | None
            },
            ...
          ]
        },
        ...
      ],
      "computed_at": str
    }
    """
    filter_tid = _canonicalise_topic_id(topic_id) if topic_id else None

    # Fetch graded answers in chronological order (by answer id as proxy)
    rows = (
        db.query(QuizAnswer, Question, QuizAttempt)
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .join(Question, QuizAnswer.question_id == Question.id)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAnswer.grading_status.in_([GradingStatus.GRADED, GradingStatus.PUBLISHED]),
            Question.topic_id.isnot(None),
        )
        .order_by(QuizAnswer.id)
        .all()
    )

    # Fetch stored MasteryState rows so we use the same per-topic BKT priors
    state_map: dict[str, MasteryState] = {
        _canonicalise_topic_id(s.topic_id): s
        for s in db.query(MasteryState).filter(MasteryState.user_id == user_id).all()
    }

    trajectories: dict[str, dict] = {}

    for answer, question, attempt in rows:
        tid = _canonicalise_topic_id(question.topic_id)
        if filter_tid and tid != filter_tid:
            continue

        if tid not in trajectories:
            state = state_map.get(tid)
            trajectories[tid] = {
                "topic_id": tid,
                "label": TOPIC_LABELS.get(tid, tid),
                "p_slip": state.p_slip if state else BKT_P_SLIP,
                "p_guess": state.p_guess if state else BKT_P_GUESS,
                "p_transit": state.p_transit if state else BKT_P_TRANSIT,
                "points": [],
                "_current": BKT_P_INIT,
                "_n": 0,
            }

        traj = trajectories[tid]

        score = answer.instructor_score if answer.instructor_score is not None else answer.auto_score
        if score is None:
            continue

        was_correct = score >= (question.max_score * 0.5)
        new_mastery = _bkt_update(
            current_mastery=traj["_current"],
            was_correct=was_correct,
            p_slip=traj["p_slip"],
            p_guess=traj["p_guess"],
            p_transit=traj["p_transit"],
        )
        traj["_n"] += 1
        traj["_current"] = new_mastery

        lo, hi = _ci(new_mastery, traj["_n"])

        ts = answer.graded_at or attempt.completed_at or attempt.created_at
        traj["points"].append({
            "n": traj["_n"],
            "mastery": round(new_mastery, 4),
            "ci_lower": round(lo, 4),
            "ci_upper": round(hi, 4),
            "correct": was_correct,
            "timestamp": ts.isoformat() if ts else None,
        })

    result_topics = sorted(
        [
            {
                "topic_id": traj["topic_id"],
                "label": traj["label"],
                "current_mastery": round(traj["_current"], 4),
                "n_observations": traj["_n"],
                "points": traj["points"],
            }
            for traj in trajectories.values()
        ],
        key=lambda t: t["topic_id"],
    )

    return {
        "user_id": user_id,
        "topics": result_topics,
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }
