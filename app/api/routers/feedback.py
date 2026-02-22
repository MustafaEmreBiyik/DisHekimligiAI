"""
Feedback Router
===============
Endpoint for collecting student feedback after case completion.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional
import logging
import datetime

from app.api.deps import get_current_user
from db.database import SessionLocal, StudentSession, FeedbackLog

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== REQUEST/RESPONSE MODELS ====================

class FeedbackRequest(BaseModel):
    """
    Feedback submission from student after case completion.
    """
    session_id: int = Field(..., description="Session ID for this case", example=1)
    case_id: str = Field(..., description="Case identifier", example="olp_001")
    rating: int = Field(..., ge=1, le=5, description="1-5 star rating", example=4)
    comment: Optional[str] = Field(None, description="Optional qualitative feedback", example="Vaka çok gerçekçiydi ve öğreticiydi.")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": 1,
                "case_id": "olp_001",
                "rating": 5,
                "comment": "Harika bir deneyimdi. Klinik muhakeme becerilerimi geliştirdi."
            }
        }


class FeedbackResponse(BaseModel):
    """
    Confirmation response after feedback submission.
    """
    success: bool
    message: str
    feedback_id: int


# ==================== ENDPOINTS ====================

@router.post("/submit", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(
    request: FeedbackRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Submit student feedback after completing a case.
    
    **Authentication Required:** Yes (Bearer token)
    
    This endpoint:
    1. Validates the session belongs to the authenticated student
    2. Saves the feedback to FeedbackLog table
    3. Returns confirmation
    
    The feedback data is critical for academic research evaluation.
    """
    db = SessionLocal()
    try:
        # Verify session exists and belongs to current user
        session = db.query(StudentSession).filter_by(
            id=request.session_id,
            student_id=current_user
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {request.session_id} not found or does not belong to you."
            )
        
        # Check if feedback already submitted for this session
        existing_feedback = db.query(FeedbackLog).filter_by(
            session_id=request.session_id
        ).first()
        
        if existing_feedback:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Feedback already submitted for this session."
            )
        
        # Create feedback entry
        feedback = FeedbackLog(
            session_id=request.session_id,
            student_id=current_user,
            case_id=request.case_id,
            rating=request.rating,
            comment=request.comment,
            submitted_at=datetime.datetime.utcnow()
        )
        
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        
        logger.info(
            f"✅ Feedback submitted: Student {current_user}, Case {request.case_id}, "
            f"Rating {request.rating}/5, Session {request.session_id}"
        )
        
        return FeedbackResponse(
            success=True,
            message="Geri bildiriminiz başarıyla kaydedildi. Teşekkür ederiz!",
            feedback_id=feedback.id
        )
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )
    finally:
        db.close()


@router.get("/status", status_code=status.HTTP_200_OK)
def feedback_service_status():
    """
    Check if feedback service is operational.
    """
    return {
        "service": "feedback",
        "status": "operational"
    }
