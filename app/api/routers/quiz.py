"""
Quiz Router
===========
Serves MCQ (multiple-choice question) bank from data/mcq_questions.json.
Answer keys are never included in student-facing GET responses; grading is
performed server-side via POST /submit.
"""

from fastapi import APIRouter, status, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
import json
import logging
from pathlib import Path

from app.api.deps import get_current_user_context, AuthenticatedUser

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


class QuestionResult(BaseModel):
    id: str
    topic: str
    question: str
    options: List[str]
    correct_option: str
    explanation: str
    selected_option: Optional[str]
    is_correct: bool


class SubmitResponse(BaseModel):
    score: int
    total: int
    percentage: int
    results: List[QuestionResult]


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
    current_user: AuthenticatedUser = Depends(get_current_user_context),
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
    current_user: AuthenticatedUser = Depends(get_current_user_context),
):
    """
    Grade submitted quiz answers server-side.

    **Authentication Required:** Yes (Bearer token)

    Accepts a map of {question_id: selected_option}, scores them against the
    answer key, and returns per-question results (including correct_option and
    explanation) only after submission.
    """
    question_map = {q["id"]: q for q in _load_full_questions()}
    graded_ids = set(body.answers.keys()) & question_map.keys()

    results: List[QuestionResult] = []
    correct_count = 0

    for qid in graded_ids:
        q = question_map[qid]
        selected = body.answers[qid]
        is_correct = selected == q["correct_option"]
        if is_correct:
            correct_count += 1

        results.append(QuestionResult(
            id=q["id"],
            topic=q["topic"],
            question=q["question"],
            options=q["options"],
            correct_option=q["correct_option"],
            explanation=q["explanation"],
            selected_option=selected,
            is_correct=is_correct,
        ))

    total = len(results)
    percentage = round((correct_count / total) * 100) if total > 0 else 0

    return SubmitResponse(
        score=correct_count,
        total=total,
        percentage=percentage,
        results=results,
    )


@router.get("/topics", status_code=status.HTTP_200_OK)
def get_topics(current_user: AuthenticatedUser = Depends(get_current_user_context)):
    """
    Return all available quiz topics.

    **Authentication Required:** Yes (Bearer token)
    """
    questions = _load_full_questions()
    topics = sorted(set(q["topic"] for q in questions))
    return ["Tümü"] + topics
