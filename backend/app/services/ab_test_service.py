"""T06: A/B test framework for recommendation strategy comparison.

Experiments are defined in ACTIVE_EXPERIMENTS (code config, not DB).
Group assignment is deterministic: SHA-256(experiment_id:user_id) % n_groups.
Assignments are persisted in experiment_assignments on first call.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import (
    ExamResult,
    ExperimentAssignment,
    MasteryState,
    QuizAttempt,
    StudentSession,
    User,
)

# ── Experiment registry (code-config, no DB table needed) ────────────────────

ACTIVE_EXPERIMENTS: Dict[str, Dict[str, Any]] = {
    "recsys_ab_2026": {
        "name": "Öneri Stratejisi A/B Testi 2026",
        "description": (
            "Kontrol grubu (kural tabanlı, kişiselleştirme yok) ile "
            "tedavi grupları (BKT+IRT+SM-2 kişiselleştirmesi) karşılaştırması. "
            "treatment_persona grubu ileride persona-aware geliştirmeler için ayrılmıştır."
        ),
        "groups": ["control", "treatment_v2", "treatment_persona"],
        "is_active": True,
        "started_at": "2026-06-06",
    }
}


def _deterministic_group(user_id: str, experiment_id: str, groups: List[str]) -> str:
    """Hash user_id + experiment_id to deterministically pick a group.

    Same user always lands in the same group for a given experiment,
    regardless of when or how many times this is called.
    """
    key = f"{experiment_id}:{user_id}"
    digest = int(hashlib.sha256(key.encode()).hexdigest(), 16)
    return groups[digest % len(groups)]


def get_or_assign(user_id: str, experiment_id: str, db: Session) -> str:
    """Return user's group for experiment_id; create assignment if missing."""
    experiment = ACTIVE_EXPERIMENTS.get(experiment_id)
    if not experiment:
        raise ValueError(f"Unknown experiment: {experiment_id}")

    existing = (
        db.query(ExperimentAssignment)
        .filter_by(user_id=user_id, experiment_id=experiment_id)
        .first()
    )
    if existing:
        return existing.group_name

    group_name = _deterministic_group(user_id, experiment_id, experiment["groups"])
    assignment = ExperimentAssignment(
        user_id=user_id,
        experiment_id=experiment_id,
        group_name=group_name,
        assigned_at=datetime.utcnow(),
    )
    db.add(assignment)

    # Sync shortcut field on User for easy reporting
    user_row = db.query(User).filter(User.user_id == user_id).first()
    if user_row and not user_row.experiment_group:
        user_row.experiment_group = group_name

    db.commit()
    return group_name


def list_experiments() -> List[Dict[str, Any]]:
    """Return all registered experiments (no DB needed)."""
    return [
        {"experiment_id": eid, **cfg}
        for eid, cfg in ACTIVE_EXPERIMENTS.items()
    ]


def get_experiment_summary(experiment_id: str, db: Session) -> Dict[str, Any]:
    """Return experiment metadata + current group distribution from DB."""
    experiment = ACTIVE_EXPERIMENTS.get(experiment_id)
    if not experiment:
        raise ValueError(f"Unknown experiment: {experiment_id}")

    rows = (
        db.query(ExperimentAssignment.group_name, func.count(ExperimentAssignment.id))
        .filter(ExperimentAssignment.experiment_id == experiment_id)
        .group_by(ExperimentAssignment.group_name)
        .all()
    )
    distribution: Dict[str, int] = {g: 0 for g in experiment["groups"]}
    for group_name, count in rows:
        distribution[group_name] = count

    return {
        "experiment_id": experiment_id,
        "name": experiment["name"],
        "description": experiment["description"],
        "is_active": experiment["is_active"],
        "started_at": experiment["started_at"],
        "groups": experiment["groups"],
        "group_distribution": distribution,
        "total_assigned": sum(distribution.values()),
    }


def get_experiment_results(experiment_id: str, db: Session) -> Dict[str, Any]:
    """Compute per-group learning metrics for a given experiment.

    Metrics per group:
      - user_count
      - avg_exam_score_pct  (ExamResult: score/max_score * 100)
      - total_sessions      (StudentSession count)
      - quiz_attempts       (QuizAttempt count)
      - avg_mastery         (mean of MasteryState.mastery_prob)
    """
    experiment = ACTIVE_EXPERIMENTS.get(experiment_id)
    if not experiment:
        raise ValueError(f"Unknown experiment: {experiment_id}")

    assignments = (
        db.query(ExperimentAssignment)
        .filter(ExperimentAssignment.experiment_id == experiment_id)
        .all()
    )

    group_to_users: Dict[str, List[str]] = {g: [] for g in experiment["groups"]}
    for a in assignments:
        if a.group_name in group_to_users:
            group_to_users[a.group_name].append(a.user_id)

    group_results: Dict[str, Any] = {}
    for group_name, user_ids in group_to_users.items():
        if not user_ids:
            group_results[group_name] = {
                "user_count": 0,
                "avg_exam_score_pct": None,
                "total_sessions": 0,
                "quiz_attempts": 0,
                "avg_mastery": None,
            }
            continue

        # Avg exam score
        exam_rows = (
            db.query(ExamResult.score, ExamResult.max_score)
            .filter(ExamResult.user_id.in_(user_ids))
            .all()
        )
        if exam_rows:
            total_score = sum(r.score for r in exam_rows)
            total_max = sum(r.max_score for r in exam_rows)
            avg_exam_pct: Optional[float] = (
                round(total_score / total_max * 100, 1) if total_max > 0 else None
            )
        else:
            avg_exam_pct = None

        # Total clinical sessions
        session_count: int = (
            db.query(func.count(StudentSession.id))
            .filter(StudentSession.student_id.in_(user_ids))
            .scalar()
        ) or 0

        # Quiz attempts
        attempt_count: int = (
            db.query(func.count(QuizAttempt.id))
            .filter(QuizAttempt.user_id.in_(user_ids))
            .scalar()
        ) or 0

        # Average BKT mastery
        mastery_rows = (
            db.query(MasteryState.mastery_prob)
            .filter(MasteryState.user_id.in_(user_ids))
            .all()
        )
        avg_mastery: Optional[float] = (
            round(sum(r.mastery_prob for r in mastery_rows) / len(mastery_rows), 3)
            if mastery_rows
            else None
        )

        group_results[group_name] = {
            "user_count": len(user_ids),
            "avg_exam_score_pct": avg_exam_pct,
            "total_sessions": session_count,
            "quiz_attempts": attempt_count,
            "avg_mastery": avg_mastery,
        }

    return {
        "experiment_id": experiment_id,
        "experiment_name": experiment["name"],
        "group_results": group_results,
    }
