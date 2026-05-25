"""
Exam Schedules Router (T-8A, T-8B, T-8C)
==========================================
CRUD for scheduled exams, timed attempt creation, and inter-rater grading.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_context, AuthenticatedUser, get_db, require_roles
from db.database import (
    ExamSchedule, Question, QuizAttempt, QuizAnswer,
    GradingStatus, UserRole,
)

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ExamScheduleCreate(BaseModel):
    title: str = Field(..., min_length=1)
    question_ids: List[int]
    opens_at: str
    closes_at: str
    time_limit_minutes: Optional[int] = None


class ExamScheduleOut(BaseModel):
    id: int
    title: str
    question_ids: List[int]
    opens_at: str
    closes_at: str
    time_limit_minutes: Optional[int]
    created_by: str
    is_active: bool


class ExamStartResponse(BaseModel):
    attempt_id: int
    question_count: int
    time_limit_expires_at: Optional[str] = None


class SecondaryGradePayload(BaseModel):
    score: float
    feedback: Optional[str] = None


class HighDeltaItem(BaseModel):
    answer_id: int
    question_text_short: str
    primary_score: float
    secondary_score: float
    delta: float


# ── T-8A: Instructor CRUD ────────────────────────────────────────────────────

@router.post(
    "/instructor/exam-schedules",
    response_model=ExamScheduleOut,
    status_code=status.HTTP_201_CREATED,
)
def create_exam_schedule(
    body: ExamScheduleCreate,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    schedule = ExamSchedule(
        title=body.title,
        question_ids=body.question_ids,
        opens_at=datetime.fromisoformat(body.opens_at),
        closes_at=datetime.fromisoformat(body.closes_at),
        time_limit_minutes=body.time_limit_minutes,
        created_by=current_user.user_id,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _schedule_to_out(schedule)


@router.get(
    "/instructor/exam-schedules",
    response_model=List[ExamScheduleOut],
)
def list_instructor_schedules(
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    rows = db.query(ExamSchedule).order_by(ExamSchedule.opens_at.desc()).all()
    return [_schedule_to_out(r) for r in rows]


@router.get(
    "/exam-schedules",
    response_model=List[ExamScheduleOut],
)
def list_open_schedules(
    current_user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    rows = (
        db.query(ExamSchedule)
        .filter(
            ExamSchedule.is_active == True,
            ExamSchedule.opens_at <= now,
            ExamSchedule.closes_at >= now,
        )
        .order_by(ExamSchedule.closes_at.asc())
        .all()
    )
    return [_schedule_to_out(r) for r in rows]


@router.get(
    "/exam-schedules/upcoming",
    response_model=List[ExamScheduleOut],
)
def list_upcoming_schedules(
    days: int = 7,
    current_user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    horizon = now + timedelta(days=days)
    rows = (
        db.query(ExamSchedule)
        .filter(
            ExamSchedule.is_active == True,
            ExamSchedule.opens_at <= horizon,
            ExamSchedule.closes_at >= now,
        )
        .order_by(ExamSchedule.opens_at.asc())
        .all()
    )
    return [_schedule_to_out(r) for r in rows]


# ── T-8B: Start timed exam ───────────────────────────────────────────────────

@router.post(
    "/exam-schedules/{schedule_id}/start",
    response_model=ExamStartResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_exam(
    schedule_id: int,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    schedule = db.query(ExamSchedule).filter(ExamSchedule.id == schedule_id).first()
    if not schedule or not schedule.is_active:
        raise HTTPException(status_code=404, detail="Exam not found")

    now = datetime.utcnow()
    if now < schedule.opens_at or now > schedule.closes_at:
        raise HTTPException(status_code=400, detail="Exam is not currently open")

    existing = (
        db.query(QuizAttempt)
        .filter(QuizAttempt.user_id == current_user.user_id, QuizAttempt.schedule_id == schedule_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="You already started this exam")

    expires_at = None
    if schedule.time_limit_minutes:
        expires_at = now + timedelta(minutes=schedule.time_limit_minutes)

    questions = (
        db.query(Question)
        .filter(Question.id.in_(schedule.question_ids))
        .all()
    )
    max_score = sum(q.max_score for q in questions)

    attempt = QuizAttempt(
        user_id=current_user.user_id,
        schedule_id=schedule_id,
        max_score=max_score,
        time_limit_expires_at=expires_at,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return ExamStartResponse(
        attempt_id=attempt.id,
        question_count=len(questions),
        time_limit_expires_at=expires_at.isoformat() + "Z" if expires_at else None,
    )


# ── T-8C: Secondary grading (inter-rater) ────────────────────────────────────

@router.post("/instructor/answers/{answer_id}/secondary-grade", status_code=status.HTTP_200_OK)
def submit_secondary_grade(
    answer_id: int,
    payload: SecondaryGradePayload,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    ans = db.query(QuizAnswer).filter(QuizAnswer.id == answer_id).first()
    if not ans:
        raise HTTPException(status_code=404, detail="Answer not found")
    if ans.instructor_score is None:
        raise HTTPException(status_code=400, detail="Primary grade must be submitted first")
    if ans.graded_by_id == current_user.user_id:
        raise HTTPException(status_code=400, detail="Secondary grader must be different from primary")

    ans.secondary_instructor_score = payload.score
    ans.secondary_instructor_id = current_user.user_id
    ans.secondary_graded_at = datetime.utcnow()
    ans.inter_rater_delta = abs(float(ans.instructor_score) - payload.score)
    db.commit()

    return {
        "status": "ok",
        "delta": ans.inter_rater_delta,
    }


@router.get(
    "/instructor/high-delta-answers",
    response_model=List[HighDeltaItem],
)
def get_high_delta_answers(
    threshold: float = 2.0,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(QuizAnswer)
        .filter(
            QuizAnswer.inter_rater_delta != None,
            QuizAnswer.inter_rater_delta >= threshold,
        )
        .order_by(QuizAnswer.inter_rater_delta.desc())
        .limit(20)
        .all()
    )
    result = []
    for ans in rows:
        result.append(HighDeltaItem(
            answer_id=ans.id,
            question_text_short=(ans.question.question_text or "")[:80] if ans.question else "",
            primary_score=float(ans.instructor_score or 0),
            secondary_score=float(ans.secondary_instructor_score or 0),
            delta=ans.inter_rater_delta,
        ))
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _schedule_to_out(s: ExamSchedule) -> ExamScheduleOut:
    return ExamScheduleOut(
        id=s.id,
        title=s.title,
        question_ids=s.question_ids or [],
        opens_at=s.opens_at.isoformat() + "Z" if s.opens_at else "",
        closes_at=s.closes_at.isoformat() + "Z" if s.closes_at else "",
        time_limit_minutes=s.time_limit_minutes,
        created_by=s.created_by,
        is_active=s.is_active,
    )
