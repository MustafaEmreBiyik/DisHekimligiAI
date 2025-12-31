"""
Chat Router
===========
Endpoints for student-AI chat interactions.
Reuses existing DentalEducationAgent from app/agent.py.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os
import logging

from app.agent import DentalEducationAgent
from app.assessment_engine import AssessmentEngine
from app.scenario_manager import ScenarioManager
from app.api.deps import get_current_user  # JWT authentication

logger = logging.getLogger(__name__)

router = APIRouter()

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


class EvaluationResult(BaseModel):
    """Hidden evaluation from the Silent Grader."""
    is_clinically_accurate: bool = Field(True, description="Whether the action was clinically appropriate")
    safety_violation: bool = Field(False, description="Whether a safety violation occurred")
    score: float = Field(0.0, description="Points earned for this action")
    feedback: Optional[str] = Field(None, description="Internal feedback for analytics")


class ChatResponse(BaseModel):
    """
    Chat response from AI - Silent Evaluator Architecture.
    The student sees response_text, but evaluation is hidden.
    """
    student_id: str
    case_id: str
    response_text: str = Field(..., description="Patient's dialogue response to show the student")
    interpreted_action: str = Field(..., description="What the system understood from student input")
    evaluation: EvaluationResult = Field(..., description="Hidden grader output (not shown to student)")
    is_case_finished: bool = Field(False, description="Whether the case simulation is complete")
    score: float = Field(..., description="Current session score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Full result for debugging")

    class Config:
        json_schema_extra = {
            "example": {
                "student_id": "2021001",
                "case_id": "olp_001",
                "response_text": "Doctor, I have a burning sensation in my cheek.",
                "interpreted_action": "ask_complaint",
                "evaluation": {
                    "is_clinically_accurate": True,
                    "safety_violation": False,
                    "score": 10.0,
                    "feedback": "Correctly identified the chief complaint."
                },
                "is_case_finished": False,
                "score": 35.0,
                "metadata": {}
            }
        }


# ==================== ENDPOINTS ====================

@router.post("/send", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def send_chat_message(
    request: ChatRequest,
    current_user: str = Depends(get_current_user)  # JWT Authentication Required
):
    """
    Process a student's chat message and return AI response.
    
    **Authentication Required:** Yes (Bearer token in Authorization header)
    
    This endpoint uses the Silent Evaluator Architecture:
    1. Gemini interprets the student's action and generates patient dialogue
    2. AssessmentEngine scores the action against clinical rules
    3. MedGemma silently evaluates clinical accuracy (hidden from student)
    4. Returns patient response + hidden evaluation for analytics
    
    The student sees only `response_text`. The `evaluation` object is for
    backend analytics and should NOT be displayed to students.
    """
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable. GEMINI_API_KEY not configured."
        )
    
    try:
        # Use authenticated student_id from JWT token (not from request)
        result = agent.process_student_input(
            student_id=current_user,  # From JWT token
            raw_action=request.message,
            case_id=request.case_id
        )
        
        # Extract key fields for Silent Evaluator response
        llm_interpretation = result.get("llm_interpretation", {})
        assessment = result.get("assessment", {})
        silent_eval = result.get("silent_evaluation", {})
        updated_state = result.get("updated_state", {})
        
        # Response text is the patient's dialogue (from Gemini's explanatory feedback)
        response_text = result.get("final_feedback", "")
        
        # Interpreted action from LLM
        interpreted_action = llm_interpretation.get("interpreted_action", "unknown")
        
        # Build evaluation result (hidden from student UI)
        evaluation = EvaluationResult(
            is_clinically_accurate=silent_eval.get("is_clinically_accurate", True),
            safety_violation=silent_eval.get("safety_violation", False),
            score=assessment.get("score", 0.0),
            feedback=silent_eval.get("feedback") or assessment.get("rule_outcome"),
        )
        
        # Current session score from updated state
        current_score = updated_state.get("current_score", 0.0)
        
        # Check if case is finished (placeholder logic - can be enhanced)
        is_case_finished = updated_state.get("is_finished", False)
        
        # Return Silent Evaluator response
        return ChatResponse(
            student_id=current_user,
            case_id=result["case_id"],
            response_text=response_text,
            interpreted_action=interpreted_action,
            evaluation=evaluation,
            is_case_finished=is_case_finished,
            score=current_score,
            metadata=result,  # Full result for debugging/advanced features
        )
    
    except Exception as e:
        logger.exception(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.get("/history/{student_id}/{case_id}", status_code=status.HTTP_200_OK)
def get_chat_history(student_id: str, case_id: str):
    """
    Get chat history for a student's session.
    
    Returns all messages exchanged in this case session.
    """
    from db.database import SessionLocal, StudentSession, ChatLog
    
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
                    "metadata": msg.metadata_json
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
