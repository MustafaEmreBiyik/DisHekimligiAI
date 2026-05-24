"""
Rubric Version Service (T-4B)
==============================
Manages immutable snapshots of question rubrics (rubric_guide +
model_answer_outline) so we can audit which criteria were active when
each student answer was graded.

Design decisions
----------------
* Snapshot-on-publish: a new RubricVersion row is created only when an
  instructor explicitly publishes a rubric change, NOT on every question edit.
  This avoids bloat while still providing meaningful audit history.
* Immutable snapshots: rows are never updated after creation.
* Stamp-on-grade: the grading endpoint passes the current rubric version id
  so QuizAnswer.rubric_version_id is filled at grade-publish time.
* No auth logic here: the caller (API router) is responsible for verifying
  the instructor role before calling these functions.
"""
from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class RubricVersionError(ValueError):
    """Raised for invalid rubric versioning operations."""


# ---------------------------------------------------------------------------
# Result dataclasses (returned to callers without exposing ORM objects)
# ---------------------------------------------------------------------------

@dataclass
class RubricVersionInfo:
    """Lightweight snapshot returned to the API layer."""
    id: int
    question_id: int
    version: int
    rubric_guide: str
    model_answer_outline: str
    change_notes: Optional[str]
    created_by: str
    created_at: str   # ISO-8601 string


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _to_info(rv) -> RubricVersionInfo:
    """Convert ORM RubricVersion → RubricVersionInfo dataclass."""
    return RubricVersionInfo(
        id=rv.id,
        question_id=rv.question_id,
        version=rv.version,
        rubric_guide=rv.rubric_guide,
        model_answer_outline=rv.model_answer_outline,
        change_notes=rv.change_notes,
        created_by=rv.created_by,
        created_at=rv.created_at.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def snapshot_rubric(
    db: Session,
    *,
    question_id: int,
    rubric_guide: str,
    model_answer_outline: str,
    change_notes: Optional[str],
    created_by: str,
) -> RubricVersionInfo:
    """
    Create a new immutable rubric version snapshot for the given question.

    The question's current_rubric_version counter is incremented and the
    question's rubric_guide / model_answer_outline fields are updated to
    match the snapshot.

    Returns the newly created RubricVersionInfo.
    Raises RubricVersionError if the question does not exist.
    """
    from db.database import Question, RubricVersion  # avoid circular at module level

    question = db.query(Question).filter(Question.id == question_id).first()
    if question is None:
        raise RubricVersionError(f"Question with id={question_id} not found.")

    # Determine next version number
    next_version = (question.current_rubric_version or 0) + 1

    # Create immutable snapshot row
    rv = RubricVersion(
        question_id=question_id,
        version=next_version,
        rubric_guide=rubric_guide.strip(),
        model_answer_outline=model_answer_outline.strip(),
        change_notes=change_notes.strip() if change_notes else None,
        created_by=created_by,
        created_at=datetime.datetime.utcnow(),
    )
    db.add(rv)
    db.flush()  # get rv.id before committing

    # Update the question's live rubric and version counter
    question.rubric_guide = rubric_guide.strip()
    question.model_answer_outline = model_answer_outline.strip()
    question.current_rubric_version = next_version
    question.updated_at = datetime.datetime.utcnow()

    db.commit()
    db.refresh(rv)

    logger.info(
        "Rubric snapshot created: question_id=%s version=%s by=%s",
        question_id, next_version, created_by,
    )
    return _to_info(rv)


def get_rubric_versions(
    db: Session,
    *,
    question_id: int,
) -> List[RubricVersionInfo]:
    """
    Return all rubric version snapshots for a question, newest first.
    Returns an empty list if none exist.
    Raises RubricVersionError if the question does not exist.
    """
    from db.database import Question, RubricVersion

    question = db.query(Question).filter(Question.id == question_id).first()
    if question is None:
        raise RubricVersionError(f"Question with id={question_id} not found.")

    rows = (
        db.query(RubricVersion)
        .filter(RubricVersion.question_id == question_id)
        .order_by(RubricVersion.version.desc())
        .all()
    )
    return [_to_info(rv) for rv in rows]


def get_rubric_version(
    db: Session,
    *,
    version_id: int,
) -> RubricVersionInfo:
    """
    Return a single rubric version snapshot by its primary key.
    Raises RubricVersionError if not found.
    """
    from db.database import RubricVersion

    rv = db.query(RubricVersion).filter(RubricVersion.id == version_id).first()
    if rv is None:
        raise RubricVersionError(f"RubricVersion with id={version_id} not found.")
    return _to_info(rv)


def get_current_rubric_version_id(
    db: Session,
    *,
    question_id: int,
) -> Optional[int]:
    """
    Return the id of the latest RubricVersion row for a question, or None if
    no snapshot has ever been published for that question.

    Used by the grading endpoint to stamp QuizAnswer.rubric_version_id.
    """
    from db.database import RubricVersion

    rv = (
        db.query(RubricVersion)
        .filter(RubricVersion.question_id == question_id)
        .order_by(RubricVersion.version.desc())
        .first()
    )
    return rv.id if rv else None


def stamp_answer_rubric_version(
    db: Session,
    *,
    answer_id: int,
    rubric_version_id: int,
) -> None:
    """
    Stamp a QuizAnswer with the rubric version that was active at grading time.
    No-ops silently if rubric_version_id is None or the answer is not found.
    """
    from db.database import QuizAnswer

    answer = db.query(QuizAnswer).filter(QuizAnswer.id == answer_id).first()
    if answer is None:
        logger.warning("stamp_answer_rubric_version: answer_id=%s not found", answer_id)
        return
    answer.rubric_version_id = rubric_version_id
    db.commit()
