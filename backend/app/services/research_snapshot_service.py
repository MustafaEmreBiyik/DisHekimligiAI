"""S11-A: Reproducible Research Snapshot Service.

Creates immutable system-state bundles so published results can be reproduced
months after the study concludes.  A snapshot captures:
  - All active questions (with rubric versions)
  - All active case definitions (with scoring rules)
  - Composite scoring weights and weak-topic threshold
  - LLM model IDs used in the last 90 days
  - Git HEAD commit hash (best-effort)
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.constants import COMPOSITE_WEIGHTS, WEAK_THRESHOLD_PCT
from db.database import (
    CaseDefinition,
    LLMInteractionLog,
    Question,
    RubricVersion,
    SystemSnapshot,
)


def _git_commit_hash() -> str | None:
    """Return the current git HEAD SHA (short form), or None if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _serialize_question(q: Question) -> dict[str, Any]:
    return {
        "id": q.id,
        "question_id": q.question_id,
        "question_type": q.question_type.value if q.question_type else None,
        "question_text": q.question_text,
        "topic_id": q.topic_id,
        "bloom_level": q.bloom_level,
        "difficulty": q.difficulty,
        "safety_category": q.safety_category,
        "unit_id": q.unit_id,
        "week_number": q.week_number,
        "competency_areas": q.competency_areas,
        "max_score": q.max_score,
        "current_rubric_version": q.current_rubric_version,
        "options_json": q.options_json,
        "correct_option": q.correct_option,
        "instructor_explanation": q.instructor_explanation,
        "rubric_guide": q.rubric_guide,
        "model_answer_outline": q.model_answer_outline,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
    }


def _serialize_case(c: CaseDefinition) -> dict[str, Any]:
    return {
        "id": c.id,
        "case_id": c.case_id,
        "schema_version": c.schema_version,
        "title": c.title,
        "category": c.category,
        "difficulty": c.difficulty,
        "estimated_duration_minutes": c.estimated_duration_minutes,
        "learning_objectives": c.learning_objectives,
        "prerequisite_competencies": c.prerequisite_competencies,
        "competency_tags": c.competency_tags,
        "initial_state": c.initial_state,
        "states_json": c.states_json,
        "patient_info_json": c.patient_info_json,
        "rules_json": c.rules_json,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _serialize_rubric_version(rv: RubricVersion) -> dict[str, Any]:
    return {
        "id": rv.id,
        "question_id": rv.question_id,
        "version": rv.version,
        "rubric_guide": rv.rubric_guide,
        "model_answer_outline": rv.model_answer_outline,
        "change_notes": rv.change_notes,
        "created_by": rv.created_by,
        "created_at": rv.created_at.isoformat() if rv.created_at else None,
    }


def _collect_llm_config(db: Session) -> dict[str, Any]:
    """Summarise LLM models used in the last 90 days."""
    cutoff = datetime.utcnow() - timedelta(days=90)
    rows = (
        db.query(
            LLMInteractionLog.provider,
            LLMInteractionLog.model_id,
        )
        .filter(LLMInteractionLog.created_at >= cutoff)
        .distinct()
        .all()
    )
    models = [{"provider": r.provider, "model_id": r.model_id} for r in rows]
    return {
        "observation_window_days": 90,
        "models_observed": models,
        "captured_at": datetime.utcnow().isoformat(),
    }


def create_snapshot(
    db: Session,
    *,
    label: str,
    created_by: str,
    notes: str | None = None,
) -> SystemSnapshot:
    """Build and persist a full system snapshot.

    Args:
        db: Database session.
        label: Human-readable name (e.g. "Bahar 2026 – Snapshot 1").
        created_by: User ID of the instructor requesting the snapshot.
        notes: Optional free-text notes appended to the snapshot record.

    Returns:
        The persisted SystemSnapshot ORM instance.
    """
    questions = (
        db.query(Question)
        .filter(Question.is_active.is_(True), Question.is_archived.is_(False))
        .order_by(Question.id)
        .all()
    )
    cases = (
        db.query(CaseDefinition)
        .filter(CaseDefinition.is_active.is_(True), CaseDefinition.is_archived.is_(False))
        .order_by(CaseDefinition.id)
        .all()
    )
    rubric_versions = (
        db.query(RubricVersion)
        .order_by(RubricVersion.question_id, RubricVersion.version)
        .all()
    )

    questions_payload = [_serialize_question(q) for q in questions]
    case_definitions_payload = [_serialize_case(c) for c in cases]
    rubric_versions_payload = [_serialize_rubric_version(rv) for rv in rubric_versions]

    scoring_config_payload = {
        "composite_weights": COMPOSITE_WEIGHTS,
        "weak_threshold_pct": WEAK_THRESHOLD_PCT,
        "env_overrides": {
            "DENTAI_WEIGHT_MCQ": os.getenv("DENTAI_WEIGHT_MCQ"),
            "DENTAI_WEIGHT_OE": os.getenv("DENTAI_WEIGHT_OE"),
            "DENTAI_WEIGHT_CASE": os.getenv("DENTAI_WEIGHT_CASE"),
            "DENTAI_WEAK_THRESHOLD": os.getenv("DENTAI_WEAK_THRESHOLD"),
        },
    }

    llm_config_payload = _collect_llm_config(db)

    bundle = {
        "schema": "dentai-research-snapshot-v1",
        "label": label,
        "created_by": created_by,
        "created_at": datetime.utcnow().isoformat(),
        "notes": notes,
        "git_commit_hash": _git_commit_hash(),
        "questions": questions_payload,
        "case_definitions": case_definitions_payload,
        "rubric_versions": rubric_versions_payload,
        "scoring_config": scoring_config_payload,
        "llm_config": llm_config_payload,
    }
    bundle_bytes = len(json.dumps(bundle, ensure_ascii=False).encode("utf-8"))

    snapshot = SystemSnapshot(
        label=label,
        created_by=created_by,
        notes=notes,
        git_commit_hash=bundle["git_commit_hash"],
        questions_count=len(questions_payload),
        cases_count=len(case_definitions_payload),
        questions_payload=questions_payload,
        case_definitions_payload=case_definitions_payload,
        scoring_config_payload=scoring_config_payload,
        llm_config_payload=llm_config_payload,
        rubric_versions_payload=rubric_versions_payload,
        bundle_size_bytes=bundle_bytes,
        created_at=datetime.utcnow(),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def export_bundle(snapshot: SystemSnapshot) -> bytes:
    """Serialize a snapshot to a JSON bundle ready for download."""
    bundle = {
        "schema": "dentai-research-snapshot-v1",
        "label": snapshot.label,
        "created_by": snapshot.created_by,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "notes": snapshot.notes,
        "git_commit_hash": snapshot.git_commit_hash,
        "questions": snapshot.questions_payload,
        "case_definitions": snapshot.case_definitions_payload,
        "rubric_versions": snapshot.rubric_versions_payload,
        "scoring_config": snapshot.scoring_config_payload,
        "llm_config": snapshot.llm_config_payload,
    }
    return json.dumps(bundle, ensure_ascii=False, indent=2).encode("utf-8")
