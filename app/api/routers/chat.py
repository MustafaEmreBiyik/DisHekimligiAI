"""
Chat Router
===========
Endpoints for student-AI chat interactions.
Reuses existing DentalEducationAgent from app/agent.py.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
import logging
import datetime

from app.agent import DentalEducationAgent
from app.assessment_engine import AssessmentEngine
from app.scenario_manager import ScenarioManager
from app.api.deps import (
    AuthenticatedUser,
    get_current_user_context,
    require_roles,
)
from app.services.reasoning_classifier import ReasoningPatternClassifier
from db.database import SessionLocal, StudentSession, ChatLog, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()
sessions_router = APIRouter()
reasoning_classifier = ReasoningPatternClassifier()

# Initialize the agent (same as Streamlit version)
try:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if not GEMINI_API_KEY:
        logger.warning("⚠️ GEMINI_API_KEY not found in environment. Chat endpoint will fail.")
        agent = None
    else:
        agent = DentalEducationAgent(
            api_key=GEMINI_API_KEY,
            model_name="models/gemini-2.5-flash-lite"
        )
        logger.info("✅ DentalEducationAgent initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize DentalEducationAgent: {e}")
    agent = None


# ==================== REQUEST/RESPONSE MODELS ====================

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
            metadata_json=None,  # User messages don't have metadata
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
                "reasoning_pattern": reasoning_pattern,
            },
            timestamp=datetime.datetime.utcnow()
        )
        db.add(assistant_log)
        
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
        
        # STEP 8: Return student-safe response payload
        return ChatResponse(
            session_id=session.id,
            ai_response=response_text,
            final_feedback=final_feedback,
            state_updates=safe_state_updates,
            revealed_findings=revealed_findings,
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
    return {
        "service": "chat",
        "status": "operational" if agent else "unavailable",
        "agent_initialized": agent is not None,
        "model": "gemini-2.5-flash-lite" if agent else None
    }


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
