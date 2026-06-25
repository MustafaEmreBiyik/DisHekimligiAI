"""T08 + S14B-5: KVKK-anonymised research dataset export service.

Anonymisation rules:
- user_id   → SHA-256(salt:user_id)[:16]  (stable across exports, not reversible)
- name, email, phone fields stripped
- timestamps preserved for time-series analysis

Tables exported (10 CSVs in a single ZIP):
  chat_logs, quiz_attempts, quiz_answers,
  recommendation_snapshots, mastery_states,
  irt_parameters, review_schedules,
  mastery_trajectories, learning_curve_fits,   ← S14B-5
  outcome_correlation                           ← S14B-5

The salt is read from env DENTAI_ANON_SALT; falls back to a static default so
that cross-export user correlation is reproducible on a single deployment without
requiring manual configuration.
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import zipfile
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from db.database import (
    ChatLog,
    ExamResult,
    GradingStatus,
    IRTParameters,
    MasteryState,
    Question,
    QuizAnswer,
    QuizAttempt,
    RecommendationSnapshot,
    ReviewSchedule,
    StudentSession,
    User,
    UserRole,
)

_SALT = os.getenv("DENTAI_ANON_SALT", "dentai-anon-v1")

TABLES = [
    "chat_logs",
    "quiz_attempts",
    "quiz_answers",
    "recommendation_snapshots",
    "mastery_states",
    "irt_parameters",
    "review_schedules",
    "mastery_trajectories",
    "learning_curve_fits",
    "outcome_correlation",
]


def _uid(user_id: str) -> str:
    """Deterministic, non-reversible hash of a user_id."""
    return hashlib.sha256(f"{_SALT}:{user_id}".encode()).hexdigest()[:16]


def _iso(v: Any) -> str:
    return v.isoformat() if v is not None else ""


def _csv_bytes(rows: List[Dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


def build_export_zip(db: Session) -> Tuple[bytes, int, List[str]]:
    """Generate a ZIP containing one CSV per table.

    Returns (zip_bytes, total_row_count, tables_included).
    """
    # Pre-build session → anon_user_id map for chat_logs
    sessions = db.query(StudentSession).all()
    session_user: Dict[int, str] = {s.id: s.student_id for s in sessions}

    # ── Collect rows ───────────────────────────────────────────────────────���──

    chat_log_rows: List[Dict[str, Any]] = []
    for cl in db.query(ChatLog).all():
        uid_raw = session_user.get(cl.session_id, "")
        chat_log_rows.append({
            "id": cl.id,
            "session_id": cl.session_id,
            "anon_user_id": _uid(uid_raw) if uid_raw else "",
            "role": cl.role,
            "content": cl.content,
            "timestamp": _iso(cl.timestamp),
        })

    quiz_attempt_rows: List[Dict[str, Any]] = []
    for qa in db.query(QuizAttempt).all():
        quiz_attempt_rows.append({
            "id": qa.id,
            "anon_user_id": _uid(qa.user_id),
            "total_score": qa.total_score,
            "max_score": qa.max_score,
            "created_at": _iso(qa.created_at),
            "completed_at": _iso(qa.completed_at),
        })

    quiz_answer_rows: List[Dict[str, Any]] = []
    for ans in db.query(QuizAnswer).all():
        quiz_answer_rows.append({
            "id": ans.id,
            "attempt_id": ans.attempt_id,
            "question_id": ans.question_id,
            "student_response_text": ans.student_response_text,
            "auto_score": ans.auto_score if ans.auto_score is not None else "",
            "instructor_score": ans.instructor_score if ans.instructor_score is not None else "",
            "grading_status": ans.grading_status.value if ans.grading_status else "",
            "ai_score_suggestion": ans.ai_score_suggestion if ans.ai_score_suggestion is not None else "",
        })

    rec_snap_rows: List[Dict[str, Any]] = []
    for rs in db.query(RecommendationSnapshot).all():
        rec_snap_rows.append({
            "id": rs.id,
            "anon_user_id": _uid(rs.user_id),
            "case_id": rs.case_id,
            "reason_code": rs.reason_code,
            "priority_score": rs.priority_score,
            "algorithm_version": rs.algorithm_version,
            "is_spotlight": rs.is_spotlight,
            "created_at": _iso(rs.created_at),
        })

    mastery_rows: List[Dict[str, Any]] = []
    for ms in db.query(MasteryState).all():
        mastery_rows.append({
            "id": ms.id,
            "anon_user_id": _uid(ms.user_id),
            "topic_id": ms.topic_id,
            "mastery_prob": ms.mastery_prob,
            "n_observations": ms.n_observations,
            "last_observation_at": _iso(ms.last_observation_at),
            "updated_at": _iso(ms.updated_at),
        })

    irt_rows: List[Dict[str, Any]] = []
    for irt in db.query(IRTParameters).all():
        irt_rows.append({
            "id": irt.id,
            "question_id": irt.question_id,
            "model": irt.model,
            "difficulty_b": irt.difficulty_b,
            "discrimination_a": irt.discrimination_a,
            "guessing_c": irt.guessing_c if irt.guessing_c is not None else "",
            "sample_size": irt.sample_size,
            "is_synthetic": irt.is_synthetic,
            "calibrated_at": _iso(irt.calibrated_at),
        })

    review_rows: List[Dict[str, Any]] = []
    for rv in db.query(ReviewSchedule).all():
        review_rows.append({
            "id": rv.id,
            "anon_user_id": _uid(rv.user_id),
            "question_id": rv.question_id,
            "repetitions": rv.repetitions,
            "interval_days": rv.interval_days,
            "ease_factor": rv.ease_factor,
            "due_date": _iso(rv.due_date),
            "last_reviewed_at": _iso(rv.last_reviewed_at),
            "created_at": _iso(rv.created_at),
        })

    # ── S14B-5: mastery trajectories per (user, topic) ────────────────────────
    from app.services.mastery_trajectory_service import build_trajectory

    students = (
        db.query(User)
        .filter(User.role == UserRole.STUDENT, User.is_archived.is_(False))
        .all()
    )

    trajectory_rows: List[Dict[str, Any]] = []
    lc_fit_rows: List[Dict[str, Any]] = []

    from app.services.learning_curve_service import build_learning_curves

    for student in students:
        anon = _uid(student.user_id)
        try:
            traj = build_trajectory(user_id=student.user_id, db=db)
            for topic in traj["topics"]:
                for pt in topic["points"]:
                    trajectory_rows.append({
                        "anon_user_id": anon,
                        "topic_id": topic["topic_id"],
                        "topic_label": topic["label"],
                        "n": pt["n"],
                        "mastery": pt["mastery"],
                        "ci_lower": pt["ci_lower"],
                        "ci_upper": pt["ci_upper"],
                        "correct": int(pt["correct"]),
                        "timestamp": pt["timestamp"] or "",
                    })
        except Exception:
            pass

        try:
            lc = build_learning_curves(user_id=student.user_id, db=db)
            for topic in lc["topics"]:
                fit = topic["fit"]
                params = fit.get("params", {})
                lc_fit_rows.append({
                    "anon_user_id": anon,
                    "topic_id": topic["topic_id"],
                    "topic_label": topic["label"],
                    "n_observations": topic["n_observations"],
                    "model": fit.get("model") or "",
                    "param_L": params.get("L", ""),
                    "param_2": params.get("p0", params.get("b", "")),
                    "param_3": params.get("k", params.get("c", "")),
                    "r_squared": fit.get("r_squared") if fit.get("r_squared") is not None else "",
                    "projected_trials_to_mastery": (
                        fit.get("projected_trials_to_mastery") or ""
                    ),
                })
        except Exception:
            pass

    # ── S14B-5: outcome correlation per student ────────────────────────────────
    outcome_rows: List[Dict[str, Any]] = []
    for student in students:
        anon = _uid(student.user_id)
        # Quiz pct
        quiz_rows = (
            db.query(QuizAnswer, Question)
            .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
            .join(Question, QuizAnswer.question_id == Question.id)
            .filter(
                QuizAttempt.user_id == student.user_id,
                QuizAnswer.grading_status.in_([GradingStatus.GRADED, GradingStatus.PUBLISHED]),
            )
            .all()
        )
        q_earned = sum(
            (a.instructor_score if a.instructor_score is not None else a.auto_score or 0)
            for a, _ in quiz_rows
        )
        q_max = sum(q.max_score for _, q in quiz_rows)
        quiz_pct = round(q_earned / q_max * 100, 2) if q_max > 0 else ""

        case_rows = (
            db.query(ExamResult)
            .filter(
                ExamResult.user_id == student.user_id,
                ExamResult.max_score > 0,
                ExamResult.case_id != "quiz_global",
            )
            .all()
        )
        c_earned = sum(r.score for r in case_rows)
        c_max = sum(r.max_score for r in case_rows)
        case_pct = round(c_earned / c_max * 100, 2) if c_max > 0 else ""

        outcome_rows.append({
            "anon_user_id": anon,
            "quiz_pct": quiz_pct,
            "case_pct": case_pct,
        })

    table_data = {
        "chat_logs": chat_log_rows,
        "quiz_attempts": quiz_attempt_rows,
        "quiz_answers": quiz_answer_rows,
        "recommendation_snapshots": rec_snap_rows,
        "mastery_states": mastery_rows,
        "irt_parameters": irt_rows,
        "review_schedules": review_rows,
        "mastery_trajectories": trajectory_rows,
        "learning_curve_fits": lc_fit_rows,
        "outcome_correlation": outcome_rows,
    }

    total_rows = sum(len(v) for v in table_data.values())

    # ── Build ZIP ─────────────────────────────────────────────────────────────
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, rows in table_data.items():
            zf.writestr(f"{name}.csv", _csv_bytes(rows))

    return zip_buf.getvalue(), total_rows, TABLES
