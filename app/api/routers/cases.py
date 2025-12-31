"""
Cases Router
============
Endpoints for retrieving case scenarios and managing sessions.
Provides student-safe views (filters out hidden findings).
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import json
import logging

from app.api.deps import get_current_user
from app.scenario_manager import ScenarioManager
from db.database import SessionLocal, StudentSession

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize ScenarioManager (reuses existing case loading logic)
scenario_manager = ScenarioManager()


# ==================== RESPONSE MODELS ====================

class PatientInfo(BaseModel):
    """Patient information (student-safe view)."""
    age: Optional[int] = None
    gender: Optional[str] = None
    chief_complaint: Optional[str] = None


class CaseSummary(BaseModel):
    """Summary of a case for listing."""
    case_id: str
    name: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None
    patient: Optional[PatientInfo] = None


class CaseDetail(BaseModel):
    """Detailed case information (student-safe view)."""
    case_id: str
    name: Optional[str] = None
    difficulty: Optional[str] = None
    category: Optional[str] = None
    patient: Optional[PatientInfo] = None
    correct_diagnosis: Optional[str] = None  # Hidden until case completion


class SessionInfo(BaseModel):
    """Session information for a student."""
    session_id: int
    case_id: str
    current_score: float
    is_active: bool = True


# ==================== HELPER FUNCTIONS ====================

def _extract_patient_info(case: Dict[str, Any]) -> Optional[PatientInfo]:
    """Extract patient info from case data (handles both Turkish and English keys)."""
    # Try Turkish keys first (hasta_profili)
    hp = case.get("hasta_profili")
    if isinstance(hp, dict):
        return PatientInfo(
            age=hp.get("yas"),
            chief_complaint=hp.get("sikayet"),
        )
    
    # Try English keys (patient)
    patient = case.get("patient")
    if isinstance(patient, dict):
        return PatientInfo(
            age=patient.get("age"),
            gender=patient.get("gender"),
            chief_complaint=patient.get("chief_complaint"),
        )
    
    return None


def _get_case_name(case: Dict[str, Any]) -> Optional[str]:
    """Extract case name from case data."""
    return case.get("name") or case.get("dogru_tani")


def _get_difficulty(case: Dict[str, Any]) -> Optional[str]:
    """Extract difficulty from case data."""
    return case.get("difficulty") or case.get("zorluk_seviyesi")


# ==================== ENDPOINTS ====================

@router.get("", response_model=List[CaseSummary], status_code=status.HTTP_200_OK)
def list_cases(current_user: str = Depends(get_current_user)):
    """
    List all available case scenarios.
    
    **Authentication Required:** Yes (Bearer token)
    
    Returns a list of cases with basic information.
    Hidden findings are NOT included.
    """
    cases = []
    
    for case in scenario_manager.case_data:
        if not isinstance(case, dict):
            continue
            
        case_id = case.get("case_id")
        if not case_id:
            continue
            
        cases.append(CaseSummary(
            case_id=case_id,
            name=_get_case_name(case),
            difficulty=_get_difficulty(case),
            category=case.get("category") or case.get("Category"),
            patient=_extract_patient_info(case),
        ))
    
    return cases


@router.get("/{case_id}", response_model=CaseDetail, status_code=status.HTTP_200_OK)
def get_case(case_id: str, current_user: str = Depends(get_current_user)):
    """
    Get details for a specific case.
    
    **Authentication Required:** Yes (Bearer token)
    
    Returns case information suitable for display to students.
    Hidden findings and correct diagnosis are NOT included until case completion.
    """
    # Find the case
    case = None
    for c in scenario_manager.case_data:
        if isinstance(c, dict) and c.get("case_id") == case_id:
            case = c
            break
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found"
        )
    
    return CaseDetail(
        case_id=case_id,
        name=_get_case_name(case),
        difficulty=_get_difficulty(case),
        category=case.get("category") or case.get("Category"),
        patient=_extract_patient_info(case),
        correct_diagnosis=None,  # Hidden until completion
    )


@router.post("/{case_id}/start", response_model=SessionInfo, status_code=status.HTTP_201_CREATED)
def start_session(case_id: str, current_user: str = Depends(get_current_user)):
    """
    Start a new session for a case or return existing active session.
    
    **Authentication Required:** Yes (Bearer token)
    
    Creates a new StudentSession if none exists for this student+case combination.
    Returns the session information including current score.
    """
    # Verify case exists
    case_exists = False
    for c in scenario_manager.case_data:
        if isinstance(c, dict) and c.get("case_id") == case_id:
            case_exists = True
            break
    
    if not case_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Case '{case_id}' not found"
        )
    
    # Get or create session (ScenarioManager handles this)
    state = scenario_manager.get_state(current_user, case_id=case_id)
    
    # Fetch the session from database
    db = SessionLocal()
    try:
        session = db.query(StudentSession).filter_by(
            student_id=current_user,
            case_id=case_id
        ).order_by(StudentSession.start_time.desc()).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )
        
        logger.info(f"✅ Session started/resumed: student={current_user}, case={case_id}")
        
        return SessionInfo(
            session_id=session.id,
            case_id=case_id,
            current_score=session.current_score or 0.0,
            is_active=True,
        )
    finally:
        db.close()


@router.get("/{case_id}/session", response_model=SessionInfo, status_code=status.HTTP_200_OK)
def get_session(case_id: str, current_user: str = Depends(get_current_user)):
    """
    Get current session info for a case.
    
    **Authentication Required:** Yes (Bearer token)
    
    Returns 404 if no session exists.
    """
    db = SessionLocal()
    try:
        session = db.query(StudentSession).filter_by(
            student_id=current_user,
            case_id=case_id
        ).order_by(StudentSession.start_time.desc()).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No session found for case '{case_id}'"
            )
        
        return SessionInfo(
            session_id=session.id,
            case_id=case_id,
            current_score=session.current_score or 0.0,
            is_active=True,
        )
    finally:
        db.close()


@router.get("/status", status_code=status.HTTP_200_OK)
def cases_service_status():
    """
    Check cases service status.
    """
    return {
        "service": "cases",
        "status": "operational",
        "total_cases": len(scenario_manager.case_data),
    }
