"""Mini-Cases Router (T-5B) — lightweight clinical vignettes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_context, AuthenticatedUser, get_db
from app.services.mini_case_service import list_mini_cases, get_mini_case

router = APIRouter()


class MiniCaseListResponse(BaseModel):
    id: int
    mini_case_id: str
    title: str
    difficulty: str
    linked_topic_ids: List[str]
    question_count: int


class MiniCaseDetailResponse(BaseModel):
    id: int
    mini_case_id: str
    title: str
    clinical_vignette: str
    key_findings: List[str]
    question_ids: List[str]
    learning_objectives: List[str]
    linked_topic_ids: List[str]
    difficulty: str


@router.get("", response_model=List[MiniCaseListResponse])
def list_all_mini_cases(
    current_user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    items = list_mini_cases(db)
    return [MiniCaseListResponse(**item.__dict__) for item in items]


@router.get("/{mini_case_id}", response_model=MiniCaseDetailResponse)
def get_mini_case_detail(
    mini_case_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user_context),
    db: Session = Depends(get_db),
):
    detail = get_mini_case(mini_case_id, db)
    if not detail:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mini case not found")
    return MiniCaseDetailResponse(**detail.__dict__)
