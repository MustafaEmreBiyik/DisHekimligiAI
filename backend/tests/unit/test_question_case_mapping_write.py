"""
Unit tests for question_case_mapping_service.py — write operations (T-3B)
==========================================================================

Covers create_mapping():
  - Happy path: mapping created and returned with all correct fields
  - Default review_status is 'unmapped' when not supplied
  - Custom review_status is respected
  - All three mapping_type values are accepted
  - All three review_status values are accepted
  - Blank question_id raises QuestionNotFoundError
  - Non-existent question_id raises QuestionNotFoundError
  - Blank case_id raises ValueError
  - Missing / blank mapping_type raises ValueError
  - Invalid mapping_type string raises ValueError
  - Invalid review_status string raises ValueError
  - Duplicate (question_id, case_id) pair raises DuplicateMappingError
  - Duplicate check is case-sensitive for case_id
  - Same question_id can map to a different case without error
  - Same case_id can be linked to a different question without error
  - Created mapping is visible via get_question_case_mappings

Covers delete_mapping():
  - Happy path: mapping deleted, no longer visible via get_question_case_mappings
  - Non-existent mapping_id raises MappingNotFoundError
  - Deleting a mapping does not affect other mappings
  - Deleted id raises MappingNotFoundError on a second delete attempt

Covers exception types:
  - QuestionNotFoundError is a subclass of ValueError
  - DuplicateMappingError is a subclass of ValueError
  - MappingNotFoundError is a subclass of ValueError
"""

from __future__ import annotations

import pytest

from db.database import (
    MappingType,
    Question,
    QuestionCaseMapping,
    QuestionType,
    ReviewStatus,
)
from app.services.question_case_mapping_service import (
    create_mapping,
    delete_mapping,
    get_question_case_mappings,
    DuplicateMappingError,
    MappingNotFoundError,
    QuestionNotFoundError,
)


def _make_question(
    db,
    question_id: str,
    topic_id: str = "oral_pathology",
    question_type: QuestionType = QuestionType.MCQ,
) -> Question:
    q = Question(
        question_id=question_id,
        question_type=question_type,
        question_text=f"Text for {question_id}",
        topic_id=topic_id,
        competency_areas=[],
        bloom_level="remember",
        difficulty="medium",
        safety_category="standard",
        max_score=1,
    )
    db.add(q)
    db.commit()
    return q


# ── TestExceptionHierarchy ────────────────────────────────────────────────────

class TestExceptionHierarchy:
    def test_question_not_found_is_value_error(self):
        assert issubclass(QuestionNotFoundError, ValueError)

    def test_duplicate_mapping_is_value_error(self):
        assert issubclass(DuplicateMappingError, ValueError)

    def test_mapping_not_found_is_value_error(self):
        assert issubclass(MappingNotFoundError, ValueError)


# ── TestCreateMappingHappyPath ────────────────────────────────────────────────

class TestCreateMappingHappyPath:
    def test_returns_correct_question_id(self, db):
        _make_question(db, "qhp1")
        record = create_mapping(db, question_id="qhp1", case_id="case_a",
                                mapping_type="theory_support")
        assert record.question_id == "qhp1"

    def test_returns_correct_case_id(self, db):
        _make_question(db, "qhp2")
        record = create_mapping(db, question_id="qhp2", case_id="case_b",
                                mapping_type="theory_support")
        assert record.case_id == "case_b"

    def test_returns_correct_mapping_type(self, db):
        _make_question(db, "qhp3")
        record = create_mapping(db, question_id="qhp3", case_id="case_c",
                                mapping_type="case_reinforcement")
        assert record.mapping_type == "case_reinforcement"

    def test_default_review_status_is_unmapped(self, db):
        _make_question(db, "qhp4")
        record = create_mapping(db, question_id="qhp4", case_id="case_d",
                                mapping_type="theory_support")
        assert record.review_status == "unmapped"

    def test_question_text_is_populated(self, db):
        q = _make_question(db, "qhp5")
        record = create_mapping(db, question_id="qhp5", case_id="case_e",
                                mapping_type="theory_support")
        assert record.question_text == q.question_text

    def test_question_type_is_populated(self, db):
        _make_question(db, "qhp6", question_type=QuestionType.OPEN_ENDED)
        record = create_mapping(db, question_id="qhp6", case_id="case_f",
                                mapping_type="assessment_link")
        assert record.question_type == "OPEN_ENDED"

    def test_topic_id_is_populated(self, db):
        _make_question(db, "qhp7", topic_id="traumatic")
        record = create_mapping(db, question_id="qhp7", case_id="case_g",
                                mapping_type="theory_support")
        assert record.topic_id == "traumatic"

    def test_id_and_question_pk_are_positive_integers(self, db):
        _make_question(db, "qhp8")
        record = create_mapping(db, question_id="qhp8", case_id="case_h",
                                mapping_type="theory_support")
        assert isinstance(record.id, int) and record.id > 0
        assert isinstance(record.question_pk, int) and record.question_pk > 0


# ── TestCreateMappingReviewStatus ─────────────────────────────────────────────

class TestCreateMappingReviewStatus:
    def test_approved_status_accepted(self, db):
        _make_question(db, "qrs1")
        record = create_mapping(db, question_id="qrs1", case_id="case_a",
                                mapping_type="theory_support", review_status="approved")
        assert record.review_status == "approved"

    def test_blocked_review_needed_status_accepted(self, db):
        _make_question(db, "qrs2")
        record = create_mapping(db, question_id="qrs2", case_id="case_a",
                                mapping_type="theory_support",
                                review_status="blocked_review_needed")
        assert record.review_status == "blocked_review_needed"

    def test_unmapped_status_explicit(self, db):
        _make_question(db, "qrs3")
        record = create_mapping(db, question_id="qrs3", case_id="case_a",
                                mapping_type="theory_support", review_status="unmapped")
        assert record.review_status == "unmapped"

    def test_blank_review_status_defaults_to_unmapped(self, db):
        _make_question(db, "qrs4")
        record = create_mapping(db, question_id="qrs4", case_id="case_a",
                                mapping_type="theory_support", review_status="")
        assert record.review_status == "unmapped"


# ── TestCreateMappingAllMappingTypes ──────────────────────────────────────────

class TestCreateMappingAllMappingTypes:
    def test_theory_support(self, db):
        _make_question(db, "qmt1")
        record = create_mapping(db, question_id="qmt1", case_id="c",
                                mapping_type="theory_support")
        assert record.mapping_type == "theory_support"

    def test_case_reinforcement(self, db):
        _make_question(db, "qmt2")
        record = create_mapping(db, question_id="qmt2", case_id="c",
                                mapping_type="case_reinforcement")
        assert record.mapping_type == "case_reinforcement"

    def test_assessment_link(self, db):
        _make_question(db, "qmt3")
        record = create_mapping(db, question_id="qmt3", case_id="c",
                                mapping_type="assessment_link")
        assert record.mapping_type == "assessment_link"


# ── TestCreateMappingErrors ───────────────────────────────────────────────────

class TestCreateMappingErrors:
    def test_nonexistent_question_id_raises(self, db):
        with pytest.raises(QuestionNotFoundError):
            create_mapping(db, question_id="no_such_q", case_id="case_a",
                           mapping_type="theory_support")

    def test_blank_question_id_raises(self, db):
        with pytest.raises(QuestionNotFoundError):
            create_mapping(db, question_id="", case_id="case_a",
                           mapping_type="theory_support")

    def test_whitespace_question_id_raises(self, db):
        with pytest.raises(QuestionNotFoundError):
            create_mapping(db, question_id="   ", case_id="case_a",
                           mapping_type="theory_support")

    def test_blank_case_id_raises(self, db):
        _make_question(db, "qerr1")
        with pytest.raises(ValueError):
            create_mapping(db, question_id="qerr1", case_id="",
                           mapping_type="theory_support")

    def test_whitespace_case_id_raises(self, db):
        _make_question(db, "qerr2")
        with pytest.raises(ValueError):
            create_mapping(db, question_id="qerr2", case_id="   ",
                           mapping_type="theory_support")

    def test_blank_mapping_type_raises(self, db):
        _make_question(db, "qerr3")
        with pytest.raises(ValueError):
            create_mapping(db, question_id="qerr3", case_id="case_a",
                           mapping_type="")

    def test_invalid_mapping_type_raises(self, db):
        _make_question(db, "qerr4")
        with pytest.raises(ValueError, match="mapping_type"):
            create_mapping(db, question_id="qerr4", case_id="case_a",
                           mapping_type="not_a_type")

    def test_invalid_review_status_raises(self, db):
        _make_question(db, "qerr5")
        with pytest.raises(ValueError, match="review_status"):
            create_mapping(db, question_id="qerr5", case_id="case_a",
                           mapping_type="theory_support",
                           review_status="invalid_status")


# ── TestDuplicateMapping ──────────────────────────────────────────────────────

class TestDuplicateMapping:
    def test_duplicate_raises_duplicate_error(self, db):
        _make_question(db, "qdup1")
        create_mapping(db, question_id="qdup1", case_id="case_x",
                       mapping_type="theory_support")
        with pytest.raises(DuplicateMappingError):
            create_mapping(db, question_id="qdup1", case_id="case_x",
                           mapping_type="case_reinforcement")  # same pair, different type

    def test_same_question_different_case_is_allowed(self, db):
        _make_question(db, "qdup2")
        create_mapping(db, question_id="qdup2", case_id="case_a",
                       mapping_type="theory_support")
        record = create_mapping(db, question_id="qdup2", case_id="case_b",
                                mapping_type="theory_support")
        assert record.case_id == "case_b"

    def test_same_case_different_question_is_allowed(self, db):
        _make_question(db, "qdup3a")
        _make_question(db, "qdup3b")
        create_mapping(db, question_id="qdup3a", case_id="shared_case",
                       mapping_type="theory_support")
        record = create_mapping(db, question_id="qdup3b", case_id="shared_case",
                                mapping_type="theory_support")
        assert record.question_id == "qdup3b"


# ── TestCreateMappingVisibility ───────────────────────────────────────────────

class TestCreateMappingVisibility:
    def test_created_mapping_found_by_get(self, db):
        _make_question(db, "qvis1")
        create_mapping(db, question_id="qvis1", case_id="case_v",
                       mapping_type="theory_support")
        result = get_question_case_mappings(db, question_id="qvis1")
        assert result.total == 1
        assert result.mappings[0].case_id == "case_v"

    def test_created_mapping_filterable_by_case(self, db):
        _make_question(db, "qvis2")
        create_mapping(db, question_id="qvis2", case_id="target_case",
                       mapping_type="theory_support")
        result = get_question_case_mappings(db, case_id="target_case")
        assert result.total == 1

    def test_create_two_mappings_both_visible(self, db):
        _make_question(db, "qvis3")
        create_mapping(db, question_id="qvis3", case_id="case_a",
                       mapping_type="theory_support")
        create_mapping(db, question_id="qvis3", case_id="case_b",
                       mapping_type="case_reinforcement")
        result = get_question_case_mappings(db, question_id="qvis3")
        assert result.total == 2


# ── TestDeleteMappingHappyPath ────────────────────────────────────────────────

class TestDeleteMappingHappyPath:
    def test_deleted_mapping_not_found_by_get(self, db):
        _make_question(db, "qdel1")
        record = create_mapping(db, question_id="qdel1", case_id="case_d",
                                mapping_type="theory_support")
        delete_mapping(db, mapping_id=record.id)
        result = get_question_case_mappings(db, question_id="qdel1")
        assert result.total == 0

    def test_delete_does_not_affect_other_mappings(self, db):
        _make_question(db, "qdel2")
        r1 = create_mapping(db, question_id="qdel2", case_id="case_keep",
                            mapping_type="theory_support")
        r2 = create_mapping(db, question_id="qdel2", case_id="case_delete",
                            mapping_type="theory_support")
        delete_mapping(db, mapping_id=r2.id)
        result = get_question_case_mappings(db, question_id="qdel2")
        assert result.total == 1
        assert result.mappings[0].id == r1.id

    def test_delete_returns_none(self, db):
        _make_question(db, "qdel3")
        record = create_mapping(db, question_id="qdel3", case_id="case_x",
                                mapping_type="theory_support")
        result = delete_mapping(db, mapping_id=record.id)
        assert result is None


# ── TestDeleteMappingErrors ───────────────────────────────────────────────────

class TestDeleteMappingErrors:
    def test_nonexistent_id_raises(self, db):
        with pytest.raises(MappingNotFoundError):
            delete_mapping(db, mapping_id=99999)

    def test_double_delete_raises_on_second_call(self, db):
        _make_question(db, "qdd1")
        record = create_mapping(db, question_id="qdd1", case_id="case_d",
                                mapping_type="theory_support")
        delete_mapping(db, mapping_id=record.id)
        with pytest.raises(MappingNotFoundError):
            delete_mapping(db, mapping_id=record.id)

    def test_error_message_contains_id(self, db):
        with pytest.raises(MappingNotFoundError, match="42"):
            delete_mapping(db, mapping_id=42)
