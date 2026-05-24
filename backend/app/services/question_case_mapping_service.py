"""
Question-Case Mapping Service
==============================
Read and write operations for the theory-to-case link graph stored in the
QuestionCaseMapping table.

Each mapping associates one Question with one CaseDefinition and records:
  - The relationship type  (MappingType:  THEORY_SUPPORT / CASE_REINFORCEMENT /
                                          ASSESSMENT_LINK)
  - The review status      (ReviewStatus: APPROVED / BLOCKED_REVIEW_NEEDED /
                                          UNMAPPED)

All four fields accept optional filter values so callers can slice the graph
by question, case, relationship type, or review status independently.

Usage example
-------------
from app.services.question_case_mapping_service import get_question_case_mappings

result = get_question_case_mappings(db, question_id="oral_path_001")
for m in result.mappings:
    print(m.question_id, "->", m.case_id, f"[{m.mapping_type}]")
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from db.database import (
    MappingType,
    Question,
    QuestionCaseMapping,
    ReviewStatus,
)


# -- Data classes --------------------------------------------------------------

@dataclass
class MappingRecord:
    """One row from QuestionCaseMapping, enriched with Question metadata."""

    id: int
    question_pk: int
    question_id: str
    question_type: str
    topic_id: str
    question_text: str
    case_id: str
    mapping_type: str
    review_status: str


@dataclass
class MappingQueryResult:
    """Result of a question-case mapping query."""

    mappings: list[MappingRecord] = field(default_factory=list)
    total: int = 0
    computed_at: str = ""


# -- Private helpers -----------------------------------------------------------

def _parse_mapping_type(value: Optional[str]) -> Optional[MappingType]:
    if not value or not value.strip():
        return None
    try:
        return MappingType(value.strip().lower())
    except ValueError:
        valid = ", ".join(m.value for m in MappingType)
        raise ValueError(f"Invalid mapping_type '{value}'. Valid values: {valid}")


def _parse_review_status(value: Optional[str]) -> Optional[ReviewStatus]:
    if not value or not value.strip():
        return None
    try:
        return ReviewStatus(value.strip().lower())
    except ValueError:
        valid = ", ".join(s.value for s in ReviewStatus)
        raise ValueError(f"Invalid review_status '{value}'. Valid values: {valid}")


# -- Public read API -----------------------------------------------------------

def get_question_case_mappings(
    db: Session,
    *,
    question_id: Optional[str] = None,
    case_id: Optional[str] = None,
    mapping_type: Optional[str] = None,
    review_status: Optional[str] = None,
) -> MappingQueryResult:
    """Return all QuestionCaseMapping rows matching the given filters."""
    mt_filter = _parse_mapping_type(mapping_type)
    rs_filter = _parse_review_status(review_status)

    query = (
        db.query(QuestionCaseMapping, Question)
        .join(Question, QuestionCaseMapping.question_id == Question.id)
    )

    if question_id:
        query = query.filter(Question.question_id == question_id)
    if case_id:
        query = query.filter(QuestionCaseMapping.case_id == case_id)
    if mt_filter is not None:
        query = query.filter(QuestionCaseMapping.mapping_type == mt_filter)
    if rs_filter is not None:
        query = query.filter(QuestionCaseMapping.review_status == rs_filter)

    rows = (
        query
        .order_by(Question.question_id.asc(), QuestionCaseMapping.case_id.asc())
        .all()
    )

    computed_at = datetime.datetime.utcnow().isoformat() + "Z"

    mappings = [
        MappingRecord(
            id=m.id,
            question_pk=q.id,
            question_id=q.question_id,
            question_type=q.question_type.value,
            topic_id=q.topic_id,
            question_text=q.question_text,
            case_id=m.case_id,
            mapping_type=m.mapping_type.value,
            review_status=m.review_status.value,
        )
        for m, q in rows
    ]

    return MappingQueryResult(
        mappings=mappings,
        total=len(mappings),
        computed_at=computed_at,
    )


# -- Custom exceptions ---------------------------------------------------------

class QuestionNotFoundError(ValueError):
    """Raised when the supplied question_id string does not match any Question row."""


class DuplicateMappingError(ValueError):
    """Raised when a (question_id, case_id) pair already exists in QuestionCaseMapping."""


class MappingNotFoundError(ValueError):
    """Raised when the requested QuestionCaseMapping primary key does not exist."""


# -- Write helpers -------------------------------------------------------------

def _build_record(mapping: QuestionCaseMapping, question: Question) -> MappingRecord:
    """Construct a MappingRecord from ORM objects."""
    return MappingRecord(
        id=mapping.id,
        question_pk=question.id,
        question_id=question.question_id,
        question_type=question.question_type.value,
        topic_id=question.topic_id,
        question_text=question.question_text,
        case_id=mapping.case_id,
        mapping_type=mapping.mapping_type.value,
        review_status=mapping.review_status.value,
    )


# -- Public write API ----------------------------------------------------------

def create_mapping(
    db: Session,
    *,
    question_id: str,
    case_id: str,
    mapping_type: str,
    review_status: str = "unmapped",
) -> MappingRecord:
    """
    Create a new QuestionCaseMapping and return the enriched record.

    Raises
    ------
    QuestionNotFoundError
        When question_id is blank or matches no Question row.
    DuplicateMappingError
        When the (question, case_id) pair already exists.
    ValueError
        When mapping_type or review_status is an unrecognised non-blank string.
    """
    if not question_id or not question_id.strip():
        raise QuestionNotFoundError("question_id must not be blank.")
    if not case_id or not case_id.strip():
        raise ValueError("case_id must not be blank.")

    mt = _parse_mapping_type(mapping_type)
    if mt is None:
        valid = ", ".join(m.value for m in MappingType)
        raise ValueError(f"mapping_type is required. Valid values: {valid}")

    rs = _parse_review_status(review_status)
    if rs is None:
        rs = ReviewStatus.UNMAPPED  # blank string -> default to unmapped

    question = db.query(Question).filter(Question.question_id == question_id.strip()).first()
    if question is None:
        raise QuestionNotFoundError(
            f"No question found with question_id='{question_id}'. "
            "Create the question first."
        )

    existing = (
        db.query(QuestionCaseMapping)
        .filter(
            QuestionCaseMapping.question_id == question.id,
            QuestionCaseMapping.case_id == case_id.strip(),
        )
        .first()
    )
    if existing is not None:
        raise DuplicateMappingError(
            f"A mapping between question '{question_id}' and case '{case_id}' "
            f"already exists (id={existing.id}). "
            "Use the existing mapping or delete it first."
        )

    mapping = QuestionCaseMapping(
        question_id=question.id,
        case_id=case_id.strip(),
        mapping_type=mt,
        review_status=rs,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    return _build_record(mapping, question)


def delete_mapping(db: Session, *, mapping_id: int) -> None:
    """
    Delete a QuestionCaseMapping by its primary key.

    Raises
    ------
    MappingNotFoundError
        When no row with this id exists.
    """
    mapping = db.query(QuestionCaseMapping).filter(QuestionCaseMapping.id == mapping_id).first()
    if mapping is None:
        raise MappingNotFoundError(
            f"No QuestionCaseMapping found with id={mapping_id}."
        )
    db.delete(mapping)
    db.commit()
