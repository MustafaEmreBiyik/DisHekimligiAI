"""
Chat Router
===========
Endpoints for student-AI chat interactions.
Reuses existing DentalEducationAgent from app/agent.py.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List
import os
import json
import logging
import datetime
import threading
from typing import Optional

from app.agent import DentalEducationAgent
from app.assessment_engine import AssessmentEngine
from app.scenario_manager import ScenarioManager
from app.api.deps import (
    AuthenticatedUser,
    get_current_user_context,
    require_roles,
)
from app.services.reasoning_classifier import ReasoningPatternClassifier
from db.database import (
    SessionLocal,
    StudentSession,
    ChatLog,
    UserRole,
    CoachHint,
    ValidatorAuditLog,
    CaseDefinition,
    QuestionCaseMapping,
    Question,
)

logger = logging.getLogger(__name__)

router = APIRouter()
sessions_router = APIRouter()
reasoning_classifier = ReasoningPatternClassifier()
scenario_manager = ScenarioManager()

# Per-API-key agent cache: supports key rotation without service restart.
_agent_cache: dict[str, DentalEducationAgent] = {}
_agent_lock = threading.Lock()


def _get_or_create_agent() -> Optional[DentalEducationAgent]:
    """Return a cached DentalEducationAgent, creating one per unique API key.

    Supports key rotation: when GEMINI_API_KEY changes, a fresh agent is built
    and cached under the new key without requiring a process restart.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.warning("GEMINI_API_KEY not configured — chat service unavailable")
        return None
    if api_key not in _agent_cache:
        with _agent_lock:
            if api_key not in _agent_cache:
                try:
                    _agent_cache[api_key] = DentalEducationAgent(
                        api_key=api_key,
                        model_name="models/gemini-2.5-flash-lite",
                    )
                    logger.info("DentalEducationAgent initialised (key rotation aware)")
                except Exception as exc:
                    logger.error("Failed to initialise DentalEducationAgent: %s", exc)
                    return None
    return _agent_cache.get(api_key)


# ==================== REQUEST/RESPONSE MODELS ====================

class ReinforcementQuestion(BaseModel):
    """Linked theory question surfaced when student fails a case action. S10-A."""
    question_id: str
    topic_id: str
    question_text: str


class ChatRequest(BaseModel):
    """
    Chat message request from student.
    Student ID is automatically extracted from JWT token.
    """
    message: str = Field(..., description="Student's raw action/message", example="Hastanın alerjilerini kontrol ediyorum")
    case_id: str = Field(..., description="Active case identifier", example="olp_001")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hastanın oral mukozasını muayene ediyorum",
                "case_id": "olp_001"
            }
        }


class ChatResponse(BaseModel):
    """
    Student-safe chat response payload.
    Hidden grader and metadata outputs are not exposed.
    """
    session_id: Optional[int] = Field(None, description="Database session ID for this chat session")
    ai_response: str = Field(..., description="Patient-facing response text")
    final_feedback: Optional[str] = Field(None, description="Response text to show the student")
    state_updates: Dict[str, Any] = Field(default_factory=dict, description="Safe state updates")
    revealed_findings: List[str] = Field(default_factory=list, description="Newly revealed findings")
    reinforcement_questions: List[ReinforcementQuestion] = Field(
        default_factory=list,
        description="Theory questions linked to this case, surfaced on failure (S10-A)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": 42,
                "ai_response": "Doctor, I have a burning sensation in my cheek.",
                "final_feedback": "Doctor, I have a burning sensation in my cheek.",
                "state_updates": {
                    "case_id": "olp_001",
                    "is_case_finished": False
                },
                "revealed_findings": ["reticular white striae"]
            }
        }


class CoachRequest(BaseModel):
    """Clinical coach prompt request bound to an existing session."""

    session_id: int = Field(..., description="Existing session ID", examples=[12])
    message: str = Field(..., description="Student question for clinical guidance")


class CoachResponse(BaseModel):
    """Coach hint response without diagnosis or scoring leakage."""

    hint_level: str
    content: str
    hint_used: bool
    session_hints_remaining: int


class SessionEvaluationItem(BaseModel):
    """Internal evaluation metadata for instructor/admin review."""

    log_id: int
    timestamp: Optional[str] = None
    interpreted_action: str = "unknown"
    score: float = 0.0
    assessment: Dict[str, Any] = Field(default_factory=dict)
    silent_evaluation: Dict[str, Any] = Field(default_factory=dict)
    reasoning_pattern: Optional[Dict[str, Any]] = None


class SessionEvaluationResponse(BaseModel):
    """Internal session-level evaluation response."""

    session_id: int
    student_id: str
    case_id: str
    current_score: float
    evaluations: List[SessionEvaluationItem]


# ==================== HELPER FUNCTIONS ====================

def get_or_create_session(db, student_id: str, case_id: str) -> StudentSession:
    """
    Get existing session or create a new one for student + case combination.
    Returns the most recent session for this student and case.
    """
    # Try to find existing session
    session = db.query(StudentSession).filter_by(
        student_id=student_id,
        case_id=case_id
    ).order_by(StudentSession.start_time.desc()).first()
    
    if session:
        logger.info(f"Found existing session {session.id} for student {student_id} on case {case_id}")
        return session
    
    case = scenario_manager.get_case(case_id, include_inactive=False)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start session. Case '{case_id}' is not active or does not exist."
        )

    # Create new session
    new_session = StudentSession(
        student_id=student_id,
        case_id=case_id,
        current_score=0.0,
        state_json="{}",
        start_time=datetime.datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    logger.info(f"Created new session {new_session.id} for student {student_id} on case {case_id}")
    return new_session


def build_reasoning_action_history(db, session_id: int) -> list[dict[str, Any]]:
    """
    Build ordered action history from assistant logs for reasoning classification.
    """
    logs = (
        db.query(ChatLog)
        .filter_by(session_id=session_id, role="assistant")
        .order_by(ChatLog.timestamp.asc(), ChatLog.id.asc())
        .all()
    )

    history: list[dict[str, Any]] = []
    for log in logs:
        metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
        interpreted_action = str(metadata.get("interpreted_action", "")).strip()
        if not interpreted_action or interpreted_action in {"general_chat", "error", "unknown"}:
            continue

        silent_eval = metadata.get("silent_evaluation", {})
        if not isinstance(silent_eval, dict):
            silent_eval = {}

        history.append(
            {
                "action": interpreted_action,
                "reasoning_deviation": bool(silent_eval.get("reasoning_deviation", False)),
                "reasoning_deviation_flags": int(silent_eval.get("reasoning_deviation_flags", 0) or 0),
            }
        )

    return history


def enforce_student_resource_access(
    *,
    current_user: AuthenticatedUser,
    target_student_id: str,
) -> None:
    """Allow students to access only their own resources; staff can access all."""
    if current_user.role == UserRole.STUDENT and current_user.user_id != target_student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


def build_student_state_updates(
    *,
    case_id: str,
    is_case_finished: bool,
) -> Dict[str, Any]:
    """Build safe, non-scoring state updates for student clients."""
    return {
        "case_id": case_id,
        "is_case_finished": is_case_finished,
    }


def _safe_load_state(state_json: Optional[str]) -> Dict[str, Any]:
    if not state_json:
        return {}
    try:
        payload = json.loads(state_json)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_case_metadata(db, case_id: str) -> Dict[str, Any]:
    case_meta = {
        "title": case_id,
        "category": "unknown",
        "difficulty": "intermediate",
        "final_diagnosis": None,
    }

    db_case = db.query(CaseDefinition).filter(CaseDefinition.case_id == case_id).first()
    if db_case:
        case_meta.update(
            {
                "title": db_case.title,
                "category": db_case.category,
                "difficulty": str(db_case.difficulty).lower(),
            }
        )
        return case_meta

    case = scenario_manager.get_case(case_id, include_inactive=True)
    if case:
        difficulty_raw = str(case.get("difficulty") or case.get("zorluk_seviyesi") or "").strip().lower()
        difficulty_map = {
            "kolay": "beginner",
            "orta": "intermediate",
            "zor": "advanced",
        }
        case_meta.update(
            {
                "title": str(case.get("title") or case.get("name") or case_id),
                "category": str(case.get("category") or case.get("Category") or "unknown"),
                "difficulty": difficulty_map.get(difficulty_raw, difficulty_raw or "intermediate"),
                "final_diagnosis": case.get("dogru_tani") or case.get("correct_diagnosis"),
            }
        )

    return case_meta


def _session_has_diagnosis_checkpoint(db, session: StudentSession) -> bool:
    state = _safe_load_state(session.state_json)
    if bool(state.get("is_finished") or state.get("is_case_finished")):
        return True

    assistant_logs = db.query(ChatLog).filter_by(session_id=session.id, role="assistant").all()
    for log in assistant_logs:
        metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
        interpreted_action = str(metadata.get("interpreted_action", "")).strip()
        if interpreted_action.startswith("diagnose_"):
            return True

    return False


def _build_action_history_for_coach(db, session_id: int) -> List[str]:
    assistant_logs = (
        db.query(ChatLog)
        .filter_by(session_id=session_id, role="assistant")
        .order_by(ChatLog.timestamp.asc(), ChatLog.id.asc())
        .all()
    )
    history: List[str] = []
    for log in assistant_logs:
        metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
        action = str(metadata.get("interpreted_action", "")).strip()
        if not action or action in {"general_chat", "error", "unknown"}:
            continue
        history.append(action)
    return history[-12:]


def _hint_level_for_usage(used_count: int) -> str:
    levels = ["light_nudge", "guided_hint", "reflective_feedback"]
    return levels[max(0, min(used_count, len(levels) - 1))]


def _default_coach_content(hint_level: str, revealed_findings: List[str]) -> str:
    if hint_level == "light_nudge":
        return "Hastanin sistemik gecmisi, ilaclari ve alerjileri tam sorguladigindan emin misin?"
    if hint_level == "guided_hint":
        return "Anamnez ve muayene bulgularini birlikte degerlendir; kritik risk faktorlerini eksiksiz dogrula."

    findings_note = ""
    if revealed_findings:
        findings_note = f"Acilan bulgular: {', '.join(revealed_findings[:3])}. "
    return findings_note + "Simdiye kadar yaptiklarini kisaca ozetleyip eksik kalan guvenlik adimlarini tamamla."


def _extract_coach_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return ""

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            candidate = payload.get("content") or payload.get("hint") or payload.get("explanatory_feedback")
            if isinstance(candidate, str):
                return candidate.strip()
    except Exception:
        pass

    return text


def _get_reinforcement_questions(db, case_id: str, limit: int = 2) -> List[ReinforcementQuestion]:
    """Return THEORY_SUPPORT mapped questions for this case. Used by S10-A."""
    try:
        mappings = (
            db.query(QuestionCaseMapping)
            .filter(
                QuestionCaseMapping.case_id == case_id,
                QuestionCaseMapping.mapping_type == "THEORY_SUPPORT",
                QuestionCaseMapping.review_status == "APPROVED",
            )
            .limit(limit)
            .all()
        )
        result = []
        for m in mappings:
            q = db.query(Question).filter(Question.id == m.question_id).first()
            if q and q.is_active:
                result.append(ReinforcementQuestion(
                    question_id=q.question_id,
                    topic_id=q.topic_id,
                    question_text=q.question_text,
                ))
        return result
    except Exception:
        return []


def _sanitize_coach_content(content: str, hint_level: str, case_meta: Dict[str, Any], revealed_findings: List[str]) -> str:
    cleaned = " ".join((content or "").split()).strip()
    if not cleaned:
        return _default_coach_content(hint_level, revealed_findings)

    lowered = cleaned.lower()
    blocked_tokens = [
        "diagnosis",
        "diagnose",
        "tani",
        "tanı",
        "score",
        "puan",
        "rule engine",
        "kural motoru",
        "is_critical_safety_rule",
    ]
    final_dx = str(case_meta.get("final_diagnosis") or "").strip().lower()
    if final_dx:
        blocked_tokens.append(final_dx)

    if any(token in lowered for token in blocked_tokens):
        return _default_coach_content(hint_level, revealed_findings)

    if len(cleaned) > 420:
        cleaned = cleaned[:420].rstrip() + "..."
    return cleaned


# ==================== ENDPOINTS ====================

@router.post("/send", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def send_chat_message(
    request: ChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user_context),
):
    """
    Process a student's chat message and return AI response.
    
    **Authentication Required:** Yes (Bearer token in Authorization header)
    
    This endpoint uses the Silent Evaluator Architecture and tracks interactions:
    1. Validates JWT token and extracts student_id
    2. Gets or creates a StudentSession for telemetry
    3. Logs user message to ChatLog
    4. Calls agent.process_student_input()
    5. MedGemma silently evaluates clinical accuracy
    6. Logs AI response with evaluation metadata to ChatLog
    7. Updates session score and commits to DB
    8. Returns patient response + hidden evaluation for analytics
    
    The student sees only `response_text`. The `evaluation` object is for
    backend analytics and should NOT be displayed to students.
    """
    agent = _get_or_create_agent()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable. GEMINI_API_KEY not configured."
        )

    db = SessionLocal()
    try:
        # STEP 1: Get or create session for this student + case
        session = get_or_create_session(db, current_user.user_id, request.case_id)

        # STEP 2: Log student's message to database
        user_log = ChatLog(
            session_id=session.id,
            role='user',
            content=request.message,
            metadata_json=None,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(user_log)

        # STEP 3: Process with AI agent
        result = agent.process_student_input(
            student_id=current_user.user_id,
            raw_action=request.message,
            case_id=request.case_id
        )
        
        # Extract key fields for Silent Evaluator response
        llm_interpretation = result.get("llm_interpretation", {})
        assessment = result.get("assessment", {})
        silent_eval = result.get("silent_evaluation", {})
        llm_safety = result.get("llm_safety", {}) if isinstance(result.get("llm_safety"), dict) else {}
        safety_events = result.get("safety_events", []) if isinstance(result.get("safety_events"), list) else []
        updated_state = result.get("updated_state", {})
        score = assessment.get("score", 0.0)
        
        # Response text is the patient's dialogue (from Gemini's explanatory feedback)
        response_text = result.get("final_feedback", "")
        final_feedback = response_text
        
        # Interpreted action from LLM
        interpreted_action = llm_interpretation.get("interpreted_action", "unknown")
        is_diagnosis_action = interpreted_action.startswith("diagnose_")
        
        # Current session score from updated state
        current_score = updated_state.get("current_score", session.current_score + score)
        
        # Consider diagnosis actions as case completion checkpoints.
        is_case_finished = updated_state.get("is_finished", False) or is_diagnosis_action

        reasoning_pattern = None
        if is_diagnosis_action:
            past_history = build_reasoning_action_history(db, session.id)
            current_history_item = {
                "action": interpreted_action,
                "reasoning_deviation": bool(silent_eval.get("reasoning_deviation", False)),
                "reasoning_deviation_flags": int(silent_eval.get("reasoning_deviation_flags", 0) or 0),
            }
            reasoning_pattern = reasoning_classifier.classify(
                session_id=session.id,
                action_history=[*past_history, current_history_item],
            )

        for event in safety_events:
            if not isinstance(event, dict):
                continue

            event_type = str(event.get("event_type") or "llm_safety_event")
            logger.warning(
                "LLM safety event logged for student=%s case=%s type=%s risk=%s",
                current_user.user_id,
                request.case_id,
                event_type,
                event.get("risk_level", "low"),
            )
            db.add(
                ChatLog(
                    session_id=session.id,
                    role="system_validator",
                    content=f"LLM safety event: {event_type}",
                    metadata_json={
                        "source": "llm_safety",
                        "event": event,
                    },
                    timestamp=datetime.datetime.utcnow(),
                )
            )

        # STEP 5: Log AI's response to database with metadata
        assistant_log = ChatLog(
            session_id=session.id,
            role='assistant',
            content=response_text,
            metadata_json={
                "score": score,
                "interpreted_action": interpreted_action,
                "clinical_intent": llm_interpretation.get("clinical_intent", ""),
                "priority": llm_interpretation.get("priority", ""),
                "assessment": assessment,
                "silent_evaluation": silent_eval,
                "llm_safety": llm_safety,
                "reasoning_pattern": reasoning_pattern,
            },
            timestamp=datetime.datetime.utcnow()
        )
        db.add(assistant_log)

        audit_meta = silent_eval.get("audit", {}) if isinstance(silent_eval, dict) else {}
        if not isinstance(audit_meta, dict):
            audit_meta = {}

        clinical_accuracy = silent_eval.get("clinical_accuracy") if isinstance(silent_eval, dict) else None
        if clinical_accuracy is not None:
            clinical_accuracy = str(clinical_accuracy).strip().lower()
            if clinical_accuracy not in {"high", "medium", "low"}:
                clinical_accuracy = None

        validator_audit = ValidatorAuditLog(
            session_id=session.id,
            action=str(interpreted_action or "unknown"),
            validator_used=str(audit_meta.get("validator_used") or "medgemma"),
            safety_violation=bool(silent_eval.get("safety_violation", False)),
            clinical_accuracy=clinical_accuracy,
            response_time_ms=int(audit_meta.get("response_time_ms") or 0),
            error_message=(
                str(audit_meta.get("error_message"))
                if audit_meta.get("error_message") is not None
                else None
            ),
            created_at=datetime.datetime.utcnow(),
        )
        db.add(validator_audit)
        
        # STEP 6: Update session score
        session.current_score = current_score
        
        # STEP 7: Commit all changes to database
        db.commit()
        
        logger.info(
            f"✅ Logged interaction for student {current_user.user_id} on case {request.case_id}. "
            f"Action Score: {score}, Total: {current_score}"
        )

        revealed_findings = updated_state.get("revealed_findings", [])
        if not isinstance(revealed_findings, list):
            revealed_findings = []

        safe_state_updates = build_student_state_updates(
            case_id=result.get("case_id", request.case_id),
            is_case_finished=is_case_finished,
        )

        # S10-A: Surface reinforcement questions on failed/penalised actions.
        reinforcement: List[ReinforcementQuestion] = []
        action_meaningful = interpreted_action not in {"general_chat", "error", "unknown", ""}
        action_failed = score < 0 or bool(silent_eval.get("reasoning_deviation", False))
        if action_meaningful and action_failed:
            reinforcement = _get_reinforcement_questions(db, request.case_id)

        # STEP 8: Return student-safe response payload
        return ChatResponse(
            session_id=session.id,
            ai_response=response_text,
            final_feedback=final_feedback,
            state_updates=safe_state_updates,
            revealed_findings=revealed_findings,
            reinforcement_questions=reinforcement,
        )
    finally:
        db.close()


@router.post("/coach", response_model=CoachResponse, status_code=status.HTTP_200_OK)
def coach_student(
    request: CoachRequest,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.STUDENT)),
):
    """Provide bounded coaching hints without diagnosis or scoring leakage."""
    db = SessionLocal()
    try:
        session = db.query(StudentSession).filter_by(id=request.session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {request.session_id} not found",
            )

        if session.student_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

        if _session_has_diagnosis_checkpoint(db, session):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session is already finished; coach is unavailable.",
            )

        used_hints = db.query(CoachHint).filter_by(
            session_id=session.id,
            user_id=current_user.user_id,
        ).count()
        if used_hints >= 3:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Hint limit exceeded for this session.",
            )

        hint_level = _hint_level_for_usage(used_hints)
        state = _safe_load_state(session.state_json)
        revealed_findings = state.get("revealed_findings", [])
        if not isinstance(revealed_findings, list):
            revealed_findings = []

        action_history = _build_action_history_for_coach(db, session.id)
        case_meta = _resolve_case_metadata(db, session.case_id)

        coach_prompt = f"""
You are DentAI Clinical Coach. Provide one short Turkish coaching hint.
HARD CONSTRAINTS:
- NEVER reveal final diagnosis.
- NEVER reveal or explain scoring logic.
- Keep hint focused on next safe step.

HINT LEVEL: {hint_level}
STUDENT MESSAGE: {request.message}
CASE CATEGORY: {case_meta.get('category')}
CASE DIFFICULTY: {case_meta.get('difficulty')}
REVEALED FINDINGS: {json.dumps(revealed_findings, ensure_ascii=False)}
ACTION HISTORY: {json.dumps(action_history, ensure_ascii=False)}
SESSION STATE: {json.dumps(state, ensure_ascii=False)}

Return plain Turkish text only.
""".strip()

        generated_content = ""
        _coach_agent = _get_or_create_agent()
        if _coach_agent and getattr(_coach_agent, "model", None):
            try:
                response = _coach_agent.model.generate_content(coach_prompt)
                generated_content = _extract_coach_text(getattr(response, "text", ""))
            except Exception as exc:
                logger.warning("Coach generation failed, fallback will be used: %s", exc)

        if not generated_content:
            generated_content = _default_coach_content(hint_level, revealed_findings)

        safe_content = _sanitize_coach_content(
            generated_content,
            hint_level,
            case_meta,
            revealed_findings,
        )

        db.add(
            CoachHint(
                session_id=session.id,
                user_id=current_user.user_id,
                hint_level=hint_level,
                content=safe_content,
                created_at=datetime.datetime.utcnow(),
            )
        )
        db.commit()

        hints_remaining = max(0, 3 - (used_hints + 1))
        return CoachResponse(
            hint_level=hint_level,
            content=safe_content,
            hint_used=True,
            session_hints_remaining=hints_remaining,
        )
    finally:
        db.close()


@router.get("/history/{student_id}/{case_id}", status_code=status.HTTP_200_OK)
def get_chat_history(
    student_id: str,
    case_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user_context),
):
    """
    Get chat history for a student's session.
    
    Returns all messages exchanged in this case session.
    """
    from db.database import SessionLocal, StudentSession, ChatLog
    
    enforce_student_resource_access(
        current_user=current_user,
        target_student_id=student_id,
    )

    db = SessionLocal()
    try:
        # Find the session
        session = db.query(StudentSession).filter_by(
            student_id=student_id,
            case_id=case_id
        ).order_by(StudentSession.start_time.desc()).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No session found for student {student_id} on case {case_id}"
            )
        
        # Get chat logs
        messages = db.query(ChatLog).filter_by(
            session_id=session.id
        ).order_by(ChatLog.timestamp).all()
        
        include_internal_metadata = current_user.role in {UserRole.INSTRUCTOR, UserRole.ADMIN}

        return {
            "student_id": student_id,
            "case_id": case_id,
            "session_id": session.id,
            "current_score": session.current_score,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                    "metadata": msg.metadata_json if include_internal_metadata else None,
                }
                for msg in messages
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat history: {str(e)}"
        )
    finally:
        db.close()


@router.get("/status", status_code=status.HTTP_200_OK)
def chat_service_status():
    """
    Check if chat service is operational.
    """
    _status_agent = _get_or_create_agent()
    return {
        "service": "chat",
        "status": "operational" if _status_agent else "unavailable",
        "agent_initialized": _status_agent is not None,
        "model": "gemini-2.5-flash-lite" if _status_agent else None,
    }


# Safety-critical actions that must be taken before any clinical procedure.
_SAFETY_CRITICAL_ACTIONS: frozenset[str] = frozenset({
    "ask_allergies",
    "ask_medications",
    "ask_medical_history",
})


@sessions_router.get(
    "/sessions/{session_id}/evaluation",
    response_model=SessionEvaluationResponse,
    status_code=status.HTTP_200_OK,
)
def get_session_evaluation(
    session_id: int,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    """Return internal evaluation metadata for a session (staff only)."""
    db = SessionLocal()
    try:
        session = db.query(StudentSession).filter_by(id=session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found",
            )

        assistant_logs = (
            db.query(ChatLog)
            .filter_by(session_id=session_id, role="assistant")
            .order_by(ChatLog.timestamp.asc(), ChatLog.id.asc())
            .all()
        )

        evaluations: List[SessionEvaluationItem] = []
        for log in assistant_logs:
            metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
            evaluations.append(
                SessionEvaluationItem(
                    log_id=log.id,
                    timestamp=log.timestamp.isoformat() if log.timestamp else None,
                    interpreted_action=str(metadata.get("interpreted_action", "unknown")),
                    score=float(metadata.get("score", 0.0) or 0.0),
                    assessment=metadata.get("assessment", {}) or {},
                    silent_evaluation=metadata.get("silent_evaluation", {}) or {},
                    reasoning_pattern=metadata.get("reasoning_pattern"),
                )
            )

        return SessionEvaluationResponse(
            session_id=session.id,
            student_id=session.student_id,
            case_id=session.case_id,
            current_score=session.current_score,
            evaluations=evaluations,
        )
    finally:
        db.close()


# ── S10-F: Diagnostic Reasoning Process Trace ────────────────────────────────

class ProcessTraceEvent(BaseModel):
    seq: int
    role: str
    timestamp: Optional[str] = None
    content_preview: str
    interpreted_action: Optional[str] = None
    score: Optional[float] = None
    reasoning_deviation: Optional[bool] = None
    clinical_intent: Optional[str] = None


class ProcessTraceResponse(BaseModel):
    session_id: int
    student_id: str
    case_id: str
    total_score: float
    events: List[ProcessTraceEvent]
    reasoning_pattern: Optional[Dict[str, Any]] = None
    total_actions: int
    deviation_count: int


@sessions_router.get(
    "/sessions/{session_id}/process-trace",
    response_model=ProcessTraceResponse,
    status_code=status.HTTP_200_OK,
    summary="Full diagnostic reasoning process trace for a session (instructor view)",
)
def get_session_process_trace(
    session_id: int,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    db = SessionLocal()
    try:
        session = db.query(StudentSession).filter_by(id=session_id).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found")

        all_logs = (
            db.query(ChatLog)
            .filter_by(session_id=session_id)
            .order_by(ChatLog.timestamp.asc(), ChatLog.id.asc())
            .all()
        )

        events: List[ProcessTraceEvent] = []
        reasoning_pattern: Optional[Dict[str, Any]] = None
        deviation_count = 0
        total_actions = 0

        for seq, log in enumerate(all_logs, start=1):
            metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
            interpreted_action = str(metadata.get("interpreted_action", "")).strip() or None
            score = metadata.get("score")
            score = float(score) if score is not None else None
            silent_eval = metadata.get("silent_evaluation") or {}
            deviation = bool(silent_eval.get("reasoning_deviation", False)) if isinstance(silent_eval, dict) else None

            if interpreted_action and interpreted_action not in {"general_chat", "error", "unknown"}:
                total_actions += 1
                if deviation:
                    deviation_count += 1

            rp = metadata.get("reasoning_pattern")
            if rp and isinstance(rp, dict):
                reasoning_pattern = rp

            events.append(ProcessTraceEvent(
                seq=seq,
                role=log.role,
                timestamp=log.timestamp.isoformat() if log.timestamp else None,
                content_preview=(log.content or "")[:120],
                interpreted_action=interpreted_action,
                score=score,
                reasoning_deviation=deviation if log.role == "assistant" else None,
                clinical_intent=str(metadata.get("clinical_intent", "")).strip() or None,
            ))

        return ProcessTraceResponse(
            session_id=session.id,
            student_id=session.student_id,
            case_id=session.case_id,
            total_score=float(session.current_score or 0.0),
            events=events,
            reasoning_pattern=reasoning_pattern,
            total_actions=total_actions,
            deviation_count=deviation_count,
        )
    finally:
        db.close()


# ── S10-D: Cognitive Load Profiling ──────────────────────────────────────────

class CognitiveLoadResponse(BaseModel):
    session_id: int
    student_id: str
    avg_response_time_ms: Optional[float] = None
    hint_count: int
    deviation_count: int
    action_count: int
    load_level: str
    computed_at: str


@sessions_router.get(
    "/sessions/{session_id}/cognitive-load",
    response_model=CognitiveLoadResponse,
    status_code=status.HTTP_200_OK,
    summary="Cognitive load profiling derived from session activity (S10-D)",
)
def get_session_cognitive_load(
    session_id: int,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    db = SessionLocal()
    try:
        session = db.query(StudentSession).filter_by(id=session_id).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found")

        user_logs = (
            db.query(ChatLog)
            .filter_by(session_id=session_id, role="user")
            .order_by(ChatLog.timestamp.asc())
            .all()
        )
        assistant_logs = (
            db.query(ChatLog)
            .filter_by(session_id=session_id, role="assistant")
            .order_by(ChatLog.timestamp.asc())
            .all()
        )

        # Avg time between consecutive user messages (proxy for response latency)
        response_times_ms: List[float] = []
        for i in range(1, len(user_logs)):
            prev = user_logs[i - 1].timestamp
            curr = user_logs[i].timestamp
            if prev and curr:
                delta = (curr - prev).total_seconds() * 1000
                if 0 < delta < 300_000:  # ignore gaps > 5 min (likely idle)
                    response_times_ms.append(delta)

        avg_rt = round(sum(response_times_ms) / len(response_times_ms), 1) if response_times_ms else None

        hint_count = db.query(CoachHint).filter_by(session_id=session_id).count()

        deviation_count = 0
        action_count = 0
        for log in assistant_logs:
            metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
            action = str(metadata.get("interpreted_action", "")).strip()
            if action and action not in {"general_chat", "error", "unknown"}:
                action_count += 1
                silent_eval = metadata.get("silent_evaluation") or {}
                if isinstance(silent_eval, dict) and silent_eval.get("reasoning_deviation"):
                    deviation_count += 1

        # Heuristic load classification
        load_score = 0
        if avg_rt and avg_rt > 60_000:
            load_score += 1
        if hint_count >= 2:
            load_score += 1
        if action_count > 0 and deviation_count / action_count > 0.3:
            load_score += 1

        load_level = "low" if load_score == 0 else ("medium" if load_score == 1 else "high")

        import datetime as _dt
        return CognitiveLoadResponse(
            session_id=session.id,
            student_id=session.student_id,
            avg_response_time_ms=avg_rt,
            hint_count=hint_count,
            deviation_count=deviation_count,
            action_count=action_count,
            load_level=load_level,
            computed_at=_dt.datetime.utcnow().isoformat() + "Z",
        )
    finally:
        db.close()


# ── S10-E: Safety-Critical Action Reaction Time ───────────────────────────────

class SafetyMetricsResponse(BaseModel):
    session_id: int
    student_id: str
    case_id: str
    safety_actions_taken: List[str]
    safety_actions_missing: List[str]
    first_safety_action_seconds: Optional[float] = None
    all_safety_checks_done: bool
    computed_at: str


@sessions_router.get(
    "/sessions/{session_id}/safety-metrics",
    response_model=SafetyMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Safety-critical action reaction time per session (S10-E)",
)
def get_session_safety_metrics(
    session_id: int,
    current_user: AuthenticatedUser = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.ADMIN)),
):
    db = SessionLocal()
    try:
        session = db.query(StudentSession).filter_by(id=session_id).first()
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session {session_id} not found")

        assistant_logs = (
            db.query(ChatLog)
            .filter_by(session_id=session_id, role="assistant")
            .order_by(ChatLog.timestamp.asc(), ChatLog.id.asc())
            .all()
        )

        taken: set[str] = set()
        first_safety_seconds: Optional[float] = None

        for log in assistant_logs:
            metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
            action = str(metadata.get("interpreted_action", "")).strip()
            if action in _SAFETY_CRITICAL_ACTIONS and action not in taken:
                taken.add(action)
                if first_safety_seconds is None and log.timestamp and session.start_time:
                    delta = (log.timestamp - session.start_time).total_seconds()
                    first_safety_seconds = round(delta, 1)

        missing = sorted(_SAFETY_CRITICAL_ACTIONS - taken)

        import datetime as _dt
        return SafetyMetricsResponse(
            session_id=session.id,
            student_id=session.student_id,
            case_id=session.case_id,
            safety_actions_taken=sorted(taken),
            safety_actions_missing=missing,
            first_safety_action_seconds=first_safety_seconds,
            all_safety_checks_done=len(missing) == 0,
            computed_at=_dt.datetime.utcnow().isoformat() + "Z",
        )
    finally:
        db.close()
