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
from db.database import SessionLocal, StudentSession, ChatLog, FeedbackLog, get_student_detailed_history, get_user_stats

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


def get_latest_reasoning_pattern(student_id: str):
    """
    Fetch the most recent reasoning pattern classification for the student.
    """
    db = SessionLocal()
    try:
        logs = (
            db.query(ChatLog)
            .join(StudentSession, ChatLog.session_id == StudentSession.id)
            .filter(StudentSession.student_id == student_id, ChatLog.role == "assistant")
            .order_by(ChatLog.timestamp.desc(), ChatLog.id.desc())
            .all()
        )

        for log in logs:
            metadata = log.metadata_json if isinstance(log.metadata_json, dict) else {}
            reasoning = metadata.get("reasoning_pattern")
            if isinstance(reasoning, dict) and reasoning.get("pattern"):
                return reasoning
        return None
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


@router.get("/student-stats")
def get_student_stats(current_user: str = Depends(get_current_user)):
    """
    Get comprehensive statistics for the authenticated student.

    Returns real data from the database including action history,
    trend data, and action type breakdown for analytics display.
    """
    try:
        # Detailed action history from chat logs
        detailed = get_student_detailed_history(current_user)
        # High-level stats from exam results
        user_stats = get_user_stats(current_user)

        action_history = detailed.get("action_history", [])
        total_score = detailed.get("total_score", 0)
        total_actions = detailed.get("total_actions", 0)
        completed_cases = detailed.get("completed_cases", set())

        # Compute average score per action
        average_score = round(total_score / total_actions, 1) if total_actions > 0 else 0.0

        # Count sessions
        db = SessionLocal()
        try:
            total_sessions = db.query(StudentSession).filter_by(student_id=current_user).count()
        finally:
            db.close()

        reasoning_pattern = get_latest_reasoning_pattern(current_user)

        # Build trend data (cumulative score over actions)
        trend_data = []
        cumulative = 0
        for idx, action in enumerate(action_history, 1):
            cumulative += action.get("score", 0)
            if idx % max(1, len(action_history) // 10) == 0 or idx == len(action_history):
                trend_data.append({"actionIndex": idx, "cumulative": round(cumulative, 1)})

        # Action type stats
        action_type_map: dict = {}
        for action in action_history:
            atype = action.get("action", "unknown")
            score = action.get("score", 0)
            if atype not in action_type_map:
                action_type_map[atype] = {"usage": 0, "total": 0}
            action_type_map[atype]["usage"] += 1
            action_type_map[atype]["total"] += score

        action_type_stats = [
            {
                "type": atype,
                "usage": vals["usage"],
                "total": round(vals["total"], 1),
                "mean": round(vals["total"] / vals["usage"], 1) if vals["usage"] > 0 else 0.0
            }
            for atype, vals in action_type_map.items()
        ]
        action_type_stats.sort(key=lambda x: x["usage"], reverse=True)

        # Pie data (top action types by usage)
        pie_data = [{"name": s["type"], "value": s["usage"]} for s in action_type_stats[:6]]

        # Score distribution (histogram buckets)
        buckets = {"0-2 Puan": 0, "3-5 Puan": 0, "6-8 Puan": 0, "9-10 Puan": 0}
        for action in action_history:
            s = action.get("score", 0)
            if s <= 2:
                buckets["0-2 Puan"] += 1
            elif s <= 5:
                buckets["3-5 Puan"] += 1
            elif s <= 8:
                buckets["6-8 Puan"] += 1
            else:
                buckets["9-10 Puan"] += 1
        histogram_data = [{"scoreRange": k, "count": v} for k, v in buckets.items()]

        # Recommendation: find weakest action type
        recommendation = ""
        if action_type_stats:
            weakest = min(action_type_stats, key=lambda x: x["mean"])
            if weakest["mean"] < 7:
                recommendation = (
                    f"'{weakest['type']}' eylem tipinde ortalama puanınız "
                    f"{weakest['mean']} ile düşük görünüyor. "
                    "Bu alanda daha fazla pratik yapmanız önerilir."
                )
            else:
                best = max(action_type_stats, key=lambda x: x["mean"])
                recommendation = (
                    f"Genel performansınız iyi. '{best['type']}' alanında "
                    f"ortalama {best['mean']} puan ile en yüksek başarıyı gösteriyorsunuz."
                )

        return {
            "total_sessions": total_sessions,
            "completed_cases": len(completed_cases),
            "total_score": round(total_score, 1),
            "total_actions": total_actions,
            "average_score": average_score,
            "action_history": action_history[-10:],  # last 10
            "trend_data": trend_data,
            "action_type_stats": action_type_stats,
            "pie_data": pie_data,
            "histogram_data": histogram_data,
            "recommendation": recommendation,
            "reasoning_pattern": reasoning_pattern,
            # From exam results
            "exam_completed_cases": user_stats.get("total_solved", 0),
            "user_level": user_stats.get("user_level", "Başlangıç"),
        }

    except Exception as e:
        logger.exception(f"Error computing student stats for {current_user}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute student stats: {str(e)}"
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
