"""
Outcome Correlation Service — Sprint 14B S14B-4
===============================================
Computes Pearson correlation between theory performance (quiz/composite) and
clinical performance (case simulation scores) at student and cohort level.

This is direct construct-validity evidence: a significant positive correlation
between quiz theory scores and case performance supports the claim that the
platform measures a unified clinical competency construct.

Usage
-----
from app.services.outcome_correlation_service import build_outcome_correlation

result = build_outcome_correlation(db=db_session)
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from db.database import (
    ExamResult,
    GradingStatus,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
    User,
    UserRole,
)


def _pearson(xs: list[float], ys: list[float]) -> Optional[float]:
    n = len(xs)
    if n < 3:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x < 1e-9 or den_y < 1e-9:
        return None
    return round(num / (den_x * den_y), 4)


def _quiz_pct(user_id: str, db: Session) -> Optional[float]:
    """Return overall quiz score % (MCQ + OE published) for user_id, or None."""
    rows = (
        db.query(QuizAnswer, Question)
        .join(QuizAttempt, QuizAnswer.attempt_id == QuizAttempt.id)
        .join(Question, QuizAnswer.question_id == Question.id)
        .filter(
            QuizAttempt.user_id == user_id,
            QuizAnswer.grading_status.in_([GradingStatus.GRADED, GradingStatus.PUBLISHED]),
        )
        .all()
    )
    if not rows:
        return None
    earned = 0
    max_possible = 0
    for answer, question in rows:
        score = answer.instructor_score if answer.instructor_score is not None else answer.auto_score
        if score is None:
            continue
        earned += score
        max_possible += question.max_score
    if max_possible == 0:
        return None
    return round(earned / max_possible * 100.0, 2)


def _case_pct(user_id: str, db: Session) -> Optional[float]:
    """Return overall case simulation score % for user_id, or None."""
    rows = (
        db.query(ExamResult)
        .filter(
            ExamResult.user_id == user_id,
            ExamResult.max_score > 0,
            ExamResult.case_id != "quiz_global",
        )
        .all()
    )
    if not rows:
        return None
    earned = sum(r.score for r in rows)
    max_possible = sum(r.max_score for r in rows)
    return round(earned / max_possible * 100.0, 2) if max_possible > 0 else None


def build_outcome_correlation(db: Session) -> dict:
    """
    Compute quiz↔case correlation for the full cohort.

    Returns
    -------
    {
      "pearson_r": float | None,
      "n_paired": int,
      "students": [
        {
          "user_id": str,
          "display_name": str,
          "quiz_pct": float | None,
          "case_pct": float | None
        },
        ...
      ],
      "interpretation": str,
      "computed_at": str
    }
    """
    students = (
        db.query(User)
        .filter(User.role == UserRole.STUDENT, User.is_archived.is_(False))
        .order_by(User.display_name)
        .all()
    )

    student_rows: list[dict] = []
    quiz_vals: list[float] = []
    case_vals: list[float] = []

    for student in students:
        sid = student.user_id
        qpct = _quiz_pct(sid, db)
        cpct = _case_pct(sid, db)
        student_rows.append({
            "user_id": sid,
            "display_name": student.display_name,
            "quiz_pct": qpct,
            "case_pct": cpct,
        })
        if qpct is not None and cpct is not None:
            quiz_vals.append(qpct)
            case_vals.append(cpct)

    r = _pearson(quiz_vals, case_vals)
    n_paired = len(quiz_vals)

    if r is None:
        interpretation = "Yeterli eşleştirilmiş veri yok (en az 3 öğrenci gerekli)."
    elif r >= 0.7:
        interpretation = f"Güçlü pozitif korelasyon (r={r:.2f}): teori başarısı klinik performansı güçlü biçimde yordamaktadır."
    elif r >= 0.4:
        interpretation = f"Orta pozitif korelasyon (r={r:.2f}): teori ve klinik ölçümler arasında beklenen ilişki gözlemlenmektedir."
    elif r >= 0:
        interpretation = f"Zayıf pozitif korelasyon (r={r:.2f}): ilişki istatistiksel olarak anlamlı olmayabilir."
    else:
        interpretation = f"Negatif korelasyon (r={r:.2f}): beklenmedik yön — daha fazla veri gerekebilir."

    return {
        "pearson_r": r,
        "n_paired": n_paired,
        "students": student_rows,
        "interpretation": interpretation,
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }
