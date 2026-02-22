"""
Analytics Router
================
Endpoints for exporting research data as CSV files.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from typing import List
import logging
import csv
import io

from app.api.deps import get_current_user
from db.database import SessionLocal, StudentSession, ChatLog, FeedbackLog

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== HELPER FUNCTIONS ====================

def generate_actions_csv() -> str:
    """
    Generate CSV export of all chat actions (student interactions).
    Joins ChatLog with StudentSession to include student_id and case_id.
    """
    db = SessionLocal()
    try:
        # Query all chat logs with session data
        query = db.query(
            ChatLog.id,
            ChatLog.session_id,
            StudentSession.student_id,
            StudentSession.case_id,
            ChatLog.role,
            ChatLog.content,
            ChatLog.metadata_json,
            ChatLog.timestamp,
            StudentSession.current_score
        ).join(
            StudentSession, ChatLog.session_id == StudentSession.id
        ).order_by(ChatLog.timestamp)
        
        results = query.all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'log_id',
            'session_id',
            'student_id',
            'case_id',
            'role',
            'content',
            'score',
            'interpreted_action',
            'clinical_intent',
            'timestamp',
            'session_total_score'
        ])
        
        # Write data rows
        for row in results:
            metadata = row.metadata_json or {}
            writer.writerow([
                row.id,
                row.session_id,
                row.student_id,
                row.case_id,
                row.role,
                row.content,
                metadata.get('score', '') if row.role == 'assistant' else '',
                metadata.get('interpreted_action', '') if row.role == 'assistant' else '',
                metadata.get('clinical_intent', '') if row.role == 'assistant' else '',
                row.timestamp.isoformat() if row.timestamp else '',
                row.current_score
            ])
        
        return output.getvalue()
    
    finally:
        db.close()


def generate_feedback_csv() -> str:
    """
    Generate CSV export of all student feedback submissions.
    """
    db = SessionLocal()
    try:
        # Query all feedback
        feedback_logs = db.query(FeedbackLog).order_by(FeedbackLog.submitted_at).all()
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'feedback_id',
            'session_id',
            'student_id',
            'case_id',
            'rating',
            'comment',
            'submitted_at'
        ])
        
        # Write data rows
        for feedback in feedback_logs:
            writer.writerow([
                feedback.id,
                feedback.session_id,
                feedback.student_id,
                feedback.case_id,
                feedback.rating,
                feedback.comment or '',
                feedback.submitted_at.isoformat() if feedback.submitted_at else ''
            ])
        
        return output.getvalue()
    
    finally:
        db.close()


def generate_sessions_csv() -> str:
    """
    Generate CSV export of all student sessions (summary).
    """
    db = SessionLocal()
    try:
        sessions = db.query(StudentSession).order_by(StudentSession.start_time).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'session_id',
            'student_id',
            'case_id',
            'current_score',
            'start_time',
            'message_count'
        ])
        
        for session in sessions:
            message_count = len(session.chat_logs) if session.chat_logs else 0
            writer.writerow([
                session.id,
                session.student_id,
                session.case_id,
                session.current_score,
                session.start_time.isoformat() if session.start_time else '',
                message_count
            ])
        
        return output.getvalue()
    
    finally:
        db.close()


# ==================== ENDPOINTS ====================

@router.get("/export/actions")
def export_actions_csv(current_user: str = Depends(get_current_user)):
    """
    Export all chat action logs as CSV.
    
    **Authentication Required:** Yes
    **Format:** CSV file with columns: log_id, session_id, student_id, case_id, 
                role, content, score, interpreted_action, clinical_intent, timestamp
    
    This endpoint is designed for researchers to download the complete dataset
    for academic analysis.
    """
    try:
        csv_content = generate_actions_csv()
        
        # Create streaming response
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=dental_tutor_actions.csv"
            }
        )
    
    except Exception as e:
        logger.exception(f"Error generating actions CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate CSV: {str(e)}"
        )


@router.get("/export/feedback")
def export_feedback_csv(current_user: str = Depends(get_current_user)):
    """
    Export all student feedback submissions as CSV.
    
    **Authentication Required:** Yes
    **Format:** CSV file with columns: feedback_id, session_id, student_id, 
                case_id, rating, comment, submitted_at
    
    This qualitative data is critical for academic research evaluation.
    """
    try:
        csv_content = generate_feedback_csv()
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=dental_tutor_feedback.csv"
            }
        )
    
    except Exception as e:
        logger.exception(f"Error generating feedback CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate CSV: {str(e)}"
        )


@router.get("/export/sessions")
def export_sessions_csv(current_user: str = Depends(get_current_user)):
    """
    Export all student sessions (summary) as CSV.
    
    **Authentication Required:** Yes
    **Format:** CSV file with session-level summaries
    """
    try:
        csv_content = generate_sessions_csv()
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=dental_tutor_sessions.csv"
            }
        )
    
    except Exception as e:
        logger.exception(f"Error generating sessions CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate CSV: {str(e)}"
        )


@router.get("/status")
def analytics_service_status():
    """
    Check if analytics service is operational.
    """
    return {
        "service": "analytics",
        "status": "operational",
        "available_exports": ["actions", "feedback", "sessions"]
    }
