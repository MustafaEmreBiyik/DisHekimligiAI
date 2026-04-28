"""
Quiz Router
===========
Serves MCQ (multiple-choice question) bank from data/mcq_questions.json.
Answer keys are never included in student-facing GET responses; grading is
performed server-side via POST /submit.
"""

from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_context, AuthenticatedUser, get_db, require_roles
from db.database import ExamResult, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

QUESTIONS_FILE = Path(__file__).parent.parent.parent.parent / "data" / "mcq_questions.json"

TOPIC_MAP = {
    "oral_pathology": "Oral Patoloji",
    "infectious_diseases": "Enfeksiyöz Hastalıklar",
    "traumatic": "Travmatik Lezyonlar",
}


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class StudentQuestion(BaseModel):
    """Student-safe schema: no answer keys."""
    id: str
    topic: str
    question: str
    options: List[str]


class SubmitRequest(BaseModel):
    answers: Dict[str, str]   # {question_id: selected_option}


class QuestionFeedback(BaseModel):
    id: str
    topic: str
    question: str
    selected_option: Optional[str]
    is_correct: bool
    feedback: str


class SubmitResponse(BaseModel):
    attempt_id: int
    score: int
    total: int
    percentage: int
    results: List[QuestionFeedback]


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _safe_feedback(*, is_correct: bool) -> str:
    if is_correct:
        return "Dogru cevap. Benzer vakalarda ayni klinik yaklasimi surdurun."
    return "Bu yanit dogru degil. Konuyu yeniden gozden gecirip tekrar deneyin."


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_full_questions() -> List[dict]:
    """Load full question data including answer keys (server-side only)."""
    if not QUESTIONS_FILE.exists():
        logger.warning(f"Questions file not found: {QUESTIONS_FILE}")
        return []

    try:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)

        questions = []
        for category_key, items in raw.items():
            topic_label = TOPIC_MAP.get(category_key, category_key.replace("_", " ").title())
            for item in items:
                questions.append({
                    "id": item.get("id", ""),
                    "topic": topic_label,
                    "question": item.get("question", ""),
                    "options": item.get("options", []),
                    "correct_option": item.get("correct_option", ""),
                    "explanation": item.get("explanation", ""),
                })

        return questions

    except Exception as e:
        logger.error(f"Failed to load questions: {e}")
        return []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/questions",
    response_model=List[StudentQuestion],
    status_code=status.HTTP_200_OK,
)
def get_questions(
    topic: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.STUDENT)),
):
    """
    Return quiz questions in student-safe format.

    **Authentication Required:** Yes (Bearer token)

    Response fields: id, topic, question, options.
    `correct_option` and `explanation` are never returned here.
    """
    questions = _load_full_questions()

    if topic and topic != "Tümü":
        questions = [q for q in questions if q["topic"] == topic]

    return [
        StudentQuestion(
            id=q["id"],
            topic=q["topic"],
            question=q["question"],
            options=q["options"],
        )
        for q in questions
    ]


@router.post(
    "/submit",
    response_model=SubmitResponse,
    status_code=status.HTTP_200_OK,
)
def submit_answers(
    body: SubmitRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """
    Grade submitted quiz answers server-side.

    **Authentication Required:** Yes (Bearer token)

    Accepts a map of {question_id: selected_option}, scores them against the
    server-side answer key, and returns student-safe feedback only.
    """
    question_map = {q["id"]: q for q in _load_full_questions()}
    results: List[QuestionFeedback] = []
    correct_count = 0

    for qid, selected in body.answers.items():
        if qid not in question_map:
            continue

        q = question_map[qid]
        is_correct = selected == q["correct_option"]
        if is_correct:
            correct_count += 1

        results.append(QuestionFeedback(
            id=q["id"],
            topic=q["topic"],
            question=q["question"],
            selected_option=selected,
            is_correct=is_correct,
            feedback=_safe_feedback(is_correct=is_correct),
        ))

    total = len(results)
    percentage = round((correct_count / total) * 100) if total > 0 else 0

    attempt = ExamResult(
        user_id=current_user.user_id,
        case_id="quiz_global",
        score=correct_count,
        max_score=total,
        details_json=json.dumps(
            {
                "results": [result.model_dump() for result in results],
                "percentage": percentage,
            },
            ensure_ascii=False,
        ),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return SubmitResponse(
        attempt_id=attempt.id,
        score=correct_count,
        total=total,
        percentage=percentage,
        results=results,
    )


@router.get(
    "/attempts/{attempt_id}",
    response_model=SubmitResponse,
    status_code=status.HTTP_200_OK,
)
def get_attempt(
    attempt_id: int,
    current_user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    """Return a previously graded quiz attempt with ownership-aware RBAC."""
    attempt = db.query(ExamResult).filter(ExamResult.id == attempt_id).first()
    if not attempt or attempt.case_id != "quiz_global":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz attempt not found")

    if current_user.role == UserRole.STUDENT and attempt.user_id != current_user.user_id:
        raise _forbidden()
    if current_user.role not in {UserRole.STUDENT, UserRole.INSTRUCTOR, UserRole.ADMIN}:
        raise _forbidden()

    payload = {}
    if attempt.details_json:
        try:
            payload = json.loads(attempt.details_json)
        except json.JSONDecodeError:
            payload = {}

    raw_results = payload.get("results", []) if isinstance(payload, dict) else []
    safe_results: List[QuestionFeedback] = []
    if isinstance(raw_results, list):
        for item in raw_results:
            if isinstance(item, dict):
                try:
                    safe_results.append(
                        QuestionFeedback(
                            id=str(item.get("id", "")),
                            topic=str(item.get("topic", "")),
                            question=str(item.get("question", "")),
                            selected_option=(
                                str(item.get("selected_option"))
                                if item.get("selected_option") is not None
                                else None
                            ),
                            is_correct=bool(item.get("is_correct", False)),
                            feedback=str(item.get("feedback", "")),
                        )
                    )
                except Exception:
                    continue

    total = int(attempt.max_score or 0)
    percentage = int(payload.get("percentage", round((attempt.score / total) * 100) if total > 0 else 0))

    return SubmitResponse(
        attempt_id=attempt.id,
        score=int(attempt.score or 0),
        total=total,
        percentage=percentage,
        results=safe_results,
    )


@router.get("/topics", status_code=status.HTTP_200_OK)
def get_topics(current_user: AuthenticatedUser = Depends(require_roles(UserRole.STUDENT))):
    """
    Return all available quiz topics.

    **Authentication Required:** Yes (Bearer token)
    """
    questions = _load_full_questions()
    topics = sorted(set(q["topic"] for q in questions))
    return ["Tümü"] + topics
