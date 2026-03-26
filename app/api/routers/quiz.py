"""
Quiz Router
===========
Serves MCQ (multiple-choice question) bank from data/mcq_questions.json.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List, Optional
import json
import logging
from pathlib import Path

from app.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Path to the question bank relative to this file:
# routers/ -> api/ -> app/ -> dentai/ -> data/
QUESTIONS_FILE = Path(__file__).parent.parent.parent.parent / "data" / "mcq_questions.json"

# Mapping from JSON category keys to Turkish display names
TOPIC_MAP = {
    "oral_pathology": "Oral Patoloji",
    "infectious_diseases": "Enfeksiyöz Hastalıklar",
    "traumatic": "Travmatik Lezyonlar",
}


def load_questions() -> List[dict]:
    """Load and flatten questions from JSON file, adding a `topic` field."""
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


@router.get("/questions", status_code=status.HTTP_200_OK)
def get_questions(
    topic: Optional[str] = None,
    current_user: str = Depends(get_current_user),
):
    """
    Get all quiz questions (or filtered by topic).

    **Authentication Required:** Yes (Bearer token)

    Query Params:
        topic: Optional topic filter (e.g. "Oral Patoloji")

    Returns a flat list of questions each with:
        id, topic, question, options, correct_option, explanation
    """
    questions = load_questions()

    if topic and topic != "Tümü":
        questions = [q for q in questions if q["topic"] == topic]

    return questions


@router.get("/topics", status_code=status.HTTP_200_OK)
def get_topics(current_user: str = Depends(get_current_user)):
    """
    Get all available quiz topics.

    **Authentication Required:** Yes (Bearer token)
    """
    questions = load_questions()
    topics = sorted(set(q["topic"] for q in questions))
    return ["Tümü"] + topics
