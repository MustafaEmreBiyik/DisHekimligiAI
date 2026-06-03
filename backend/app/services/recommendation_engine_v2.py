"""
Recommendation Engine v2 — Sprint 11 T06
==========================================
Hybrid inference: XGBoost ranker when an active model exists, graceful
degradation to v1 rule-based engine for cold-start users and when no model
is available.

Dispatch logic
--------------
1. `algorithm == "v1_competency_based"` OR no active model row  →  v1 legacy
2. Active model exists AND user has < COLD_START_THRESHOLD sessions
       → v1 scoring, but labelled "v2_hybrid_xgb_irt_bkt_coldstart"
3. Active model exists AND user is warm  →  full XGBoost + SHAP path

ε-greedy exploration
--------------------
With probability DENTAI_EXPLORATION_EPSILON (default 0.10), a random
unattempted case is injected into position 3 of the top-5. Logged as
reason_code="exploration" so it can be tracked in analysis.

Snapshot writes
---------------
Every recommendation request writes:
  - One RecommendationSnapshot per returned item (existing schema).
  - One RecommendationFeatureLog per snapshot when an ML model is active
    (feature vector + SHAP values stored for offline debugging).
Both writes share the same transaction: feature log failure rolls back snapshot.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import xgboost as xgb
from sqlalchemy.orm import Session

from app.constants import (
    EXPLORATION_EPSILON,
    FEATURE_COLD_START_SESSION_THRESHOLD,
    RECOMMENDATION_ALGORITHM,
    RECOMMENDATION_FALLBACK,
)
from app.services import feature_store as fs
from app.services import recommendation_explainer as explainer
from app.services.recommendation_trainer import load_bundle
from db.database import (
    CaseDefinition,
    ChatLog,
    ExamResult,
    RecommendationFeatureLog,
    RecommendationModelVersion,
    RecommendationSnapshot,
    StudentSession,
)

logger = logging.getLogger(__name__)

ALGORITHM_V1        = "v1_competency_based"
ALGORITHM_V2        = "v2_hybrid_xgb_irt_bkt"
ALGORITHM_COLDSTART = "v2_hybrid_xgb_irt_bkt_coldstart"

# Module-level bundle cache: model_version_id → (booster, scaler, feature_columns)
_bundle_cache: dict[int, tuple[xgb.Booster, object, list[str]]] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_active_model_version(db: Session) -> Optional[RecommendationModelVersion]:
    return (
        db.query(RecommendationModelVersion)
        .filter(RecommendationModelVersion.is_active.is_(True))
        .first()
    )


def _load_bundle_cached(model_version: RecommendationModelVersion):
    vid = model_version.id
    if vid not in _bundle_cache:
        try:
            _bundle_cache[vid] = load_bundle(model_version.model_blob_path)
        except Exception as exc:
            logger.warning(
                "Failed to load model bundle id=%d path=%s: %s",
                vid, model_version.model_blob_path, exc,
            )
            return None
    return _bundle_cache[vid]


def invalidate_bundle_cache(model_version_id: int) -> None:
    """Call after model promotion/rollback so stale bundles are evicted."""
    _bundle_cache.pop(model_version_id, None)
    explainer.invalidate_cache(model_version_id)


def _is_cold_start(db: Session, user_id: str) -> bool:
    count = (
        db.query(StudentSession)
        .filter(StudentSession.student_id == user_id)
        .count()
    )
    return count < FEATURE_COLD_START_SESSION_THRESHOLD


def _build_active_candidates(db: Session) -> list[CaseDefinition]:
    return (
        db.query(CaseDefinition)
        .filter(CaseDefinition.is_active.is_(True), CaseDefinition.is_archived.is_(False))
        .all()
    )


def _attempted_case_ids(db: Session, user_id: str) -> set[str]:
    return {
        row[0]
        for row in db.query(StudentSession.case_id)
        .filter(StudentSession.student_id == user_id)
        .distinct()
        .all()
    }


def _completed_case_ids(db: Session, user_id: str) -> set[str]:
    return {
        row[0]
        for row in db.query(ExamResult.case_id)
        .filter(ExamResult.user_id == user_id, ExamResult.max_score > 0)
        .distinct()
        .all()
    }


# ---------------------------------------------------------------------------
# V1 scoring (extracted from recommendations router for reuse)
# ---------------------------------------------------------------------------

def _v1_priority_score(
    candidate: CaseDefinition,
    completed_ids: set[str],
    attempted_ids: set[str],
    weak_competency_tags: set[str],
    avg_pct: float,
    cold_start: bool,
) -> tuple[int, str, str]:
    """Return (priority_score, reason_code, reason_text)."""
    difficulty = str(candidate.difficulty or "").lower()
    tags = {str(t).strip().lower() for t in (candidate.competency_tags or [])}
    overlap = tags.intersection(weak_competency_tags)
    overlap_count = len(overlap)

    diff_table: dict[str, dict[str, int]]
    if avg_pct < 60.0:
        diff_table = {"beginner": 20, "intermediate": 8, "advanced": 0}
    elif avg_pct <= 80.0:
        diff_table = {"beginner": 10, "intermediate": 20, "advanced": 8}
    else:
        diff_table = {"beginner": 6, "intermediate": 12, "advanced": 20}
    difficulty_pts = diff_table.get(difficulty, 0)

    if candidate.case_id in completed_ids:
        return 0, "completed", "Bu vaka tamamlandı."

    score = 50  # base for all incomplete cases
    if candidate.case_id not in attempted_ids:
        score += 10
    if overlap_count > 0:
        score += 30 + 5 * overlap_count
    score += difficulty_pts
    if cold_start and difficulty == "beginner":
        score += 15

    if cold_start:
        reason_code = "cold_start"
        reason_text = "İlk kullanım: başlangıç seviyesi vakalar önceliklendirildi."
    elif overlap_count > 0:
        first_tag = sorted(overlap)[0]
        reason_code = "weak_competency"
        reason_text = f"{first_tag} alanında eksiklik tespit edildi."
    elif candidate.case_id not in attempted_ids:
        reason_code = "not_attempted"
        reason_text = "Bu vaka henüz başlanmamış olduğu için önceliklendirildi."
    else:
        reason_code = "difficulty_match"
        reason_text = "Vaka zorluğu mevcut performans düzeyinle uyumlu."

    return score, reason_code, reason_text


def _v1_avg_pct(db: Session, user_id: str) -> float:
    results = (
        db.query(ExamResult)
        .filter(ExamResult.user_id == user_id, ExamResult.max_score > 0)
        .all()
    )
    if results:
        return sum((r.score / r.max_score) * 100.0 for r in results) / len(results)
    sessions = db.query(StudentSession).filter(StudentSession.student_id == user_id).all()
    if not sessions:
        return 0.0
    return sum(max(0.0, min(float(s.current_score or 0.0), 100.0)) for s in sessions) / len(sessions)


def _v1_weak_competencies(db: Session, user_id: str) -> set[str]:
    from collections import Counter
    import json
    from pathlib import Path

    rules_path = Path(__file__).resolve().parents[3] / "data" / "scoring_rules.json"
    if not rules_path.exists():
        return set()

    with open(rules_path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    rules_index: dict[str, dict] = {}
    for case_entry in payload:
        cid = str(case_entry.get("case_id", "")).strip()
        for rule in case_entry.get("rules", []):
            action = str(rule.get("target_action", "")).strip()
            if cid and action:
                rules_index[f"{cid}:{action}"] = {
                    "is_critical": bool(rule.get("is_critical_safety_rule", False)),
                    "tags": [str(t).strip() for t in rule.get("competency_tags", [])],
                }

    sessions = db.query(StudentSession).filter(StudentSession.student_id == user_id).all()
    if not sessions:
        return set()

    session_map = {s.id: s for s in sessions}
    logs = (
        db.query(ChatLog)
        .filter(ChatLog.session_id.in_(list(session_map)), ChatLog.role == "assistant")
        .all()
    )

    weak_counter: Counter = Counter()
    for log in logs:
        meta = log.metadata_json if isinstance(log.metadata_json, dict) else {}
        action = str(meta.get("interpreted_action", "")).strip()
        if not action:
            continue
        sess = session_map.get(log.session_id)
        if not sess:
            continue
        rule = rules_index.get(f"{sess.case_id}:{action}")
        if not rule or not rule["is_critical"]:
            continue
        score = float(meta.get("score", 0.0) or 0.0)
        ev = meta.get("silent_evaluation", {})
        violation = bool(ev.get("safety_violation", False)) if isinstance(ev, dict) else False
        if violation or score <= 0.0:
            for tag in rule["tags"]:
                weak_counter[tag] += 1

    return {tag for tag, count in weak_counter.items() if count > 0}


# ---------------------------------------------------------------------------
# Recommendation result dataclass
# ---------------------------------------------------------------------------

class CandidateResult:
    __slots__ = [
        "case_id", "title", "difficulty", "estimated_duration_minutes",
        "competency_tags", "reason_code", "reason_text", "priority_score",
        "top_features", "model_version", "feature_vector",
    ]

    def __init__(
        self,
        case_id: str,
        title: str,
        difficulty: str,
        estimated_duration_minutes: int,
        competency_tags: list[str],
        reason_code: str,
        reason_text: str,
        priority_score: float,
        top_features: Optional[list[dict]] = None,
        model_version: Optional[str] = None,
        feature_vector: Optional[dict] = None,
    ):
        self.case_id = case_id
        self.title = title
        self.difficulty = difficulty
        self.estimated_duration_minutes = estimated_duration_minutes
        self.competency_tags = competency_tags
        self.reason_code = reason_code
        self.reason_text = reason_text
        self.priority_score = priority_score
        self.top_features = top_features or []
        self.model_version = model_version
        self.feature_vector = feature_vector or {}


class RecommendationEngineResult:
    __slots__ = ["items", "algorithm_version", "cold_start"]

    def __init__(
        self,
        items: list[CandidateResult],
        algorithm_version: str,
        cold_start: bool,
    ):
        self.items = items
        self.algorithm_version = algorithm_version
        self.cold_start = cold_start


# ---------------------------------------------------------------------------
# V1 path
# ---------------------------------------------------------------------------

def _run_v1(
    db: Session,
    user_id: str,
    k: int,
    algorithm_label: str,
) -> RecommendationEngineResult:
    candidates = _build_active_candidates(db)
    if not candidates:
        return RecommendationEngineResult([], algorithm_label, cold_start=True)

    completed_ids = _completed_case_ids(db, user_id)
    attempted_ids = _attempted_case_ids(db, user_id)
    cold_start = not attempted_ids
    avg_pct = _v1_avg_pct(db, user_id)
    weak_tags = _v1_weak_competencies(db, user_id)

    scored: list[tuple[float, CandidateResult]] = []
    for c in candidates:
        score, code, text = _v1_priority_score(
            c, completed_ids, attempted_ids, weak_tags, avg_pct, cold_start
        )
        scored.append((score, CandidateResult(
            case_id=c.case_id,
            title=c.title,
            difficulty=str(c.difficulty).lower(),
            estimated_duration_minutes=int(c.estimated_duration_minutes or 30),
            competency_tags=[str(t).strip() for t in (c.competency_tags or []) if str(t).strip()],
            reason_code=code,
            reason_text=text,
            priority_score=score,
            model_version=None,
        )))

    scored.sort(key=lambda x: (-x[0], x[1].case_id))
    top = [r for _, r in scored[:k]]
    return RecommendationEngineResult(top, algorithm_label, cold_start=cold_start)


# ---------------------------------------------------------------------------
# V2 path
# ---------------------------------------------------------------------------

def _apply_epsilon_greedy(
    ranked: list[CandidateResult],
    candidates: list[CaseDefinition],
    attempted_ids: set[str],
    model_version_str: str,
) -> list[CandidateResult]:
    """Inject a random unattempted case into position 3 with probability ε."""
    if random.random() >= EXPLORATION_EPSILON:
        return ranked

    top_ids = {r.case_id for r in ranked}
    unattempted = [
        c for c in candidates
        if c.case_id not in attempted_ids and c.case_id not in top_ids
    ]
    if not unattempted:
        return ranked

    pick = random.choice(unattempted)
    exploration_item = CandidateResult(
        case_id=pick.case_id,
        title=pick.title,
        difficulty=str(pick.difficulty).lower(),
        estimated_duration_minutes=int(pick.estimated_duration_minutes or 30),
        competency_tags=[str(t).strip() for t in (pick.competency_tags or []) if str(t).strip()],
        reason_code="exploration",
        reason_text="Keşif: farklı bir vaka denemeniz için önerildi.",
        priority_score=0,
        model_version=model_version_str,
    )

    result = list(ranked)
    insert_pos = min(2, len(result))  # position 3 (0-indexed: 2)
    result.insert(insert_pos, exploration_item)
    return result[:len(ranked)]  # keep original length


def _run_v2(
    db: Session,
    user_id: str,
    k: int,
    model_version: RecommendationModelVersion,
) -> RecommendationEngineResult:
    bundle = _load_bundle_cached(model_version)
    if bundle is None:
        logger.warning(
            "model bundle unavailable for version %d — falling back to v1",
            model_version.id,
        )
        return _run_v1(db, user_id, k, ALGORITHM_V1)

    booster, scaler, feature_columns = bundle
    candidates = _build_active_candidates(db)
    if not candidates:
        return RecommendationEngineResult([], ALGORITHM_V2, cold_start=False)

    attempted_ids = _attempted_case_ids(db, user_id)
    completed_ids  = _completed_case_ids(db, user_id)

    # Build feature vectors
    feature_rows = [
        fs.build_candidate_row(db, user_id, c.case_id)
        for c in candidates
    ]

    # Score with XGBoost
    X = np.array([[row.get(col, 0.0) for col in feature_columns] for row in feature_rows])
    X_scaled = scaler.transform(X)
    dm = xgb.DMatrix(X_scaled, feature_names=feature_columns)
    scores = booster.predict(dm)

    # SHAP top features (per candidate)
    top_features_all = explainer.compute_top_features(
        booster=booster,
        scaler=scaler,
        feature_columns=feature_columns,
        feature_rows=feature_rows,
        model_version_id=model_version.id,
        top_n=3,
    )

    # Rank by score descending
    order = np.argsort(scores)[::-1]
    ranked: list[CandidateResult] = []
    for i in order[:k]:
        c = candidates[i]
        score_val = float(scores[i])

        if c.case_id in completed_ids:
            reason_code, reason_text = "completed", "Bu vaka tamamlandı."
        elif score_val > 0.7:
            reason_code, reason_text = "high_match", "Profil analizine göre çok uyumlu vaka."
        elif c.case_id not in attempted_ids:
            reason_code, reason_text = "not_attempted", "Henüz başlanmamış vaka."
        else:
            reason_code, reason_text = "difficulty_match", "Vaka zorluğu performans düzeyinle uyumlu."

        ranked.append(CandidateResult(
            case_id=c.case_id,
            title=c.title,
            difficulty=str(c.difficulty).lower(),
            estimated_duration_minutes=int(c.estimated_duration_minutes or 30),
            competency_tags=[str(t).strip() for t in (c.competency_tags or []) if str(t).strip()],
            reason_code=reason_code,
            reason_text=reason_text,
            priority_score=round(score_val * 100),
            top_features=top_features_all[int(i)] if top_features_all else [],
            model_version=model_version.algorithm_version,
            feature_vector=feature_rows[i],
        ))

    # ε-greedy exploration
    ranked = _apply_epsilon_greedy(ranked, candidates, attempted_ids, model_version.algorithm_version)

    return RecommendationEngineResult(ranked, ALGORITHM_V2, cold_start=False)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def recommend(
    db: Session,
    user_id: str,
    k: int = 5,
    algorithm: Optional[str] = None,
) -> RecommendationEngineResult:
    """
    Return top-k recommendations for user_id using the appropriate algorithm.

    Parameters
    ----------
    db        : active SQLAlchemy session
    user_id   : student's user_id string
    k         : number of recommendations to return (default 5)
    algorithm : override; None → reads DENTAI_RECOMMENDATION_ALGORITHM env var
    """
    requested = algorithm or RECOMMENDATION_ALGORITHM

    # Explicit v1 request
    if requested == ALGORITHM_V1:
        return _run_v1(db, user_id, k, ALGORITHM_V1)

    active_model = get_active_model_version(db)

    # No trained model → silent v1 fallback
    if active_model is None:
        logger.info(
            "No active recommendation model found — falling back to %s for user=%s",
            RECOMMENDATION_FALLBACK, user_id,
        )
        return _run_v1(db, user_id, k, ALGORITHM_V1)

    # Cold-start guard: use v1 scoring but stamp with coldstart version
    if _is_cold_start(db, user_id):
        result = _run_v1(db, user_id, k, ALGORITHM_COLDSTART)
        result.cold_start = True
        # Attach model_version to items so the response is distinguishable
        for item in result.items:
            item.model_version = ALGORITHM_COLDSTART
        return result

    # Full v2 path
    return _run_v2(db, user_id, k, active_model)


# ---------------------------------------------------------------------------
# Snapshot persistence
# ---------------------------------------------------------------------------

def persist_recommendation_snapshots(
    db: Session,
    user_id: str,
    result: RecommendationEngineResult,
    active_model: Optional[RecommendationModelVersion],
) -> None:
    """
    Write RecommendationSnapshot + optional RecommendationFeatureLog rows.

    Both writes are flushed together; the caller commits the transaction.
    A failure to write the feature log will cause a db.rollback() in the caller.
    """
    for item in result.items:
        snap = RecommendationSnapshot(
            user_id=user_id,
            case_id=item.case_id,
            reason_code=item.reason_code,
            reason_text=item.reason_text,
            priority_score=int(item.priority_score),
            algorithm_version=result.algorithm_version,
            created_at=_utcnow(),
        )
        db.add(snap)
        db.flush()  # populates snap.id

        if active_model is not None and item.feature_vector:
            feat_log = RecommendationFeatureLog(
                snapshot_id=snap.id,
                feature_vector_json=item.feature_vector,
                shap_values_json=item.top_features or None,
                model_version_id=active_model.id,
                created_at=_utcnow(),
            )
            db.add(feat_log)

    db.flush()
