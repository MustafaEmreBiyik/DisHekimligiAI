"""
Quiz Router
===========
Serves MCQ and Open-Ended questions. S8B implementation.
Answer keys and protected fields are strictly omitted.
"""

from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import json
import logging
from pathlib import Path
from datetime import datetime
import re
import unicodedata
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_context, AuthenticatedUser, get_db, require_roles
from db.database import ExamResult, UserRole, Question, QuestionType, QuizAttempt, QuizAnswer, GradingStatus

logger = logging.getLogger(__name__)

router = APIRouter()

QUESTIONS_FILE = Path(__file__).resolve().parents[3] / "data" / "question_bank" / "mcq_questions.json"

TOPIC_MAP = {
    "oral_pathology": "Oral Patoloji",
    "infectious_diseases": "Enfeksiyöz Hastalıklar",
    "traumatic": "Travmatik Lezyonlar",
}


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class StudentQuestion(BaseModel):
    """Student-safe schema: no answer keys or protected fields."""
    id: str
    topic: str
    question: str
    options: List[str]
    question_type: str = "MCQ"
    difficulty: str = "medium"
    bloom_level: str = "apply"


class SubmitRequest(BaseModel):
    answers: Dict[str, str]   # {question_id: selected_option or free_text}


class QuestionFeedback(BaseModel):
    id: str
    topic: str
    question: str
    question_type: str = "MCQ"
    selected_option: Optional[str] = None
    is_correct: Optional[bool] = None
    feedback: Optional[str] = None
    grading_status: str = "PUBLISHED"
    instructor_score: Optional[int] = None
    instructor_feedback: Optional[str] = None


class SubmitResponse(BaseModel):
    attempt_id: int
    score: Optional[int] = None
    total: int
    percentage: Optional[int] = None
    overall_status: str = "PUBLISHED"
    results: List[QuestionFeedback]


class GradingQueueItem(BaseModel):
    answer_id: int
    attempt_id: int
    question_id: str
    question_text: str
    student_response: str
    rubric_guide: Optional[str] = None
    model_answer_outline: Optional[str] = None
    max_score: int
    submitted_at: Optional[str] = None


class GradeSubmission(BaseModel):
    instructor_score: int
    instructor_feedback: str
    publish: bool


class InstructorQuestionCreateRequest(BaseModel):
    question_type: str = QuestionType.OPEN_ENDED.value
    question_id: Optional[str] = None
    question_text: str
    topic_id: str
    competency_areas: List[str] = Field(default_factory=list)
    bloom_level: str
    difficulty: str
    safety_category: str
    rubric_guide: Optional[str] = None
    model_answer_outline: Optional[str] = None
    instructor_explanation: Optional[str] = None
    options: List[str] = Field(default_factory=list)
    correct_option: Optional[str] = None
    max_score: int = 10
    is_active: bool = True


class InstructorQuestionSummary(BaseModel):
    question_id: str
    question_type: str
    question_text: str
    topic_id: str
    competency_areas: List[str] = Field(default_factory=list)
    bloom_level: str
    difficulty: str
    safety_category: str
    rubric_guide: Optional[str] = None
    model_answer_outline: Optional[str] = None
    instructor_explanation: Optional[str] = None
    options: List[str] = Field(default_factory=list)
    correct_option: Optional[str] = None
    max_score: int
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _safe_feedback(*, is_correct: bool) -> str:
    if is_correct:
        return "Dogru cevap. Benzer vakalarda ayni klinik yaklasimi surdurun."
    return "Bu yanit dogru degil. Konuyu yeniden gozden gecirip tekrar deneyin."


def _normalize_text(value: Optional[str]) -> str:
    return (value or "").strip()


def _normalize_str_list(values: Optional[List[str]]) -> List[str]:
    normalized: List[str] = []
    for value in values or []:
        cleaned = _normalize_text(value)
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    return slug or "question"


def _question_to_summary(question: Question) -> InstructorQuestionSummary:
    return InstructorQuestionSummary(
        question_id=question.question_id,
        question_type=question.question_type.value,
        question_text=question.question_text,
        topic_id=question.topic_id,
        competency_areas=question.competency_areas or [],
        bloom_level=question.bloom_level,
        difficulty=question.difficulty,
        safety_category=question.safety_category,
        rubric_guide=question.rubric_guide,
        model_answer_outline=question.model_answer_outline,
        instructor_explanation=question.instructor_explanation,
        options=question.options_json or [],
        correct_option=question.correct_option,
        max_score=question.max_score,
        is_active=question.is_active,
        created_at=question.created_at.isoformat() if question.created_at else None,
        updated_at=question.updated_at.isoformat() if question.updated_at else None,
    )


def _generate_question_id(db: Session, question_type: QuestionType, topic_id: str, question_text: str) -> str:
    topic_slug = _slugify(topic_id)[:24]
    question_slug = _slugify(question_text)[:36]
    type_prefix = "oe" if question_type == QuestionType.OPEN_ENDED else "mcq"
    base_id = f"{type_prefix}-{topic_slug}-{question_slug}".strip("-")

    candidate = base_id
    suffix = 2
    while db.query(Question).filter(Question.question_id == candidate).first():
        candidate = f"{base_id}-{suffix}"
        suffix += 1

    return candidate


def _normalize_question_type(value: Optional[str]) -> QuestionType:
    normalized = _normalize_text(value).upper()
    if normalized == QuestionType.MCQ.value:
        return QuestionType.MCQ
    if normalized == QuestionType.OPEN_ENDED.value:
        return QuestionType.OPEN_ENDED
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Question type must be MCQ or OPEN_ENDED",
    )


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_full_questions() -> List[dict]:
    """Load legacy full question data."""
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


# ── Student Endpoints ─────────────────────────────────────────────────────────

@router.get("/questions", response_model=List[StudentQuestion], status_code=status.HTTP_200_OK)
def get_questions(topic: Optional[str] = None, current_user: AuthenticatedUser = Depends(require_roles(UserRole.STUDENT)), db: Session = Depends(get_db)):
    db_questions = db.query(Question).filter(Question.is_active == True)
    if topic and topic != "Tümü":
        db_questions = db_questions.filter(Question.topic_id == topic)
    
    questions_list = db_questions.all()
    if questions_list:
        return [
            StudentQuestion(
                id=q.question_id,
                topic=q.topic_id,
                question=q.question_text,
                options=q.options_json if q.options_json else [],
                question_type=q.question_type.value,
                difficulty=q.difficulty,
                bloom_level=q.bloom_level
            )
            for q in questions_list
        ]
        
    # Legacy fallback
    legacy = _load_full_questions()
    if topic and topic != "Tümü":
        legacy = [q for q in legacy if q["topic"] == topic]
        
    return [
        StudentQuestion(
            id=q["id"],
            topic=q["topic"],
            question=q["question"],
            options=q["options"]
        )
        for q in legacy
    ]


@router.post("/submit", response_model=SubmitResponse, status_code=status.HTTP_200_OK)
def submit_answers(body: SubmitRequest, current_user: AuthenticatedUser = Depends(require_roles(UserRole.STUDENT)), db: Session = Depends(get_db)):
    db_questions = db.query(Question).filter(Question.question_id.in_(body.answers.keys())).all()
    
    # LEGACY PATH
    if not db_questions:
        question_map = {q["id"]: q for q in _load_full_questions()}
        results: List[QuestionFeedback] = []
        correct_count = 0

        for qid, selected in body.answers.items():
            if qid not in question_map: continue
            q = question_map[qid]
            is_correct = selected == q["correct_option"]
            if is_correct: correct_count += 1
            
            results.append(QuestionFeedback(
                id=q["id"],
                topic=q["topic"],
                question=q["question"],
                selected_option=selected,
                is_correct=is_correct,
                feedback=_safe_feedback(is_correct=is_correct)
            ))
            
        total = len(results)
        percentage = round((correct_count / total) * 100) if total > 0 else 0
        
        attempt = ExamResult(
            user_id=current_user.user_id,
            case_id="quiz_global",
            score=correct_count,
            max_score=total,
            details_json=json.dumps({"results": [r.model_dump() for r in results], "percentage": percentage}, ensure_ascii=False)
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        
        return SubmitResponse(
            attempt_id=attempt.id,
            score=correct_count,
            total=total,
            percentage=percentage,
            overall_status="PUBLISHED",
            results=results
        )
        
    # S8B PATH
    q_map = {q.question_id: q for q in db_questions}
    attempt = QuizAttempt(user_id=current_user.user_id, total_score=0, max_score=0)
    db.add(attempt)
    db.flush()
    
    results = []
    total_score = 0
    total_max = 0
    has_pending = False
    
    for qid, selected in body.answers.items():
        if qid not in q_map: continue
        q = q_map[qid]
        
        total_max += q.max_score
        answer = QuizAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            student_response_text=selected
        )
        
        if q.question_type == QuestionType.MCQ:
            is_correct = selected == q.correct_option
            earned = q.max_score if is_correct else 0
            answer.auto_score = earned
            answer.grading_status = GradingStatus.PUBLISHED
            total_score += earned
            
            results.append(QuestionFeedback(
                id=q.question_id,
                topic=q.topic_id,
                question=q.question_text,
                question_type=q.question_type.value,
                selected_option=selected,
                is_correct=is_correct,
                feedback=_safe_feedback(is_correct=is_correct),
                grading_status=GradingStatus.PUBLISHED.value
            ))
        else:
            answer.grading_status = GradingStatus.PENDING
            has_pending = True
            
            results.append(QuestionFeedback(
                id=q.question_id,
                topic=q.topic_id,
                question=q.question_text,
                question_type=q.question_type.value,
                selected_option=selected,
                is_correct=None,
                feedback=None,
                grading_status=GradingStatus.PENDING.value
            ))
            
        db.add(answer)
        
    if not has_pending:
        attempt.total_score = total_score
        attempt.max_score = total_max
        attempt.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(attempt)
        perc = round((total_score / total_max) * 100) if total_max > 0 else 0
        return SubmitResponse(
            attempt_id=attempt.id,
            score=total_score,
            total=total_max,
            percentage=perc,
            overall_status="PUBLISHED",
            results=results
        )
    else:
        attempt.max_score = total_max
        db.commit()
        db.refresh(attempt)
        return SubmitResponse(
            attempt_id=attempt.id,
            score=None,
            total=total_max,
            percentage=None,
            overall_status="PENDING",
            results=results
        )


@router.get("/attempts/{attempt_id}", response_model=SubmitResponse, status_code=status.HTTP_200_OK)
def get_attempt(attempt_id: int, current_user: AuthenticatedUser = Depends(get_current_user_context), db: Session = Depends(get_db)):
    # Try S8B QuizAttempt first
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id).first()
    if attempt:
        if current_user.role == UserRole.STUDENT and attempt.user_id != current_user.user_id:
            raise _forbidden()
        if current_user.role not in {UserRole.STUDENT, UserRole.INSTRUCTOR, UserRole.ADMIN}:
            raise _forbidden()
            
        results = []
        has_pending = False
        
        for ans in attempt.answers:
            q = ans.question
            if ans.grading_status != GradingStatus.PUBLISHED:
                has_pending = True
                
            feedback_item = QuestionFeedback(
                id=q.question_id,
                topic=q.topic_id,
                question=q.question_text,
                question_type=q.question_type.value,
                selected_option=ans.student_response_text,
                is_correct=None if q.question_type == QuestionType.OPEN_ENDED else (ans.auto_score > 0 if ans.auto_score is not None else False),
                feedback=_safe_feedback(is_correct=(ans.auto_score > 0 if ans.auto_score is not None else False)) if q.question_type == QuestionType.MCQ else None,
                grading_status=ans.grading_status.value
            )
            
            if ans.grading_status == GradingStatus.PUBLISHED:
                feedback_item.instructor_score = ans.instructor_score
                feedback_item.instructor_feedback = ans.instructor_feedback
                
            results.append(feedback_item)
            
        if has_pending:
            return SubmitResponse(
                attempt_id=attempt.id,
                score=None,
                total=attempt.max_score,
                percentage=None,
                overall_status="PENDING",
                results=results
            )
        else:
            perc = round((attempt.total_score / attempt.max_score) * 100) if attempt.max_score > 0 else 0
            return SubmitResponse(
                attempt_id=attempt.id,
                score=attempt.total_score,
                total=attempt.max_score,
                percentage=perc,
                overall_status="PUBLISHED",
                results=results
            )

    # Fallback to Legacy ExamResult
    legacy = db.query(ExamResult).filter(ExamResult.id == attempt_id).first()
    if not legacy or legacy.case_id != "quiz_global":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz attempt not found")
        
    if current_user.role == UserRole.STUDENT and legacy.user_id != current_user.user_id:
        raise _forbidden()
    if current_user.role not in {UserRole.STUDENT, UserRole.INSTRUCTOR, UserRole.ADMIN}:
        raise _forbidden()
        
    payload = {}
    if legacy.details_json:
        try:
            payload = json.loads(legacy.details_json)
        except json.JSONDecodeError:
            pass
            
    raw_results = payload.get("results", []) if isinstance(payload, dict) else []
    safe_results = []
    if isinstance(raw_results, list):
        for item in raw_results:
            if isinstance(item, dict):
                try:
                    safe_results.append(
                        QuestionFeedback(
                            id=str(item.get("id", "")),
                            topic=str(item.get("topic", "")),
                            question=str(item.get("question", "")),
                            selected_option=item.get("selected_option"),
                            is_correct=bool(item.get("is_correct", False)),
                            feedback=str(item.get("feedback", "")),
                        )
                    )
                except Exception:
                    continue
                    
    total = int(legacy.max_score or 0)
    percentage = int(payload.get("percentage", round((legacy.score / total) * 100) if total > 0 else 0))
    
    return SubmitResponse(
        attempt_id=legacy.id,
        score=int(legacy.score or 0),
        total=total,
        percentage=percentage,
        overall_status="PUBLISHED",
        results=safe_results
    )


@router.get("/topics", status_code=status.HTTP_200_OK)
def get_topics(current_user: AuthenticatedUser = Depends(require_roles(UserRole.STUDENT)), db: Session = Depends(get_db)):
    db_topics = [r[0] for r in db.query(Question.topic_id).filter(Question.is_active == True).distinct().all()]
    if db_topics:
        return ["Tümü"] + sorted(db_topics)
        
    questions = _load_full_questions()
    topics = sorted(set(q["topic"] for q in questions))
    return ["Tümü"] + topics


# ── Instructor Endpoints ──────────────────────────────────────────────────────

@router.get("/instructor/grading_queue", response_model=List[GradingQueueItem], status_code=status.HTTP_200_OK)
def get_grading_queue(current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)), db: Session = Depends(get_db)):
    pending_answers = db.query(QuizAnswer).join(Question).filter(
        QuizAnswer.grading_status != GradingStatus.PUBLISHED,
        Question.question_type == QuestionType.OPEN_ENDED
    ).all()
    
    return [
        GradingQueueItem(
            answer_id=ans.id,
            attempt_id=ans.attempt_id,
            question_id=ans.question.question_id,
            question_text=ans.question.question_text,
            student_response=ans.student_response_text,
            rubric_guide=ans.question.rubric_guide,
            model_answer_outline=ans.question.model_answer_outline,
            max_score=ans.question.max_score,
            submitted_at=ans.attempt.created_at.isoformat() if ans.attempt else None
        )
        for ans in pending_answers
    ]

@router.post("/instructor/grade/{answer_id}", status_code=status.HTTP_200_OK)
def submit_grade(answer_id: int, payload: GradeSubmission, current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)), db: Session = Depends(get_db)):
    ans = db.query(QuizAnswer).filter(QuizAnswer.id == answer_id).first()
    if not ans:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found")
        
    ans.instructor_score = payload.instructor_score
    ans.instructor_feedback = payload.instructor_feedback
    ans.graded_by_id = current_user.user_id
    ans.graded_at = datetime.utcnow()
    
    if payload.publish:
        ans.grading_status = GradingStatus.PUBLISHED
    else:
        ans.grading_status = GradingStatus.GRADED
        
    db.commit()
    
    # Update Attempt Score if all answers are PUBLISHED
    attempt = ans.attempt
    if all(a.grading_status == GradingStatus.PUBLISHED for a in attempt.answers):
        total = sum((a.instructor_score or 0) + (a.auto_score or 0) for a in attempt.answers)
        attempt.total_score = total
        attempt.completed_at = datetime.utcnow()
        db.commit()
        
    return {"status": "success"}


@router.get(
    "/instructor/questions",
    response_model=List[InstructorQuestionSummary],
    status_code=status.HTTP_200_OK,
)
def get_instructor_open_ended_questions(
    topic: Optional[str] = None,
    question_type: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    query = db.query(Question)
    if topic:
        query = query.filter(Question.topic_id == topic)
    if question_type:
        query = query.filter(Question.question_type == _normalize_question_type(question_type))

    questions = query.order_by(Question.created_at.desc(), Question.id.desc()).all()
    return [_question_to_summary(question) for question in questions]


@router.post(
    "/instructor/questions",
    response_model=InstructorQuestionSummary,
    status_code=status.HTTP_201_CREATED,
)
def create_instructor_open_ended_question(
    payload: InstructorQuestionCreateRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    question_type = _normalize_question_type(payload.question_type)
    question_text = _normalize_text(payload.question_text)
    topic_id = _normalize_text(payload.topic_id)
    bloom_level = _normalize_text(payload.bloom_level)
    difficulty = _normalize_text(payload.difficulty)
    safety_category = _normalize_text(payload.safety_category)
    rubric_guide = _normalize_text(payload.rubric_guide)
    model_answer_outline = _normalize_text(payload.model_answer_outline)
    instructor_explanation = _normalize_text(payload.instructor_explanation)
    competency_areas = _normalize_str_list(payload.competency_areas)
    options = _normalize_str_list(payload.options)
    correct_option = _normalize_text(payload.correct_option)

    if not question_text:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Question text is required")
    if not topic_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Topic is required")
    if not bloom_level:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Bloom level is required")
    if not difficulty:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Difficulty is required")
    if not safety_category:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Safety category is required")
    if payload.max_score < 1 or payload.max_score > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Max score must be between 1 and 100")

    if question_type == QuestionType.OPEN_ENDED:
        if not rubric_guide:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Rubric guide is required")
        if not model_answer_outline:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Model answer outline is required")
        if options:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Open-ended questions cannot include options")
        if correct_option:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Open-ended questions cannot include a correct option")
    else:
        if len(options) < 3:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="MCQ questions require at least 3 options")
        if len(options) != len(set(options)):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="MCQ options must be unique")
        if not correct_option:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Correct option is required for MCQ questions")
        if correct_option not in options:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Correct option must match one of the provided options")

    requested_id = _normalize_text(payload.question_id)
    if requested_id and not re.fullmatch(r"[a-zA-Z0-9_-]+", requested_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question ID may contain only letters, numbers, hyphens, and underscores",
        )
    question_id = requested_id or _generate_question_id(db, question_type, topic_id, question_text)
    if db.query(Question).filter(Question.question_id == question_id).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Question ID already exists")

    question = Question(
        question_id=question_id,
        question_type=question_type,
        question_text=question_text,
        is_active=payload.is_active,
        topic_id=topic_id,
        competency_areas=competency_areas,
        bloom_level=bloom_level,
        difficulty=difficulty,
        safety_category=safety_category,
        options_json=options or None,
        correct_option=correct_option or None,
        instructor_explanation=instructor_explanation or None,
        rubric_guide=rubric_guide or None,
        model_answer_outline=model_answer_outline or None,
        max_score=payload.max_score,
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    return _question_to_summary(question)
