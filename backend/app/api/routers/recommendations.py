"""Student recommendation endpoints with explainable scoring."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import AuthenticatedUser, get_db, require_roles
from db.database import (
    CaseDefinition,
    ChatLog,
    ExamResult,
    RecommendationSnapshot,
    StudentSession,
    UserRole,
)

logger = logging.getLogger(__name__)

router = APIRouter()

ALGORITHM_VERSION = "v1_competency_based"
SCORING_RULES_PATH = Path(__file__).resolve().parents[3] / "data" / "scoring_rules.json"
CASE_SCENARIOS_PATH = Path(__file__).resolve().parents[3] / "data" / "case_scenarios.json"


class TopFeature(BaseModel):
    name: str
    contribution: float
    direction: str  # "up" | "down"


class RecommendationItem(BaseModel):
    case_id: str
    title: str
    difficulty: str
    estimated_duration_minutes: int
    competency_tags: list[str]
    reason_code: str
    reason_text: str
    priority_score: int
    top_features: Optional[list[TopFeature]] = None
    model_version: Optional[str] = None


class RecommendationMeta(BaseModel):
    algorithm_version: str
    generated_at: str
    cold_start: bool


class RecommendationResponse(BaseModel):
    recommendations: list[RecommendationItem]
    meta: RecommendationMeta


class CandidateCase(BaseModel):
    case_id: str
    title: str
    difficulty: str
    estimated_duration_minutes: int
    competency_tags: list[str]


def _load_scoring_rules_index() -> dict[str, dict[str, Any]]:
    with open(SCORING_RULES_PATH, "r", encoding="utf-8") as file:
        payload = json.load(file)

    index: dict[str, dict[str, Any]] = {}
    for case_rule_set in payload:
        case_id = str(case_rule_set.get("case_id", "")).strip()
        if not case_id:
            continue

        for rule in case_rule_set.get("rules", []):
            action = str(rule.get("target_action", "")).strip()
            if not action:
                continue

            key = f"{case_id}:{action}"
            index[key] = {
                "is_critical_safety_rule": bool(rule.get("is_critical_safety_rule", False)),
                "competency_tags": [
                    str(tag).strip()
                    for tag in rule.get("competency_tags", [])
                    if isinstance(tag, str) and tag.strip()
                ],
            }
    return index


def _build_case_candidates(db: Session) -> list[CandidateCase]:
    has_any_cases = db.query(CaseDefinition.id).filter(CaseDefinition.is_archived.is_(False)).first() is not None

    if has_any_cases:
        db_cases = (
            db.query(CaseDefinition)
            .filter(CaseDefinition.is_active.is_(True), CaseDefinition.is_archived.is_(False))
            .all()
        )
        return [
            CandidateCase(
                case_id=case.case_id,
                title=case.title,
                difficulty=str(case.difficulty).lower(),
                estimated_duration_minutes=int(case.estimated_duration_minutes),
                competency_tags=[
                    str(tag).strip()
                    for tag in (case.competency_tags or [])
                    if isinstance(tag, str) and tag.strip()
                ],
            )
            for case in db_cases
        ]

    # Fallback to canonical JSON if DB imports are not present yet.
    with open(CASE_SCENARIOS_PATH, "r", encoding="utf-8") as file:
        payload = json.load(file)

    candidates: list[CandidateCase] = []
    for case in payload:
        if not isinstance(case, dict) or case.get("is_active") is not True:
            continue

        case_id = str(case.get("case_id", "")).strip()
        title = str(case.get("title", "")).strip()
        difficulty = str(case.get("difficulty", "")).strip().lower()
        duration = case.get("estimated_duration_minutes")
        tags = case.get("competency_tags", [])

        if not case_id or not title or not difficulty or not isinstance(duration, int):
            continue

        candidates.append(
            CandidateCase(
                case_id=case_id,
                title=title,
                difficulty=difficulty,
                estimated_duration_minutes=duration,
                competency_tags=[
                    str(tag).strip()
                    for tag in tags
                    if isinstance(tag, str) and tag.strip()
                ],
            )
        )

    return candidates


def _mean_percentage(db: Session, user_id: str) -> float:
    results = (
        db.query(ExamResult)
        .filter(ExamResult.user_id == user_id, ExamResult.max_score > 0)
        .all()
    )
    if results:
        percentages = [(row.score / row.max_score) * 100.0 for row in results]
        return sum(percentages) / len(percentages)

    sessions = db.query(StudentSession).filter(StudentSession.student_id == user_id).all()
    if not sessions:
        return 0.0

    # Fallback heuristic if only session scores exist.
    normalized = [max(0.0, min(float(s.current_score or 0.0), 100.0)) for s in sessions]
    return sum(normalized) / len(normalized)


def _difficulty_score(avg_percentage: float, difficulty: str) -> int:
    if avg_percentage < 60.0:
        table = {"beginner": 20, "intermediate": 8, "advanced": 0}
    elif avg_percentage <= 80.0:
        table = {"beginner": 10, "intermediate": 20, "advanced": 8}
    else:
        table = {"beginner": 6, "intermediate": 12, "advanced": 20}
    return table.get(difficulty, 0)


def _extract_weak_competencies(db: Session, user_id: str) -> set[str]:
    rules_index = _load_scoring_rules_index()
    sessions = db.query(StudentSession).filter(StudentSession.student_id == user_id).all()
    if not sessions:
        return set()

    session_ids = [session.id for session in sessions]
    assistant_logs = (
        db.query(ChatLog)
        .filter(ChatLog.session_id.in_(session_ids), ChatLog.role == "assistant")
        .all()
    )

    weak_counter: Counter[str] = Counter()
    for log in assistant_logs:
        metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
        interpreted_action = str(metadata.get("interpreted_action", "")).strip()
        if not interpreted_action:
            continue

        session = next((item for item in sessions if item.id == log.session_id), None)
        if session is None:
            continue

        rule_key = f"{session.case_id}:{interpreted_action}"
        rule_meta = rules_index.get(rule_key)
        if not rule_meta or not rule_meta.get("is_critical_safety_rule"):
            continue

        score = float(metadata.get("score", 0.0) or 0.0)
        silent_eval = metadata.get("silent_evaluation", {})
        safety_violation = bool(silent_eval.get("safety_violation", False)) if isinstance(silent_eval, dict) else False

        if safety_violation or score <= 0.0:
            for tag in rule_meta.get("competency_tags", []):
                weak_counter[tag] += 1

    return {tag for tag, count in weak_counter.items() if count > 0}


def _build_reason(
    *,
    cold_start: bool,
    overlap_count: int,
    is_not_attempted: bool,
    difficulty_score: int,
    weak_tags: set[str],
) -> tuple[str, str]:
    if cold_start:
        return "cold_start", "Ilk kullanim fallback'i uygulandi: beginner vakalar onceliklendirildi."
    if overlap_count > 0:
        first_tag = sorted(weak_tags)[0] if weak_tags else "ilgili"
        return "weak_competency", f"{first_tag} alaninda eksiklik tespit edildi."
    if is_not_attempted:
        return "not_attempted", "Bu vaka henuz baslanmamis oldugu icin onceliklendirildi."
    if difficulty_score > 0:
        return "difficulty_match", "Vaka zorlugu mevcut performans duzeyinle uyumlu."
    return "difficulty_match", "Genel denge icin sirali oneride tutuldu."


@router.get("/me", response_model=RecommendationResponse)
def get_my_recommendations(
    algorithm: Optional[str] = Query(
        None,
        description="Force a specific algorithm: v1_competency_based | v2_hybrid_xgb_irt_bkt | auto",
    ),
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    from app.services.recommendation_engine_v2 import (
        get_active_model_version,
        persist_recommendation_snapshots,
        recommend,
    )

    try:
        engine_result = recommend(db, current_user.user_id, k=5, algorithm=algorithm)
        active_model = get_active_model_version(db)
        persist_recommendation_snapshots(db, current_user.user_id, engine_result, active_model)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(
            "Recommendation engine failed for user=%s: %s — falling back to v1",
            current_user.user_id, exc, exc_info=True,
        )
        # Hard fallback: run v1 directly without feature logs
        engine_result = _v1_fallback(db, current_user.user_id)
        _persist_v1_snapshots(db, current_user.user_id, engine_result)
        db.commit()

    items = [
        RecommendationItem(
            case_id=r.case_id,
            title=r.title,
            difficulty=r.difficulty,
            estimated_duration_minutes=r.estimated_duration_minutes,
            competency_tags=r.competency_tags,
            reason_code=r.reason_code,
            reason_text=r.reason_text,
            priority_score=int(r.priority_score),
            top_features=[
                TopFeature(
                    name=f["name"],
                    contribution=float(f["contribution"]),
                    direction=str(f["direction"]),
                )
                for f in (r.top_features or [])
            ] or None,
            model_version=r.model_version,
        )
        for r in engine_result.items
    ]

    return RecommendationResponse(
        recommendations=items,
        meta=RecommendationMeta(
            algorithm_version=engine_result.algorithm_version,
            generated_at=datetime.utcnow().isoformat(),
            cold_start=engine_result.cold_start,
        ),
    )


def _v1_fallback(db: Session, user_id: str):
    """Direct v1 call used only when the engine itself crashes."""
    from app.services.recommendation_engine_v2 import _run_v1, ALGORITHM_V1
    return _run_v1(db, user_id, k=5, algorithm_label=ALGORITHM_V1)


def _persist_v1_snapshots(db: Session, user_id: str, engine_result) -> None:
    for item in engine_result.items:
        db.add(RecommendationSnapshot(
            user_id=user_id,
            case_id=item.case_id,
            reason_code=item.reason_code,
            reason_text=item.reason_text,
            priority_score=int(item.priority_score),
            algorithm_version=engine_result.algorithm_version,
        ))
    db.flush()
