"""T05: Question-based personalised recommendation service.

Priority stack:
  1. SM-2 due items  (review_schedules.due_date <= now)
  2. Weak-topic IRT-matched questions  (MasteryState.mastery_prob < 0.70)
  3. Cold-start fallback  (medium-difficulty questions student hasn't tried)

No scipy/xgboost dependency — uses only SQLAlchemy models.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from db.database import (
    IRTParameters,
    MasteryState,
    Question,
    QuizAnswer,
    QuizAttempt,
    QuestionType,
    ReviewSchedule,
)

_MASTERY_THRESHOLD = 0.70
_MAX_RECOMMENDATIONS = 10
_COLD_START_LIMIT = 5


@dataclass
class RecommendedQuestion:
    question_id: str
    question_text: str
    question_type: str
    topic_id: str
    bloom_level: str
    difficulty: str
    max_score: int
    options_json: Optional[List[str]]
    reason: str
    reason_code: str   # "sm2_due" | "weak_topic_irt" | "weak_topic" | "cold_start"
    mastery_pct: Optional[int]  # rounded mastery_prob * 100; None for cold-start
    priority: int       # 1 = most urgent, ascending


def _estimate_theta(mastery_prob: float) -> float:
    """Map BKT mastery [0, 1] → IRT theta estimate in [-2, 2]."""
    return 4.0 * mastery_prob - 2.0


def _answered_question_pks(user_id: str, db: Session) -> set[int]:
    """Return Question.id (PK) values the student has ever submitted an answer for."""
    rows = (
        db.query(QuizAnswer.question_id)
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .filter(QuizAttempt.user_id == user_id)
        .distinct()
        .all()
    )
    return {r[0] for r in rows}


def _irt_sort_key(question_pk: int, irt_map: dict[int, IRTParameters], theta: float) -> float:
    """Sort key: smaller = better IRT match. Questions with no IRT get penalty 99."""
    if question_pk not in irt_map:
        return 99.0
    return abs(irt_map[question_pk].difficulty_b - theta)


def recommend_questions(
    user_id: str,
    db: Session,
    limit: int = _MAX_RECOMMENDATIONS,
) -> List[RecommendedQuestion]:
    results: List[RecommendedQuestion] = []
    seen_pks: set[int] = set()
    now = datetime.datetime.utcnow()

    # ── Pre-load IRT map (question PK → IRTParameters) ────────────────────────
    irt_rows = db.query(IRTParameters).all()
    irt_map: dict[int, IRTParameters] = {r.question_id: r for r in irt_rows}

    # ── Pre-load mastery states for this user ─────────────────────────────────
    mastery_rows = (
        db.query(MasteryState)
        .filter(MasteryState.user_id == user_id)
        .all()
    )
    mastery_by_topic: dict[str, float] = {
        m.topic_id: m.mastery_prob for m in mastery_rows
    }

    answered_pks = _answered_question_pks(user_id, db)

    # ── PRIORITY 1: SM-2 due items ────────────────────────────────────────────
    due_schedules = (
        db.query(ReviewSchedule)
        .filter(
            ReviewSchedule.user_id == user_id,
            ReviewSchedule.due_date <= now,
        )
        .order_by(ReviewSchedule.due_date.asc())
        .all()
    )
    for sched in due_schedules:
        if len(results) >= limit:
            break
        q = sched.question
        if q is None or not q.is_active or q.id in seen_pks:
            continue
        topic_mastery = mastery_by_topic.get(q.topic_id)
        pct = round(topic_mastery * 100) if topic_mastery is not None else None
        overdue_days = (now - sched.due_date).days
        if overdue_days > 0:
            reason = (
                f"Bu soru {overdue_days} gün önce tekrar edilmeliydi. "
                f"Aralıklı tekrar programınızda bekliyor."
            )
        else:
            reason = "Bu soru bugün aralıklı tekrar programınızda."
        results.append(RecommendedQuestion(
            question_id=q.question_id,
            question_text=q.question_text,
            question_type=q.question_type.value,
            topic_id=q.topic_id,
            bloom_level=q.bloom_level,
            difficulty=q.difficulty,
            max_score=q.max_score,
            options_json=q.options_json,
            reason=reason,
            reason_code="sm2_due",
            mastery_pct=pct,
            priority=1,
        ))
        seen_pks.add(q.id)

    # ── PRIORITY 2: Weak-topic IRT-matched questions ───────────────────────────
    weak_topics = [
        (topic_id, prob)
        for topic_id, prob in mastery_by_topic.items()
        if prob < _MASTERY_THRESHOLD
    ]
    # Sort weakest first
    weak_topics.sort(key=lambda x: x[1])

    for topic_id, mastery_prob in weak_topics:
        if len(results) >= limit:
            break
        theta = _estimate_theta(mastery_prob)

        # Fetch active questions for this weak topic
        candidates = (
            db.query(Question)
            .filter(
                Question.topic_id == topic_id,
                Question.is_active == True,
            )
            .all()
        )

        # Exclude already-seen (SM-2 already added them) and sort by IRT match
        candidates = [c for c in candidates if c.id not in seen_pks]
        candidates.sort(key=lambda c: _irt_sort_key(c.id, irt_map, theta))

        mastery_pct = round(mastery_prob * 100)
        not_yet_tried = [c for c in candidates if c.id not in answered_pks]
        already_tried = [c for c in candidates if c.id in answered_pks]

        # Prefer not-yet-tried for weak topics; fall back to tried if needed
        ordered = not_yet_tried + already_tried

        slots_remaining = limit - len(results)
        for q in ordered[:slots_remaining]:
            if q.id in seen_pks:
                continue
            if q.id in irt_map:
                reason = (
                    f"Bu konudaki ustalık düzeyiniz %{mastery_pct}. "
                    f"Zorluk seviyenize uygun bir soru seçildi."
                )
                reason_code = "weak_topic_irt"
            else:
                reason = (
                    f"Bu konudaki ustalık düzeyiniz %{mastery_pct}. "
                    f"Pratik yapmanız önerilir."
                )
                reason_code = "weak_topic"
            results.append(RecommendedQuestion(
                question_id=q.question_id,
                question_text=q.question_text,
                question_type=q.question_type.value,
                topic_id=q.topic_id,
                bloom_level=q.bloom_level,
                difficulty=q.difficulty,
                max_score=q.max_score,
                options_json=q.options_json,
                reason=reason,
                reason_code=reason_code,
                mastery_pct=mastery_pct,
                priority=2,
            ))
            seen_pks.add(q.id)

    # ── PRIORITY 3: Cold-start fallback ───────────────────────────────────────
    if not results:
        untried = (
            db.query(Question)
            .filter(
                Question.is_active == True,
                Question.difficulty == "medium",
                ~Question.id.in_(answered_pks) if answered_pks else True,
            )
            .limit(_COLD_START_LIMIT)
            .all()
        )
        for q in untried:
            if q.id in seen_pks:
                continue
            results.append(RecommendedQuestion(
                question_id=q.question_id,
                question_text=q.question_text,
                question_type=q.question_type.value,
                topic_id=q.topic_id,
                bloom_level=q.bloom_level,
                difficulty=q.difficulty,
                max_score=q.max_score,
                options_json=q.options_json,
                reason="Henüz yeterli veri yok. Başlamak için orta zorlukta sorular seçildi.",
                reason_code="cold_start",
                mastery_pct=None,
                priority=3,
            ))
            seen_pks.add(q.id)

    return results[:limit]


def recommend_questions_control(
    user_id: str,
    db: Session,
    limit: int = _MAX_RECOMMENDATIONS,
) -> List[RecommendedQuestion]:
    """Control-group strategy: medium-difficulty untried questions, no personalisation.

    Used in the A/B test control arm so we can compare against the
    personalised BKT+IRT+SM-2 strategy in treatment groups.
    """
    answered_pks = _answered_question_pks(user_id, db)
    query = db.query(Question).filter(
        Question.is_active == True,
        Question.difficulty == "medium",
    )
    if answered_pks:
        query = query.filter(~Question.id.in_(answered_pks))
    untried = query.limit(limit).all()

    results: List[RecommendedQuestion] = []
    for q in untried:
        results.append(RecommendedQuestion(
            question_id=q.question_id,
            question_text=q.question_text,
            question_type=q.question_type.value,
            topic_id=q.topic_id,
            bloom_level=q.bloom_level,
            difficulty=q.difficulty,
            max_score=q.max_score,
            options_json=q.options_json,
            reason="Orta zorlukta, henüz denenmemiş sorular.",
            reason_code="cold_start",
            mastery_pct=None,
            priority=3,
        ))
    return results
