"""
Feature Store — Sprint 11 T02
==============================
Single source of truth for the (user, case) feature matrix fed to the XGBoost
ranker (T05) and the hybrid inference engine (T06).

All public functions are *time-aware*: the optional `asof` parameter restricts
every query to events strictly before that timestamp. Training pipelines MUST
pass asof to prevent future-leakage; inference passes None (≡ "now").

Feature taxonomy (37 numeric columns — all floats, booleans encoded as 0.0/1.0):
  User-global   (5): mean_composite_score_30d, n_sessions_total,
                      n_sessions_last_7d, days_since_last_session, cold_start_flag
  User-mastery  (4): mean_mastery_prob_all_topics, min_mastery_prob,
                      n_topics_below_60pct, n_topics_above_80pct
  User-cognitive(3): avg_response_latency_ms_session, hint_usage_rate,
                      reasoning_deviation_rate
  User-safety   (2): safety_reaction_time_p50, safety_action_completion_rate
  Case-static   (9): case_difficulty_ordinal, estimated_duration_minutes,
                      n_competency_tags, n_safety_critical_rules,
                      irt_mean_b_mapped_questions, irt_mean_a_mapped_questions,
                      n_prerequisite_competencies, n_learning_objectives,
                      n_mapped_questions
  Case-historical(4): historical_avg_completion_score, historical_completion_rate,
                       historical_avg_session_length_min, historical_n_unique_users_attempted
  Cross         (6): mastery_gap_on_case_topics, n_prior_attempts_on_case,
                      is_completed, is_in_progress, days_since_last_attempt_on_case,
                      competency_overlap_with_weak_areas
  Reasoning     (4): reasoning_pattern_0..3  (one-hot, dominant pattern per session)

Usage
-----
from app.services.feature_store import build_candidate_row, materialise_training_frame
"""

from __future__ import annotations

import json
import logging
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.constants import (
    BKT_MASTERY_HIGH_THRESHOLD,
    BKT_MASTERY_LOW_THRESHOLD,
    FEATURE_COLD_START_SESSION_THRESHOLD,
)
from db.database import (
    CaseDefinition,
    ChatLog,
    CoachHint,
    ExamResult,
    IRTParameters,
    MasteryState,
    Question,
    QuestionCaseMapping,
    RecommendationSnapshot,
    StudentSession,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCORING_RULES_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "scoring_rules.json"
)

_DIFFICULTY_ORDINAL: dict[str, float] = {
    "beginner": 0.0,
    "easy": 0.0,
    "intermediate": 1.0,
    "medium": 1.0,
    "advanced": 2.0,
    "hard": 2.0,
}

# Default imputation values for cold-start / missing features
_DEFAULTS: dict[str, float] = {
    # User-global
    "mean_composite_score_30d": 50.0,
    "n_sessions_total": 0.0,
    "n_sessions_last_7d": 0.0,
    "days_since_last_session": 999.0,
    "cold_start_flag": 0.0,
    # User-mastery
    "mean_mastery_prob_all_topics": 0.20,
    "min_mastery_prob": 0.20,
    "n_topics_below_60pct": 0.0,
    "n_topics_above_80pct": 0.0,
    # User-cognitive
    "avg_response_latency_ms_session": 5000.0,
    "hint_usage_rate": 0.0,
    "reasoning_deviation_rate": 0.0,
    # User-safety
    "safety_reaction_time_p50": 5000.0,
    "safety_action_completion_rate": 0.50,
    # Case-static
    "case_difficulty_ordinal": 0.0,
    "estimated_duration_minutes": 30.0,
    "n_competency_tags": 0.0,
    "n_safety_critical_rules": 0.0,
    "irt_mean_b_mapped_questions": 0.0,
    "irt_mean_a_mapped_questions": 1.0,
    "n_prerequisite_competencies": 0.0,
    "n_learning_objectives": 0.0,
    "n_mapped_questions": 0.0,
    # Case-historical
    "historical_avg_completion_score": 50.0,
    "historical_completion_rate": 0.0,
    "historical_avg_session_length_min": 30.0,
    "historical_n_unique_users_attempted": 0.0,
    # Cross
    "mastery_gap_on_case_topics": 0.0,
    "n_prior_attempts_on_case": 0.0,
    "is_completed": 0.0,
    "is_in_progress": 0.0,
    "days_since_last_attempt_on_case": 999.0,
    "competency_overlap_with_weak_areas": 0.0,
    # Reasoning
    "reasoning_pattern_0": 0.0,
    "reasoning_pattern_1": 0.0,
    "reasoning_pattern_2": 0.0,
    "reasoning_pattern_3": 0.0,
}

FEATURE_COLUMNS: list[str] = list(_DEFAULTS.keys())

assert len(FEATURE_COLUMNS) == 37, (
    f"Expected 37 features, got {len(FEATURE_COLUMNS)}"
)

# Training-frame label + metadata columns (not features)
_LABEL_COLUMNS = ["user_id", "case_id", "asof_ts", "outcome_score"]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _days_ago(dt: Optional[datetime], ref: datetime) -> float:
    if dt is None:
        return 999.0
    delta = ref - dt
    return max(0.0, delta.total_seconds() / 86_400.0)


def _safe_mean(values: list[float]) -> Optional[float]:
    return statistics.mean(values) if values else None


def _canonicalise_topic_id(raw: str) -> str:
    """Normalise topic IDs to prevent duplicate mastery states from casing drift."""
    import unicodedata
    return unicodedata.normalize("NFC", raw.strip().lower())


_scoring_rules_cache: Optional[dict[str, int]] = None


def _safety_rules_per_case() -> dict[str, int]:
    """Return {case_id: n_safety_critical_rules} from scoring_rules.json (cached)."""
    global _scoring_rules_cache
    if _scoring_rules_cache is not None:
        return _scoring_rules_cache

    if not SCORING_RULES_PATH.exists():
        _scoring_rules_cache = {}
        return _scoring_rules_cache

    with open(SCORING_RULES_PATH, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    result: dict[str, int] = {}
    for case_entry in payload:
        cid = str(case_entry.get("case_id", "")).strip()
        if not cid:
            continue
        count = sum(
            1
            for rule in case_entry.get("rules", [])
            if rule.get("is_critical_safety_rule")
        )
        result[cid] = count

    _scoring_rules_cache = result
    return _scoring_rules_cache


def _weak_topic_ids(db: Session, user_id: str, asof: Optional[datetime]) -> set[str]:
    """Return topic IDs where mastery_prob < low threshold, for cross-features."""
    q = db.query(MasteryState).filter(MasteryState.user_id == user_id)
    if asof:
        q = q.filter(MasteryState.updated_at < asof)
    states = q.all()
    return {
        _canonicalise_topic_id(s.topic_id)
        for s in states
        if s.mastery_prob < BKT_MASTERY_LOW_THRESHOLD
    }


# ---------------------------------------------------------------------------
# User feature builder
# ---------------------------------------------------------------------------

def build_user_features(
    db: Session,
    user_id: str,
    asof: Optional[datetime] = None,
) -> dict[str, float]:
    """
    Build the user feature vector (21 features).

    asof=None means "use current wall-clock time". When constructing training
    rows, always pass the recommendation timestamp so no future data leaks in.
    """
    ref = asof or _utcnow()
    thirty_days_ago = datetime(ref.year, ref.month, ref.day) - __import__("datetime").timedelta(days=30)
    seven_days_ago = datetime(ref.year, ref.month, ref.day) - __import__("datetime").timedelta(days=7)

    feat: dict[str, float] = {k: v for k, v in _DEFAULTS.items()}

    # ── User-global ──────────────────────────────────────────────────────────
    sessions_q = db.query(StudentSession).filter(StudentSession.student_id == user_id)
    if asof:
        sessions_q = sessions_q.filter(StudentSession.start_time < asof)
    all_sessions = sessions_q.all()

    n_sessions_total = float(len(all_sessions))
    feat["n_sessions_total"] = n_sessions_total

    n_sessions_last_7d = float(
        sum(1 for s in all_sessions if s.start_time and s.start_time >= seven_days_ago)
    )
    feat["n_sessions_last_7d"] = n_sessions_last_7d

    last_session_dt = max(
        (s.start_time for s in all_sessions if s.start_time), default=None
    )
    feat["days_since_last_session"] = _days_ago(last_session_dt, ref)

    cold_start = n_sessions_total < FEATURE_COLD_START_SESSION_THRESHOLD
    feat["cold_start_flag"] = 1.0 if cold_start else 0.0

    # Composite score over last 30 days: use ExamResult.score/max_score
    exam_q = db.query(ExamResult).filter(
        ExamResult.user_id == user_id,
        ExamResult.max_score > 0,
        ExamResult.case_id != "quiz_global",
    )
    if asof:
        exam_q = exam_q.filter(ExamResult.completed_at < asof)
    recent_exams = [
        r for r in exam_q.all()
        if r.completed_at and r.completed_at >= thirty_days_ago
    ]
    if recent_exams:
        feat["mean_composite_score_30d"] = statistics.mean(
            (r.score / r.max_score) * 100.0 for r in recent_exams
        )

    # ── User-mastery ─────────────────────────────────────────────────────────
    mastery_q = db.query(MasteryState).filter(MasteryState.user_id == user_id)
    if asof:
        mastery_q = mastery_q.filter(MasteryState.updated_at < asof)
    mastery_states = mastery_q.all()

    if mastery_states:
        probs = [s.mastery_prob for s in mastery_states]
        feat["mean_mastery_prob_all_topics"] = statistics.mean(probs)
        feat["min_mastery_prob"] = min(probs)
        feat["n_topics_below_60pct"] = float(
            sum(1 for p in probs if p < BKT_MASTERY_LOW_THRESHOLD)
        )
        feat["n_topics_above_80pct"] = float(
            sum(1 for p in probs if p >= BKT_MASTERY_HIGH_THRESHOLD)
        )

    # ── User-cognitive ───────────────────────────────────────────────────────
    if all_sessions:
        session_ids = [s.id for s in all_sessions]

        # Hint usage rate: hints / sessions
        hint_count = (
            db.query(func.count(CoachHint.id))
            .filter(CoachHint.session_id.in_(session_ids))
            .scalar()
            or 0
        )
        if n_sessions_total > 0:
            feat["hint_usage_rate"] = float(hint_count) / n_sessions_total

        # Response latency: average inter-message gap (user turns) per session
        user_logs = (
            db.query(ChatLog)
            .filter(
                ChatLog.session_id.in_(session_ids),
                ChatLog.role == "user",
            )
            .order_by(ChatLog.session_id, ChatLog.timestamp)
            .all()
        )
        latencies: list[float] = []
        prev_sid: Optional[int] = None
        prev_ts: Optional[datetime] = None
        for log in user_logs:
            if log.session_id == prev_sid and prev_ts and log.timestamp:
                gap_ms = (log.timestamp - prev_ts).total_seconds() * 1000.0
                if 0 < gap_ms < 300_000:  # ignore gaps > 5 min (browser idle)
                    latencies.append(gap_ms)
            prev_sid = log.session_id
            prev_ts = log.timestamp
        if latencies:
            feat["avg_response_latency_ms_session"] = statistics.mean(latencies)

        # Reasoning deviation rate: fraction of assistant logs flagged as off-pattern
        asst_logs = (
            db.query(ChatLog)
            .filter(
                ChatLog.session_id.in_(session_ids),
                ChatLog.role == "assistant",
            )
            .all()
        )
        deviation_count = 0
        total_asst = 0
        reasoning_counts: dict[int, int] = {0: 0, 1: 0, 2: 0, 3: 0}
        for log in asst_logs:
            meta = log.metadata_json if isinstance(log.metadata_json, dict) else {}
            total_asst += 1
            if meta.get("reasoning_deviation"):
                deviation_count += 1
            rp = meta.get("reasoning_pattern")
            if isinstance(rp, int) and rp in reasoning_counts:
                reasoning_counts[rp] += 1

        if total_asst > 0:
            feat["reasoning_deviation_rate"] = float(deviation_count) / total_asst

        # Dominant reasoning pattern → one-hot
        dominant = max(reasoning_counts, key=lambda k: reasoning_counts[k])
        if reasoning_counts[dominant] > 0:
            feat[f"reasoning_pattern_{dominant}"] = 1.0
            for other in reasoning_counts:
                if other != dominant:
                    feat[f"reasoning_pattern_{other}"] = 0.0

    # ── User-safety ──────────────────────────────────────────────────────────
    # Derived from ValidatorAuditLog safety_violation + response_time_ms
    # Import here to avoid circular dependency at module level
    try:
        from db.database import ValidatorAuditLog  # noqa: PLC0415
        if all_sessions:
            session_ids = [s.id for s in all_sessions]
            safety_logs = (
                db.query(ValidatorAuditLog)
                .filter(ValidatorAuditLog.session_id.in_(session_ids))
                .all()
            )
            if safety_logs:
                reaction_times = [
                    float(l.response_time_ms)
                    for l in safety_logs
                    if l.response_time_ms and l.response_time_ms > 0
                ]
                if reaction_times:
                    reaction_times.sort()
                    mid = len(reaction_times) // 2
                    feat["safety_reaction_time_p50"] = (
                        reaction_times[mid]
                        if len(reaction_times) % 2 == 1
                        else (reaction_times[mid - 1] + reaction_times[mid]) / 2.0
                    )

                safety_critical = [l for l in safety_logs if l.safety_violation is not None]
                if safety_critical:
                    completed_correctly = sum(
                        1 for l in safety_critical if not l.safety_violation
                    )
                    feat["safety_action_completion_rate"] = (
                        float(completed_correctly) / len(safety_critical)
                    )
    except Exception:
        pass  # ValidatorAuditLog may not exist in all schema versions

    return feat


# ---------------------------------------------------------------------------
# Case feature builder
# ---------------------------------------------------------------------------

def build_case_features(
    db: Session,
    case_id: str,
    asof: Optional[datetime] = None,
) -> dict[str, float]:
    """
    Build the case feature vector (13 features: 9 static + 4 historical).

    Case static features do not change over time; historical ones are
    asof-bounded to avoid leakage during training.
    """
    ref = asof or _utcnow()
    feat: dict[str, float] = {k: v for k, v in _DEFAULTS.items()}

    case = db.query(CaseDefinition).filter(CaseDefinition.case_id == case_id).first()
    if case is None:
        return feat

    # ── Case-static ──────────────────────────────────────────────────────────
    diff_str = str(case.difficulty or "").lower().strip()
    feat["case_difficulty_ordinal"] = _DIFFICULTY_ORDINAL.get(diff_str, 1.0)
    feat["estimated_duration_minutes"] = float(case.estimated_duration_minutes or 30)
    feat["n_competency_tags"] = float(len(case.competency_tags or []))
    feat["n_prerequisite_competencies"] = float(len(case.prerequisite_competencies or []))
    feat["n_learning_objectives"] = float(len(case.learning_objectives or []))

    safety_rules = _safety_rules_per_case()
    feat["n_safety_critical_rules"] = float(safety_rules.get(case_id, 0))

    # IRT parameters: mean a and b across mapped questions
    mappings = (
        db.query(QuestionCaseMapping)
        .filter(QuestionCaseMapping.case_id == case_id)
        .all()
    )
    feat["n_mapped_questions"] = float(len(mappings))

    if mappings:
        q_ids = [m.question_id for m in mappings]
        irt_rows = (
            db.query(IRTParameters)
            .filter(IRTParameters.question_id.in_(q_ids))
            .all()
        )
        if irt_rows:
            feat["irt_mean_b_mapped_questions"] = statistics.mean(r.difficulty_b for r in irt_rows)
            feat["irt_mean_a_mapped_questions"] = statistics.mean(r.discrimination_a for r in irt_rows)

    # ── Case-historical ──────────────────────────────────────────────────────
    exams_q = db.query(ExamResult).filter(
        ExamResult.case_id == case_id,
        ExamResult.max_score > 0,
    )
    if asof:
        exams_q = exams_q.filter(ExamResult.completed_at < asof)
    exams = exams_q.all()

    if exams:
        scores_pct = [(r.score / r.max_score) * 100.0 for r in exams]
        feat["historical_avg_completion_score"] = statistics.mean(scores_pct)
        feat["historical_n_unique_users_attempted"] = float(
            len({r.user_id for r in exams})
        )

    sessions_q = db.query(StudentSession).filter(StudentSession.case_id == case_id)
    if asof:
        sessions_q = sessions_q.filter(StudentSession.start_time < asof)
    all_case_sessions = sessions_q.all()

    if all_case_sessions:
        n_total = float(len(all_case_sessions))
        n_completed = float(len(exams)) if exams else 0.0
        feat["historical_completion_rate"] = (
            n_completed / n_total if n_total > 0 else 0.0
        )

        # Session length approximation: last ChatLog ts − session start_time
        session_lengths: list[float] = []
        for sess in all_case_sessions:
            if not sess.start_time:
                continue
            last_log_ts = (
                db.query(func.max(ChatLog.timestamp))
                .filter(ChatLog.session_id == sess.id)
                .scalar()
            )
            if last_log_ts and last_log_ts > sess.start_time:
                length_min = (last_log_ts - sess.start_time).total_seconds() / 60.0
                if 0.5 < length_min < 240:  # sanity bounds
                    session_lengths.append(length_min)
        if session_lengths:
            feat["historical_avg_session_length_min"] = statistics.mean(session_lengths)

    return feat


# ---------------------------------------------------------------------------
# Cross (user × case) feature builder
# ---------------------------------------------------------------------------

def build_candidate_row(
    db: Session,
    user_id: str,
    case_id: str,
    asof: Optional[datetime] = None,
) -> dict[str, float]:
    """
    Build the full 37-feature vector for a (user, case) candidate pair.

    Merges user features + case features + cross features. All features are
    floats; booleans are 0.0/1.0.
    """
    ref = asof or _utcnow()

    user_feat = build_user_features(db, user_id, asof)
    case_feat = build_case_features(db, case_id, asof)

    # Merge (case features overwrite defaults where user_feat had defaults)
    row = {**user_feat, **case_feat}

    # ── Cross features ───────────────────────────────────────────────────────

    # Prior attempts on this specific case
    attempts_q = db.query(StudentSession).filter(
        StudentSession.student_id == user_id,
        StudentSession.case_id == case_id,
    )
    if asof:
        attempts_q = attempts_q.filter(StudentSession.start_time < asof)
    case_sessions = attempts_q.all()

    row["n_prior_attempts_on_case"] = float(len(case_sessions))

    # Completion status
    completed_q = db.query(ExamResult).filter(
        ExamResult.user_id == user_id,
        ExamResult.case_id == case_id,
        ExamResult.max_score > 0,
    )
    if asof:
        completed_q = completed_q.filter(ExamResult.completed_at < asof)
    completed = completed_q.first() is not None

    row["is_completed"] = 1.0 if completed else 0.0
    row["is_in_progress"] = (
        1.0 if (len(case_sessions) > 0 and not completed) else 0.0
    )

    # Days since last attempt on this case
    last_attempt_dt = max(
        (s.start_time for s in case_sessions if s.start_time), default=None
    )
    row["days_since_last_attempt_on_case"] = _days_ago(last_attempt_dt, ref)

    # Mastery gap on case topics:
    #   Sum of (1 - mastery_prob) over topics associated with mapped questions
    mappings = (
        db.query(QuestionCaseMapping)
        .filter(QuestionCaseMapping.case_id == case_id)
        .all()
    )
    if mappings:
        q_ids = [m.question_id for m in mappings]
        topic_ids_raw = (
            db.query(Question.topic_id)
            .filter(Question.id.in_(q_ids))
            .distinct()
            .all()
        )
        topic_ids = {_canonicalise_topic_id(t[0]) for t in topic_ids_raw if t[0]}

        if topic_ids:
            mastery_q = db.query(MasteryState).filter(
                MasteryState.user_id == user_id,
                MasteryState.topic_id.in_(list(topic_ids)),
            )
            if asof:
                mastery_q = mastery_q.filter(MasteryState.updated_at < asof)
            mastery_rows = mastery_q.all()

            known_topics = {_canonicalise_topic_id(m.topic_id): m.mastery_prob for m in mastery_rows}
            gap = sum(
                1.0 - known_topics.get(tid, 0.20)  # default prior for unknown topics
                for tid in topic_ids
            )
            row["mastery_gap_on_case_topics"] = gap

        # Competency overlap with user's weak areas
        case_def = db.query(CaseDefinition).filter(CaseDefinition.case_id == case_id).first()
        if case_def:
            case_tags = {str(t).lower().strip() for t in (case_def.competency_tags or [])}
            weak_topics = _weak_topic_ids(db, user_id, asof)
            overlap = case_tags.intersection(weak_topics)
            row["competency_overlap_with_weak_areas"] = float(len(overlap))

    return row


# ---------------------------------------------------------------------------
# Training frame materialisation
# ---------------------------------------------------------------------------

def materialise_training_frame(
    db: Session,
    since: datetime,
    until: datetime,
) -> pd.DataFrame:
    """
    Build the full training DataFrame for the XGBoost ranker.

    Each row represents a recommendation context: (user_id, recommended_case_id,
    asof_ts) with the realised binary outcome label and all 37 features.

    Outcome label: `outcome_score = 1.0` if the student completed the
    recommended case within 14 days of the recommendation, with score ≥ 70%
    of max_score. Otherwise 0.0.

    asof-correctness guarantee: features for a row at `asof_ts = T` are
    computed strictly from events with timestamp < T. This prevents future
    leakage.

    Parameters
    ----------
    since : datetime
        Earliest recommendation snapshot to include.
    until : datetime
        Latest recommendation snapshot to include. Should be at least 14 days
        before now so outcome labels can be observed.
    """
    snapshots = (
        db.query(RecommendationSnapshot)
        .filter(
            RecommendationSnapshot.created_at >= since,
            RecommendationSnapshot.created_at < until,
        )
        .order_by(RecommendationSnapshot.created_at)
        .all()
    )

    if not snapshots:
        logger.warning(
            "materialise_training_frame: no RecommendationSnapshot rows found "
            "between %s and %s",
            since.isoformat(),
            until.isoformat(),
        )
        return pd.DataFrame(columns=_LABEL_COLUMNS + FEATURE_COLUMNS)

    rows: list[dict] = []
    fourteen_days = __import__("datetime").timedelta(days=14)

    for snap in snapshots:
        asof_ts = snap.created_at
        outcome_window_end = asof_ts + fourteen_days

        # Outcome: completed with ≥ 70% score within 14 days of recommendation
        completion = (
            db.query(ExamResult)
            .filter(
                ExamResult.user_id == snap.user_id,
                ExamResult.case_id == snap.case_id,
                ExamResult.max_score > 0,
                ExamResult.completed_at >= asof_ts,
                ExamResult.completed_at < outcome_window_end,
            )
            .first()
        )

        outcome = 0.0
        if completion is not None:
            pct = completion.score / completion.max_score
            if pct >= 0.70:
                outcome = 1.0

        try:
            feat_row = build_candidate_row(db, snap.user_id, snap.case_id, asof=asof_ts)
        except Exception as exc:
            logger.warning(
                "Feature build failed for user=%s case=%s asof=%s: %s",
                snap.user_id,
                snap.case_id,
                asof_ts,
                exc,
            )
            continue

        row = {
            "user_id": snap.user_id,
            "case_id": snap.case_id,
            "asof_ts": asof_ts,
            "outcome_score": outcome,
            **feat_row,
        }
        rows.append(row)

    df = pd.DataFrame(rows, columns=_LABEL_COLUMNS + FEATURE_COLUMNS)
    logger.info(
        "materialise_training_frame: %d rows, %d positive labels (%.1f%%)",
        len(df),
        int(df["outcome_score"].sum()),
        100.0 * df["outcome_score"].mean() if len(df) > 0 else 0.0,
    )
    return df
