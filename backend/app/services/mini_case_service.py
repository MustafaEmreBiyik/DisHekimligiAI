"""Mini-Case Service (T-5B) — lightweight clinical vignettes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from db.database import MiniCase


@dataclass
class MiniCaseItem:
    id: int
    mini_case_id: str
    title: str
    difficulty: str
    linked_topic_ids: list[str]
    question_count: int


@dataclass
class MiniCaseDetail:
    id: int
    mini_case_id: str
    title: str
    clinical_vignette: str
    key_findings: list[str]
    question_ids: list[str]
    learning_objectives: list[str]
    linked_topic_ids: list[str]
    difficulty: str


def list_mini_cases(db: Session) -> list[MiniCaseItem]:
    rows = db.query(MiniCase).filter(MiniCase.is_active == True).order_by(MiniCase.title).all()
    return [
        MiniCaseItem(
            id=r.id,
            mini_case_id=r.mini_case_id,
            title=r.title,
            difficulty=r.difficulty,
            linked_topic_ids=r.linked_topic_ids or [],
            question_count=len(r.question_ids or []),
        )
        for r in rows
    ]


def get_mini_case(mini_case_id: str, db: Session) -> Optional[MiniCaseDetail]:
    row = db.query(MiniCase).filter(MiniCase.mini_case_id == mini_case_id).first()
    if not row:
        return None
    return MiniCaseDetail(
        id=row.id,
        mini_case_id=row.mini_case_id,
        title=row.title,
        clinical_vignette=row.clinical_vignette,
        key_findings=row.key_findings or [],
        question_ids=row.question_ids or [],
        learning_objectives=row.learning_objectives or [],
        linked_topic_ids=row.linked_topic_ids or [],
        difficulty=row.difficulty,
    )
