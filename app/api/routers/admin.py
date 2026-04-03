"""Admin portal backend endpoints (Sprint 6)."""

from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from db.database import (
    CaseDefinition,
    CasePublishHistory,
    ChatLog,
    RecommendationSnapshot,
    StudentSession,
    User,
    UserRole,
    ValidatorAuditLog,
)


router = APIRouter()

SCORING_RULES_PATH = Path(__file__).resolve().parents[3] / "data" / "scoring_rules.json"
INJECTION_PATTERNS = (
    "ignore previous",
    "system prompt",
    "jailbreak",
    "developer message",
    "act as",
)
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced"}


class AdminUserCreateRequest(BaseModel):
    display_name: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)
    role: UserRole


class AdminUserUpdateRequest(BaseModel):
    role: UserRole | None = None
    is_archived: bool | None = None


class AdminCaseCreateRequest(BaseModel):
    case_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    estimated_duration_minutes: int = Field(gt=0)
    is_active: bool = True
    schema_version: str = "2.0"
    learning_objectives: list[str] = Field(default_factory=list)
    prerequisite_competencies: list[str] = Field(default_factory=list)
    competency_tags: list[str] = Field(default_factory=list)
    initial_state: str = "consultation"
    states: dict[str, Any] = Field(default_factory=dict)
    patient_info: dict[str, Any] = Field(default_factory=dict)


class AdminCaseUpdateRequest(BaseModel):
    title: str | None = None
    category: str | None = None
    difficulty: str | None = None
    estimated_duration_minutes: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class PublishRequest(BaseModel):
    change_notes: str = Field(min_length=1)


class RulesUpdateRequest(BaseModel):
    rules: list[dict[str, Any]]


def _now() -> datetime.datetime:
    return datetime.datetime.utcnow()


def _safe_iso(value: datetime.datetime | None) -> str | None:
    return value.isoformat() if value else None


def _normalize_role(value: UserRole | str) -> str:
    if isinstance(value, UserRole):
        return value.value
    return str(value).strip().lower()


def _user_response(user: User) -> dict[str, Any]:
    return {
        "user_id": user.user_id,
        "display_name": user.display_name,
        "email": user.email,
        "role": _normalize_role(user.role),
        "is_archived": bool(user.is_archived),
        "created_at": _safe_iso(user.created_at),
    }


def _hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def _generate_user_id(db: Session) -> str:
    for _ in range(12):
        candidate = f"usr_{uuid4().hex[:10]}"
        exists = db.query(User.id).filter(User.user_id == candidate).first()
        if not exists:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate unique user_id",
    )


def _validate_difficulty(difficulty: str) -> str:
    normalized = str(difficulty).strip().lower()
    if normalized not in VALID_DIFFICULTIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="difficulty must be one of: beginner, intermediate, advanced",
        )
    return normalized


def _get_case_or_404(db: Session, case_id: str) -> CaseDefinition:
    case = (
        db.query(CaseDefinition)
        .filter(CaseDefinition.case_id == case_id, CaseDefinition.is_archived.is_(False))
        .first()
    )
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


def _latest_publish(db: Session, case_id: str) -> CasePublishHistory | None:
    return (
        db.query(CasePublishHistory)
        .filter(CasePublishHistory.case_id == case_id)
        .order_by(CasePublishHistory.version.desc(), CasePublishHistory.id.desc())
        .first()
    )


def _case_summary(db: Session, case: CaseDefinition) -> dict[str, Any]:
    latest = _latest_publish(db, case.case_id)
    return {
        "case_id": case.case_id,
        "title": case.title,
        "category": case.category,
        "difficulty": case.difficulty,
        "is_active": bool(case.is_active),
        "schema_version": case.schema_version,
        "published_version": int(latest.version) if latest else 0,
        "last_published_at": _safe_iso(latest.published_at) if latest else None,
    }


def _load_rules_payload() -> list[dict[str, Any]]:
    if not SCORING_RULES_PATH.exists():
        return []

    with open(SCORING_RULES_PATH, "r", encoding="utf-8") as file:
        payload = json.load(file)

    if not isinstance(payload, list):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid rules payload format",
        )
    return payload


def _write_rules_payload(payload: list[dict[str, Any]]) -> None:
    with open(SCORING_RULES_PATH, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def _validate_rule_items(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rules: list[dict[str, Any]] = []
    required = {
        "target_action",
        "score",
        "rule_outcome",
        "competency_tags",
        "is_critical_safety_rule",
    }

    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"rules[{index}] must be an object",
            )

        missing = sorted(required.difference(rule.keys()))
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"rules[{index}] missing fields: {', '.join(missing)}",
            )

        tags = rule.get("competency_tags")
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"rules[{index}].competency_tags must be a non-empty string list",
            )

        if not isinstance(rule.get("is_critical_safety_rule"), bool):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"rules[{index}].is_critical_safety_rule must be boolean",
            )

        normalized = dict(rule)
        if "safety_category" not in normalized:
            normalized["safety_category"] = None
        normalized_rules.append(normalized)

    return normalized_rules


def _service_status_from_key(env_key: str) -> str:
    value = os.getenv(env_key, "").strip()
    return "ok" if value else "unavailable"


@router.get("/users")
def list_admin_users(
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    _ = current_user
    rows = db.query(User).order_by(User.created_at.desc(), User.user_id.asc()).all()
    return {"users": [_user_response(row) for row in rows]}


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: AdminUserCreateRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    _ = current_user

    existing_email = db.query(User.id).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    user = User(
        user_id=_generate_user_id(db),
        display_name=payload.display_name.strip(),
        email=str(payload.email).strip().lower(),
        hashed_password=_hash_password(payload.password),
        role=payload.role,
        is_archived=False,
        archived_at=None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.put("/users/{user_id}")
def update_admin_user(
    user_id: str,
    payload: AdminUserUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    is_self = current_user.user_id == user.user_id

    if payload.role is not None and is_self and payload.role != user.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot change own role",
        )

    if payload.is_archived is True and is_self:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin cannot archive self",
        )

    if payload.role is not None:
        user.role = payload.role

    if payload.is_archived is not None:
        user.is_archived = payload.is_archived
        user.archived_at = _now() if payload.is_archived else None

    db.commit()
    db.refresh(user)
    return _user_response(user)


@router.get("/cases")
def list_admin_cases(
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    _ = current_user
    rows = (
        db.query(CaseDefinition)
        .filter(CaseDefinition.is_archived.is_(False))
        .order_by(CaseDefinition.created_at.desc(), CaseDefinition.case_id.asc())
        .all()
    )
    return {"cases": [_case_summary(db, row) for row in rows]}


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_admin_case(
    payload: AdminCaseCreateRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    _ = current_user
    case_id = payload.case_id.strip()
    existing = db.query(CaseDefinition.id).filter(CaseDefinition.case_id == case_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Case already exists")

    case = CaseDefinition(
        case_id=case_id,
        schema_version=str(payload.schema_version).strip() or "2.0",
        title=payload.title.strip(),
        category=payload.category.strip(),
        difficulty=_validate_difficulty(payload.difficulty),
        estimated_duration_minutes=payload.estimated_duration_minutes,
        is_active=payload.is_active,
        learning_objectives=payload.learning_objectives,
        prerequisite_competencies=payload.prerequisite_competencies,
        competency_tags=payload.competency_tags,
        initial_state=payload.initial_state,
        states_json=payload.states,
        patient_info_json=payload.patient_info,
        source_payload={
            "case_id": case_id,
            "schema_version": str(payload.schema_version).strip() or "2.0",
            "title": payload.title.strip(),
            "category": payload.category.strip(),
            "difficulty": _validate_difficulty(payload.difficulty),
            "estimated_duration_minutes": payload.estimated_duration_minutes,
            "is_active": payload.is_active,
            "learning_objectives": payload.learning_objectives,
            "prerequisite_competencies": payload.prerequisite_competencies,
            "competency_tags": payload.competency_tags,
            "initial_state": payload.initial_state,
            "states": payload.states,
            "patient_info": payload.patient_info,
        },
        is_archived=False,
        archived_at=None,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return _case_summary(db, case)


@router.put("/cases/{case_id}")
def update_admin_case(
    case_id: str,
    payload: AdminCaseUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    _ = current_user
    case = _get_case_or_404(db, case_id)

    if payload.title is not None:
        case.title = payload.title.strip()
    if payload.category is not None:
        case.category = payload.category.strip()
    if payload.difficulty is not None:
        case.difficulty = _validate_difficulty(payload.difficulty)
    if payload.estimated_duration_minutes is not None:
        case.estimated_duration_minutes = payload.estimated_duration_minutes
    if payload.is_active is not None:
        case.is_active = payload.is_active

    db.commit()
    db.refresh(case)
    return _case_summary(db, case)


@router.post("/cases/{case_id}/publish")
def publish_admin_case(
    case_id: str,
    payload: PublishRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    case = _get_case_or_404(db, case_id)
    latest = _latest_publish(db, case.case_id)
    next_version = int(latest.version) + 1 if latest else 1

    snapshot = {
        "case_id": case.case_id,
        "schema_version": case.schema_version,
        "title": case.title,
        "category": case.category,
        "difficulty": case.difficulty,
        "estimated_duration_minutes": case.estimated_duration_minutes,
        "is_active": case.is_active,
        "learning_objectives": case.learning_objectives,
        "prerequisite_competencies": case.prerequisite_competencies,
        "competency_tags": case.competency_tags,
        "initial_state": case.initial_state,
        "states": case.states_json,
        "patient_info": case.patient_info_json,
        "source_payload": case.source_payload,
    }

    history = CasePublishHistory(
        case_id=case.case_id,
        version=next_version,
        change_notes=payload.change_notes,
        published_by=current_user.user_id,
        published_at=_now(),
        snapshot_json=snapshot,
    )
    db.add(history)
    db.commit()
    db.refresh(history)

    return {
        "case_id": history.case_id,
        "published_version": history.version,
        "published_at": _safe_iso(history.published_at),
        "change_notes": history.change_notes,
    }


@router.get("/rules")
def list_admin_rules(
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    return _load_rules_payload()


@router.put("/rules/{case_id}")
def update_admin_rules(
    case_id: str,
    payload: RulesUpdateRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
):
    _ = current_user
    normalized_rules = _validate_rule_items(payload.rules)
    rules_payload = _load_rules_payload()

    replaced = False
    normalized_case_id = case_id.strip()
    for index, item in enumerate(rules_payload):
        if isinstance(item, dict) and str(item.get("case_id", "")).strip() == normalized_case_id:
            rules_payload[index] = {
                "case_id": normalized_case_id,
                "schema_version": "2.0",
                "rules": normalized_rules,
            }
            replaced = True
            break

    if not replaced:
        rules_payload.append(
            {
                "case_id": normalized_case_id,
                "schema_version": "2.0",
                "rules": normalized_rules,
            }
        )

    _write_rules_payload(rules_payload)
    return {
        "case_id": normalized_case_id,
        "schema_version": "2.0",
        "rules": normalized_rules,
    }


@router.get("/health")
def get_admin_health(
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    _ = current_user

    db_service_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_service_status = "unavailable"

    gemini_status = _service_status_from_key("GEMINI_API_KEY")
    medgemma_status = _service_status_from_key("HUGGINGFACE_API_KEY")

    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = db.query(User).count()
    active_sessions_today = (
        db.query(StudentSession)
        .filter(StudentSession.start_time >= today_start)
        .count()
    )
    safety_flags_today = (
        db.query(ValidatorAuditLog)
        .filter(
            ValidatorAuditLog.created_at >= today_start,
            ValidatorAuditLog.safety_violation.is_(True),
        )
        .count()
    )

    user_logs_today = (
        db.query(ChatLog)
        .filter(ChatLog.role == "user", ChatLog.timestamp >= today_start)
        .all()
    )
    injection_attempts_today = 0
    for log in user_logs_today:
        content = str(log.content or "").lower()
        if any(pattern in content for pattern in INJECTION_PATTERNS):
            injection_attempts_today += 1

    overall_status = "ok" if db_service_status == "ok" else "degraded"
    return {
        "status": overall_status,
        "services": {
            "database": db_service_status,
            "gemini_api": gemini_status,
            "medgemma_api": medgemma_status,
        },
        "stats": {
            "total_users": total_users,
            "active_sessions_today": active_sessions_today,
            "safety_flags_today": safety_flags_today,
            "injection_attempts_today": injection_attempts_today,
        },
    }
