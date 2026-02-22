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
import datetime

from app.agent import DentalEducationAgent
from app.assessment_engine import AssessmentEngine
from app.scenario_manager import ScenarioManager
from app.api.deps import get_current_user  # JWT authentication
from db.database import SessionLocal, StudentSession, ChatLog

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


class ChatResponse(BaseModel):
    """
    Chat response from AI.
    """
    student_id: str
    case_id: str
    session_id: int = Field(..., description="Database session ID for this chat session")
    final_feedback: str = Field(..., description="Response text to show the student")
    score: float = Field(..., description="Points earned for this action")
    metadata: Dict[str, Any] = Field(..., description="Full result including interpretation and assessment")

    class Config:
        schema_extra = {
            "example": {
                "student_id": "2021001",
                "case_id": "olp_001",
                "session_id": 42,
                "final_feedback": "Oral mukoza muayenesi yapılıyor...",
                "score": 20.0,
                "metadata": {
                    "llm_interpretation": {"interpreted_action": "perform_oral_exam"},
                    "assessment": {"score": 20, "rule_outcome": "..."},
                    "updated_state": {"current_score": 35}
                }
            }
        }


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


# ==================== ENDPOINTS ====================

@router.post("/send", response_model=ChatResponse, status_code=status.HTTP_200_OK)
def send_chat_message(
    request: ChatRequest,
    current_user: str = Depends(get_current_user)  # JWT Authentication Required
):
    """
    Process a student's chat message and return AI response.
    
    **Authentication Required:** Yes (Bearer token in Authorization header)
    
    This endpoint:
    1. Validates JWT token and extracts student_id
    2. Gets or creates a StudentSession for telemetry
    3. Logs user message to ChatLog
    4. Calls DentalEducationAgent.process_student_input()
    5. Logs AI response with evaluation metadata to ChatLog
    6. Updates session score
    7. Commits all changes to database
    8. Returns the AI's response and assessment
    
    The student_id is extracted from the JWT token, ensuring that users
    can only interact with their own sessions.
    """
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat service is unavailable. GEMINI_API_KEY not configured."
        )
    
    db = SessionLocal()
    try:
        # STEP 1: Get or create session for this student + case
        session = get_or_create_session(db, current_user, request.case_id)
        
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
            student_id=current_user,  # From JWT token
            raw_action=request.message,
            case_id=request.case_id
        )
        
        # STEP 4: Extract key fields for response and logging
        final_feedback = result.get("final_feedback", "")
        assessment = result.get("assessment", {})
        score = assessment.get("score", 0.0)
        llm_interpretation = result.get("llm_interpretation", {})
        
        # STEP 5: Log AI's response to database with metadata
        assistant_log = ChatLog(
            session_id=session.id,
            role='assistant',
            content=final_feedback,
            metadata_json={
                "score": score,
                "interpreted_action": llm_interpretation.get("interpreted_action", ""),
                "clinical_intent": llm_interpretation.get("clinical_intent", ""),
                "priority": llm_interpretation.get("priority", ""),
                "assessment": assessment,
                "silent_evaluation": result.get("silent_evaluation", {})
            },
            timestamp=datetime.datetime.utcnow()
        )
        db.add(assistant_log)
        
        # STEP 6: Update session score
        session.current_score += score
        
        # STEP 7: Commit all changes to database
        db.commit()
        
        logger.info(
            f"✅ Logged interaction for student {current_user} on case {request.case_id}. "
            f"Score: {score}, Total: {session.current_score}"
        )
        
        # STEP 8: Return structured response to frontend
        return ChatResponse(
            student_id=current_user,
            case_id=result["case_id"],
            session_id=session.id,  # Include session_id for feedback tracking
            final_feedback=final_feedback,
            score=score,
            metadata=result  # Full result for debugging/advanced features
        )
    
    except Exception as e:
        db.rollback()
        logger.exception(f"Error processing chat message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )
    finally:
        db.close()


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
