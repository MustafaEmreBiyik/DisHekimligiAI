"""Instructor portal backend endpoints (Sprint 5)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from db.database import (
    CaseDefinition,
    ChatLog,
    CoachHint,
    RecommendationSnapshot,
    StudentSession,
    User,
    UserRole,
    ValidatorAuditLog,
)


router = APIRouter()

SCORING_RULES_PATH = Path(__file__).resolve().parents[3] / "data" / "scoring_rules.json"
CASE_SCENARIOS_PATH = Path(__file__).resolve().parents[3] / "data" / "case_scenarios.json"
SPOTLIGHT_ALGORITHM_VERSION = "v1_instructor_spotlight"
SPOTLIGHT_PRIORITY_SCORE = 1000


class SpotlightRequest(BaseModel):
    case_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


def _safe_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _risk_level(avg_score: float) -> str:
    if avg_score < 50:
        return "high"
    if avg_score <= 70:
        return "medium"
    return "low"


def _load_scoring_rules_index() -> dict[str, list[str]]:
    with open(SCORING_RULES_PATH, "r", encoding="utf-8") as file:
        payload = json.load(file)

    index: dict[str, list[str]] = {}
    for case_rule_set in payload:
        case_id = str(case_rule_set.get("case_id", "")).strip()
        if not case_id:
            continue

        for rule in case_rule_set.get("rules", []):
            action = str(rule.get("target_action", "")).strip()
            if not action:
                continue

            key = f"{case_id}:{action}"
            index[key] = [
                str(tag).strip()
                for tag in rule.get("competency_tags", [])
                if isinstance(tag, str) and tag.strip()
            ]
    return index


def _is_finished_session(session: StudentSession) -> bool:
    try:
        state = json.loads(session.state_json) if session.state_json else {}
    except json.JSONDecodeError:
        state = {}

    if not isinstance(state, dict):
        return False
    return bool(state.get("is_finished") or state.get("is_case_finished"))


def _resolve_case_titles(db: Session) -> dict[str, str]:
    rows = (
        db.query(CaseDefinition)
        .filter(CaseDefinition.is_archived.is_(False), CaseDefinition.is_active.is_(True))
        .all()
    )
    if rows:
        return {row.case_id: row.title for row in rows}

    with open(CASE_SCENARIOS_PATH, "r", encoding="utf-8") as file:
        payload = json.load(file)

    case_titles: dict[str, str] = {}
    for case in payload:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id", "")).strip()
        title = str(case.get("title", "")).strip()
        is_active = bool(case.get("is_active", False))
        if case_id and title and is_active:
            case_titles[case_id] = title
    return case_titles


def _find_weak_competencies_by_student(
    *,
    sessions: list[StudentSession],
    assistant_logs: list[ChatLog],
    rules_index: dict[str, list[str]],
) -> tuple[dict[str, list[str]], dict[str, dict[str, dict[str, Any]]]]:
    sessions_by_id = {s.id: s for s in sessions}
    tag_scores: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    for log in assistant_logs:
        session = sessions_by_id.get(log.session_id)
        if session is None:
            continue

        metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
        interpreted_action = str(metadata.get("interpreted_action", "")).strip()
        if not interpreted_action:
            continue

        tags = rules_index.get(f"{session.case_id}:{interpreted_action}", [])
        if not tags:
            continue

        score = _safe_float(metadata.get("score", 0.0))
        student_bucket = tag_scores.setdefault(session.student_id, {})
        for tag in tags:
            if tag not in student_bucket:
                student_bucket[tag] = {"sum": 0.0, "count": 0.0, "students": {session.student_id}}
            student_bucket[tag]["sum"] += score
            student_bucket[tag]["count"] += 1.0
            student_bucket[tag]["students"].add(session.student_id)

    weak_tags: dict[str, list[str]] = {}
    for student_id, values in tag_scores.items():
        weak: list[str] = []
        for tag, metrics in values.items():
            count = float(metrics["count"])
            avg_score = float(metrics["sum"]) / count if count > 0 else 0.0
            if avg_score < 70.0:
                weak.append(tag)
        weak_tags[student_id] = sorted(weak)

    return weak_tags, tag_scores


def _require_active_student(db: Session, student_id: str) -> User:
    student = (
        db.query(User)
        .filter(
            User.user_id == student_id,
            User.role == UserRole.STUDENT,
            User.is_archived.is_(False),
        )
        .first()
    )
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )
    return student


@router.get("/overview")
def get_instructor_overview(
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    # v1 decision: instructor_student_assignments is not available yet,
    # so instructor/admin can see all active student-role users.
    students = (
        db.query(User)
        .filter(User.role == UserRole.STUDENT, User.is_archived.is_(False))
        .order_by(User.created_at.asc())
        .all()
    )
    student_ids = [student.user_id for student in students]

    sessions = (
        db.query(StudentSession)
        .filter(StudentSession.student_id.in_(student_ids))
        .order_by(StudentSession.start_time.desc())
        .all()
        if student_ids
        else []
    )
    session_ids = [session.id for session in sessions]

    session_map: dict[str, list[StudentSession]] = defaultdict(list)
    for row in sessions:
        session_map[row.student_id].append(row)

    assistant_logs = (
        db.query(ChatLog)
        .filter(ChatLog.session_id.in_(session_ids), ChatLog.role == "assistant")
        .all()
        if session_ids
        else []
    )
    rules_index = _load_scoring_rules_index()
    weak_by_student, tag_scores = _find_weak_competencies_by_student(
        sessions=sessions,
        assistant_logs=assistant_logs,
        rules_index=rules_index,
    )

    assigned_students: list[dict[str, Any]] = []
    for student in students:
        rows = session_map.get(student.user_id, [])
        total_sessions = len(rows)
        avg_score = round(sum(_safe_float(item.current_score) for item in rows) / total_sessions, 2) if total_sessions else 0.0
        last_active = max((item.start_time for item in rows if item.start_time), default=None)

        assigned_students.append(
            {
                "user_id": student.user_id,
                "display_name": student.display_name,
                "total_sessions": total_sessions,
                "avg_score": avg_score,
                "last_active": _safe_iso(last_active),
                "risk_level": _risk_level(avg_score),
                "weak_competencies": weak_by_student.get(student.user_id, []),
            }
        )

    safety_flags = []
    if session_ids:
        audit_rows = (
            db.query(ValidatorAuditLog, StudentSession, User)
            .join(StudentSession, StudentSession.id == ValidatorAuditLog.session_id)
            .join(User, User.user_id == StudentSession.student_id)
            .filter(
                ValidatorAuditLog.safety_violation.is_(True),
                StudentSession.id.in_(session_ids),
                User.is_archived.is_(False),
            )
            .order_by(ValidatorAuditLog.created_at.desc())
            .all()
        )

        for audit, session, student in audit_rows:
            safety_flags.append(
                {
                    "user_id": student.user_id,
                    "display_name": student.display_name,
                    "session_id": str(session.id),
                    "case_id": session.case_id,
                    "flag_type": "critical_safety_violation",
                    "created_at": _safe_iso(audit.created_at),
                }
            )

    competency_summary: dict[str, dict[str, Any]] = {}
    aggregate_sum: dict[str, float] = defaultdict(float)
    aggregate_count: dict[str, int] = defaultdict(int)
    aggregate_students: dict[str, set[str]] = defaultdict(set)

    for student_metrics in tag_scores.values():
        for tag, metrics in student_metrics.items():
            aggregate_sum[tag] += float(metrics["sum"])
            aggregate_count[tag] += int(metrics["count"])
            aggregate_students[tag].update(metrics["students"])

    for tag in sorted(aggregate_sum.keys()):
        count = aggregate_count[tag]
        avg_score = aggregate_sum[tag] / count if count > 0 else 0.0
        competency_summary[tag] = {
            "avg_score": round(avg_score, 2),
            "student_count": len(aggregate_students[tag]),
        }

    return {
        "assigned_students": assigned_students,
        "safety_flags": safety_flags,
        "competency_summary": competency_summary,
    }


@router.get("/students/{student_id}")
def get_student_drilldown(
    student_id: str,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    _ = current_user
    student = _require_active_student(db, student_id)

    sessions = (
        db.query(StudentSession)
        .filter(StudentSession.student_id == student_id)
        .order_by(StudentSession.start_time.desc(), StudentSession.id.desc())
        .all()
    )
    session_ids = [session.id for session in sessions]
    case_titles = _resolve_case_titles(db)

    rules_index = _load_scoring_rules_index()
    assistant_logs = (
        db.query(ChatLog)
        .filter(ChatLog.session_id.in_(session_ids), ChatLog.role == "assistant")
        .all()
        if session_ids
        else []
    )
    weak_by_student, _ = _find_weak_competencies_by_student(
        sessions=sessions,
        assistant_logs=assistant_logs,
        rules_index=rules_index,
    )

    total_sessions = len(sessions)
    avg_score = round(sum(_safe_float(item.current_score) for item in sessions) / total_sessions, 2) if total_sessions else 0.0

    safety_by_session: dict[int, list[str]] = defaultdict(list)
    if session_ids:
        rows = (
            db.query(ValidatorAuditLog)
            .filter(
                ValidatorAuditLog.session_id.in_(session_ids),
                ValidatorAuditLog.safety_violation.is_(True),
            )
            .order_by(ValidatorAuditLog.created_at.desc())
            .all()
        )
        for audit in rows:
            safety_by_session[audit.session_id].append("critical_safety_violation")

    hint_counts: dict[int, int] = defaultdict(int)
    if session_ids:
        hint_rows = (
            db.query(CoachHint)
            .filter(CoachHint.session_id.in_(session_ids))
            .all()
        )
        for hint in hint_rows:
            hint_counts[hint.session_id] += 1

    recommendation_history = (
        db.query(RecommendationSnapshot)
        .filter(RecommendationSnapshot.user_id == student_id)
        .order_by(RecommendationSnapshot.created_at.desc(), RecommendationSnapshot.id.desc())
        .all()
    )

    return {
        "student": {
            "user_id": student.user_id,
            "display_name": student.display_name,
            "avg_score": avg_score,
            "weak_competencies": weak_by_student.get(student.user_id, []),
            "risk_level": _risk_level(avg_score),
        },
        "sessions": [
            {
                "session_id": str(item.id),
                "case_id": item.case_id,
                "case_title": case_titles.get(item.case_id, item.case_id),
                "score": round(_safe_float(item.current_score), 2),
                "is_finished": _is_finished_session(item),
                "created_at": _safe_iso(item.start_time),
                "safety_flags": safety_by_session.get(item.id, []),
                "hint_count": hint_counts.get(item.id, 0),
            }
            for item in sessions
        ],
        "recommendation_history": [
            {
                "case_id": rec.case_id,
                "reason_code": rec.reason_code,
                "reason_text": rec.reason_text,
                "created_at": _safe_iso(rec.created_at),
                "is_spotlight": bool(rec.is_spotlight),
            }
            for rec in recommendation_history
        ],
    }


@router.get("/sessions/{session_id}")
def get_session_detail(
    session_id: int,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    _ = current_user
    session = db.query(StudentSession).filter(StudentSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    _require_active_student(db, session.student_id)

    logs = (
        db.query(ChatLog)
        .filter(ChatLog.session_id == session_id, ChatLog.role.in_(["user", "assistant"]))
        .order_by(ChatLog.timestamp.asc(), ChatLog.id.asc())
        .all()
    )

    actions = []
    validator_notes = []
    last_student_message = ""
    for row in logs:
        if row.role == "user":
            last_student_message = row.content
            continue

        metadata = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        assessment = metadata.get("assessment", {}) if isinstance(metadata.get("assessment"), dict) else {}
        silent_eval = metadata.get("silent_evaluation", {}) if isinstance(metadata.get("silent_evaluation"), dict) else {}

        actions.append(
            {
                "message_id": str(row.id),
                "student_message": last_student_message,
                "interpreted_action": str(metadata.get("interpreted_action", "unknown") or "unknown"),
                "score_delta": _safe_float(metadata.get("score", 0.0)),
                "is_critical_safety_rule": bool(assessment.get("is_critical_safety_rule", False)),
                "safety_category": assessment.get("safety_category"),
                "timestamp": _safe_iso(row.timestamp),
            }
        )

        validator_notes.append(
            {
                "safety_violation": bool(silent_eval.get("safety_violation", False)),
                "missing_critical_steps": silent_eval.get("missing_critical_steps", [])
                if isinstance(silent_eval.get("missing_critical_steps", []), list)
                else [],
                "clinical_accuracy": silent_eval.get("clinical_accuracy"),
                "faculty_notes": silent_eval.get("faculty_notes"),
                "created_at": _safe_iso(row.timestamp),
            }
        )

    coach_hints = (
        db.query(CoachHint)
        .filter(CoachHint.session_id == session_id)
        .order_by(CoachHint.created_at.asc(), CoachHint.id.asc())
        .all()
    )

    return {
        "session_id": str(session.id),
        "student_id": session.student_id,
        "case_id": session.case_id,
        "score": round(_safe_float(session.current_score), 2),
        "is_finished": _is_finished_session(session),
        "actions": actions,
        "validator_notes": validator_notes,
        "coach_hints": [
            {
                "hint_level": row.hint_level,
                "content": row.content,
                "created_at": _safe_iso(row.created_at),
            }
            for row in coach_hints
        ],
    }


@router.post("/students/{student_id}/spotlight")
def create_recommendation_spotlight(
    student_id: str,
    payload: SpotlightRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    _ = current_user
    _require_active_student(db, student_id)

    case = (
        db.query(CaseDefinition)
        .filter(
            CaseDefinition.case_id == payload.case_id,
            CaseDefinition.is_archived.is_(False),
            CaseDefinition.is_active.is_(True),
        )
        .first()
    )
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found",
        )

    spotlight = RecommendationSnapshot(
        user_id=student_id,
        case_id=payload.case_id,
        reason_code="instructor_spotlight",
        reason_text=payload.reason,
        priority_score=SPOTLIGHT_PRIORITY_SCORE,
        algorithm_version=SPOTLIGHT_ALGORITHM_VERSION,
        is_spotlight=True,
    )
    db.add(spotlight)
    db.commit()
    db.refresh(spotlight)

    return {
        "success": True,
        "spotlight_id": str(spotlight.id),
        "message": "Vaka öneri listesine eklendi.",
    }
