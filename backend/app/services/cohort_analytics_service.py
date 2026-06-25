"""
Cohort Analytics Service — Sprint 14B S14B-3
=============================================
Builds a student × topic mastery matrix for the instructor's cohort.

Each cell is the current BKT posterior P(L_n) from mastery_states, rounded
to two decimal places.  Missing cells (student has not attempted that topic)
are represented as None so the frontend can distinguish "untried" from 0.0.

Usage
-----
from app.services.cohort_analytics_service import build_cohort_heatmap

result = build_cohort_heatmap(db=db_session)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.constants import TOPIC_LABELS
from app.services.bkt_service import _canonicalise_topic_id
from db.database import MasteryState, User, UserRole

MASTERY_THRESHOLD = 0.70


def build_cohort_heatmap(db: Session) -> dict:
    """
    Return the full cohort mastery matrix.

    Returns
    -------
    {
      "students": [
        {
          "user_id": str,
          "display_name": str,
          "mastery": {topic_id: float | None, ...},
          "avg_mastery": float | None,
          "mastered_count": int
        },
        ...
      ],
      "topics": [
        {"topic_id": str, "label": str, "cohort_avg": float | None},
        ...
      ],
      "n_students": int,
      "n_topics": int,
      "computed_at": str
    }
    """
    students = (
        db.query(User)
        .filter(User.role == UserRole.STUDENT, User.is_archived.is_(False))
        .order_by(User.display_name)
        .all()
    )
    student_ids = [s.user_id for s in students]

    mastery_rows = (
        db.query(MasteryState)
        .filter(MasteryState.user_id.in_(student_ids) if student_ids else False)
        .all()
    ) if student_ids else []

    # Build nested dict: user_id → topic_id → mastery_prob
    matrix: dict[str, dict[str, float]] = {sid: {} for sid in student_ids}
    all_topics: set[str] = set()
    for row in mastery_rows:
        tid = _canonicalise_topic_id(row.topic_id)
        matrix[row.user_id][tid] = round(row.mastery_prob, 4)
        all_topics.add(tid)

    sorted_topics = sorted(all_topics)

    # Per-topic cohort averages
    topic_avgs: list[dict] = []
    for tid in sorted_topics:
        vals = [matrix[sid][tid] for sid in student_ids if tid in matrix[sid]]
        cohort_avg = round(sum(vals) / len(vals), 4) if vals else None
        topic_avgs.append({
            "topic_id": tid,
            "label": TOPIC_LABELS.get(tid, tid),
            "cohort_avg": cohort_avg,
        })

    # Per-student rows
    student_rows: list[dict] = []
    for student in students:
        sid = student.user_id
        mastery_map = {tid: matrix[sid].get(tid) for tid in sorted_topics}
        vals = [v for v in mastery_map.values() if v is not None]
        avg = round(sum(vals) / len(vals), 4) if vals else None
        mastered = sum(1 for v in vals if v >= MASTERY_THRESHOLD)
        student_rows.append({
            "user_id": sid,
            "display_name": student.display_name,
            "mastery": mastery_map,
            "avg_mastery": avg,
            "mastered_count": mastered,
        })

    return {
        "students": student_rows,
        "topics": topic_avgs,
        "n_students": len(students),
        "n_topics": len(sorted_topics),
        "mastery_threshold": MASTERY_THRESHOLD,
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }
