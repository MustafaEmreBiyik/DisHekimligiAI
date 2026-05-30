"""
Unit tests for question_case_mapping_service.py
=================================================

Covers:
  - No mappings → total=0, mappings=[]
  - Single mapping returned correctly with all fields
  - Multiple mappings returned
  - Filter by question_id (exact match)
  - Filter by case_id (exact match)
  - Filter by mapping_type
  - Filter by review_status
  - Combined filters (question_id + case_id, mapping_type + review_status)
  - Filter that matches nothing → empty result (not an error)
  - Invalid mapping_type → ValueError raised
  - Invalid review_status → ValueError raised
  - All MappingType values accepted
  - All ReviewStatus values accepted
  - Ordering: results sorted by question_id ASC then case_id ASC
  - computed_at is ISO-8601 + "Z"
  - total equals len(mappings)
  - question_text and question_type are present in result
  - Multiple mappings for the same question (fan-out)
  - Multiple questions mapped to the same case (fan-in)

All tests use an in-memory SQLite database.
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
from app.services.question_case_mapping_service import get_question_case_mappings


# ── Seed helpers ──────────────────────────────────────────────────────────────

def _make_question(
    db,
    question_id: str,
    topic_id: str = "oral_pathology",
    question_type: QuestionType = QuestionType.MCQ,
    question_text: str = "",
) -> Question:
    q = Question(
        question_id=question_id,
        question_type=question_type,
        question_text=question_text or f"Text for {question_id}",
        topic_id=topic_id,
        competency_areas=[],
        bloom_level="remember",
        difficulty="medium",
        safety_category="standard",
        max_score=1,
    )
    db.add(q)
    db.flush()
    return q


def _make_mapping(
    db,
    question: Question,
    case_id: str,
    mapping_type: MappingType = MappingType.THEORY_SUPPORT,
    review_status: ReviewStatus = ReviewStatus.UNMAPPED,
) -> QuestionCaseMapping:
    m = QuestionCaseMapping(
        question_id=question.id,
        case_id=case_id,
        mapping_type=mapping_type,
        review_status=review_status,
    )
    db.add(m)
    db.flush()
    return m


# ── TestNoMappings ────────────────────────────────────────────────────────────

class TestNoMappings:
    def test_empty_db_returns_empty_result(self, db):
        result = get_question_case_mappings(db)
        assert result.total == 0
        assert result.mappings == []

    def test_empty_db_computed_at_present(self, db):
        result = get_question_case_mappings(db)
        assert isinstance(result.computed_at, str)
        assert result.computed_at.endswith("Z")

    def test_total_equals_len_mappings(self, db):
        result = get_question_case_mappings(db)
        assert result.total == len(result.mappings)


# ── TestSingleMapping ─────────────────────────────────────────────────────────

class TestSingleMapping:
    def test_all_fields_returned_correctly(self, db):
        q = _make_question(db, "qsm1", topic_id="traumatic", question_type=QuestionType.MCQ,
                           question_text="What is a lesion?")
        _make_mapping(db, q, "case_trauma_01",
                      MappingType.CASE_REINFORCEMENT, ReviewStatus.APPROVED)
        db.commit()

        result = get_question_case_mappings(db)
        assert result.total == 1
        m = result.mappings[0]
        assert m.question_id == "qsm1"
        assert m.question_type == "MCQ"
        assert m.topic_id == "traumatic"
        assert m.question_text == "What is a lesion?"
        assert m.case_id == "case_trauma_01"
        assert m.mapping_type == "case_reinforcement"
        assert m.review_status == "approved"
        assert m.question_pk > 0
        assert m.id > 0

    def test_total_one(self, db):
        q = _make_question(db, "qtot1")
        _make_mapping(db, q, "case_a")
        db.commit()

        result = get_question_case_mappings(db)
        assert result.total == 1
        assert result.total == len(result.mappings)


# ── TestMultipleMappings ──────────────────────────────────────────────────────

class TestMultipleMappings:
    def test_multiple_mappings_all_returned(self, db):
        q1 = _make_question(db, "qmm1")
        q2 = _make_question(db, "qmm2")
        _make_mapping(db, q1, "case_a")
        _make_mapping(db, q1, "case_b")
        _make_mapping(db, q2, "case_a")
        db.commit()

        result = get_question_case_mappings(db)
        assert result.total == 3
        assert len(result.mappings) == 3

    def test_fan_out_one_question_multiple_cases(self, db):
        """One question linked to three cases."""
        q = _make_question(db, "qfan")
        for case_id in ("case_x", "case_y", "case_z"):
            _make_mapping(db, q, case_id)
        db.commit()

        result = get_question_case_mappings(db)
        returned_cases = {m.case_id for m in result.mappings}
        assert returned_cases == {"case_x", "case_y", "case_z"}

    def test_fan_in_multiple_questions_same_case(self, db):
        """Three questions all linked to the same case."""
        for i in range(3):
            q = _make_question(db, f"qfi{i}")
            _make_mapping(db, q, "shared_case")
        db.commit()

        result = get_question_case_mappings(db)
        assert result.total == 3
        assert all(m.case_id == "shared_case" for m in result.mappings)


# ── TestFilterByQuestionId ────────────────────────────────────────────────────

class TestFilterByQuestionId:
    def test_filter_returns_only_matching(self, db):
        q1 = _make_question(db, "qa_filter")
        q2 = _make_question(db, "qb_filter")
        _make_mapping(db, q1, "case_1")
        _make_mapping(db, q2, "case_2")
        db.commit()

        result = get_question_case_mappings(db, question_id="qa_filter")
        assert result.total == 1
        assert result.mappings[0].question_id == "qa_filter"

    def test_filter_no_match_returns_empty(self, db):
        q = _make_question(db, "qexists")
        _make_mapping(db, q, "case_1")
        db.commit()

        result = get_question_case_mappings(db, question_id="q_no_such")
        assert result.total == 0
        assert result.mappings == []

    def test_filter_multiple_mappings_for_question(self, db):
        q = _make_question(db, "qmulti_cases")
        _make_mapping(db, q, "case_a")
        _make_mapping(db, q, "case_b")
        db.commit()

        result = get_question_case_mappings(db, question_id="qmulti_cases")
        assert result.total == 2
        assert all(m.question_id == "qmulti_cases" for m in result.mappings)


# ── TestFilterByCaseId ────────────────────────────────────────────────────────

class TestFilterByCaseId:
    def test_filter_by_case_id(self, db):
        q1 = _make_question(db, "qca1")
        q2 = _make_question(db, "qca2")
        _make_mapping(db, q1, "target_case")
        _make_mapping(db, q2, "other_case")
        db.commit()

        result = get_question_case_mappings(db, case_id="target_case")
        assert result.total == 1
        assert result.mappings[0].case_id == "target_case"

    def test_filter_case_no_match(self, db):
        q = _make_question(db, "qcnm")
        _make_mapping(db, q, "some_case")
        db.commit()

        result = get_question_case_mappings(db, case_id="no_such_case")
        assert result.total == 0


# ── TestFilterByMappingType ───────────────────────────────────────────────────

class TestFilterByMappingType:
    def test_filter_theory_support(self, db):
        q = _make_question(db, "qmt")
        _make_mapping(db, q, "case_1", MappingType.THEORY_SUPPORT)
        _make_mapping(db, q, "case_2", MappingType.CASE_REINFORCEMENT)
        _make_mapping(db, q, "case_3", MappingType.ASSESSMENT_LINK)
        db.commit()

        result = get_question_case_mappings(db, mapping_type="theory_support")
        assert result.total == 1
        assert result.mappings[0].mapping_type == "theory_support"

    def test_filter_case_reinforcement(self, db):
        q = _make_question(db, "qmcr")
        _make_mapping(db, q, "case_1", MappingType.CASE_REINFORCEMENT)
        _make_mapping(db, q, "case_2", MappingType.THEORY_SUPPORT)
        db.commit()

        result = get_question_case_mappings(db, mapping_type="case_reinforcement")
        assert result.total == 1
        assert result.mappings[0].mapping_type == "case_reinforcement"

    def test_filter_assessment_link(self, db):
        q = _make_question(db, "qmal")
        _make_mapping(db, q, "case_1", MappingType.ASSESSMENT_LINK)
        db.commit()

        result = get_question_case_mappings(db, mapping_type="assessment_link")
        assert result.total == 1

    def test_invalid_mapping_type_raises_value_error(self, db):
        with pytest.raises(ValueError, match="mapping_type"):
            get_question_case_mappings(db, mapping_type="not_a_type")

    def test_none_mapping_type_applies_no_filter(self, db):
        q = _make_question(db, "qnmt")
        _make_mapping(db, q, "case_1", MappingType.THEORY_SUPPORT)
        _make_mapping(db, q, "case_2", MappingType.CASE_REINFORCEMENT)
        db.commit()

        result = get_question_case_mappings(db, mapping_type=None)
        assert result.total == 2

    def test_blank_string_mapping_type_applies_no_filter(self, db):
        q = _make_question(db, "qbmt")
        _make_mapping(db, q, "case_1", MappingType.THEORY_SUPPORT)
        db.commit()

        result = get_question_case_mappings(db, mapping_type="")
        assert result.total == 1


# ── TestFilterByReviewStatus ──────────────────────────────────────────────────

class TestFilterByReviewStatus:
    def test_filter_approved(self, db):
        q = _make_question(db, "qrs1")
        _make_mapping(db, q, "case_a", review_status=ReviewStatus.APPROVED)
        _make_mapping(db, q, "case_b", review_status=ReviewStatus.UNMAPPED)
        _make_mapping(db, q, "case_c", review_status=ReviewStatus.BLOCKED_REVIEW_NEEDED)
        db.commit()

        result = get_question_case_mappings(db, review_status="approved")
        assert result.total == 1
        assert result.mappings[0].review_status == "approved"

    def test_filter_unmapped(self, db):
        q = _make_question(db, "qrsu")
        _make_mapping(db, q, "case_a", review_status=ReviewStatus.UNMAPPED)
        _make_mapping(db, q, "case_b", review_status=ReviewStatus.APPROVED)
        db.commit()

        result = get_question_case_mappings(db, review_status="unmapped")
        assert result.total == 1
        assert result.mappings[0].review_status == "unmapped"

    def test_filter_blocked_review_needed(self, db):
        q = _make_question(db, "qrsb")
        _make_mapping(db, q, "case_a", review_status=ReviewStatus.BLOCKED_REVIEW_NEEDED)
        db.commit()

        result = get_question_case_mappings(db, review_status="blocked_review_needed")
        assert result.total == 1
        assert result.mappings[0].review_status == "blocked_review_needed"

    def test_invalid_review_status_raises_value_error(self, db):
        with pytest.raises(ValueError, match="review_status"):
            get_question_case_mappings(db, review_status="invalid_status")

    def test_blank_review_status_applies_no_filter(self, db):
        q = _make_question(db, "qbrs")
        _make_mapping(db, q, "case_a", review_status=ReviewStatus.APPROVED)
        _make_mapping(db, q, "case_b", review_status=ReviewStatus.UNMAPPED)
        db.commit()

        result = get_question_case_mappings(db, review_status="")
        assert result.total == 2


# ── TestCombinedFilters ───────────────────────────────────────────────────────

class TestCombinedFilters:
    def test_question_id_and_case_id(self, db):
        q1 = _make_question(db, "qcf1")
        q2 = _make_question(db, "qcf2")
        _make_mapping(db, q1, "case_a")
        _make_mapping(db, q1, "case_b")
        _make_mapping(db, q2, "case_a")
        db.commit()

        result = get_question_case_mappings(db, question_id="qcf1", case_id="case_a")
        assert result.total == 1
        assert result.mappings[0].question_id == "qcf1"
        assert result.mappings[0].case_id == "case_a"

    def test_mapping_type_and_review_status(self, db):
        q = _make_question(db, "qcf3")
        _make_mapping(db, q, "case_a", MappingType.THEORY_SUPPORT, ReviewStatus.APPROVED)
        _make_mapping(db, q, "case_b", MappingType.THEORY_SUPPORT, ReviewStatus.UNMAPPED)
        _make_mapping(db, q, "case_c", MappingType.CASE_REINFORCEMENT, ReviewStatus.APPROVED)
        db.commit()

        result = get_question_case_mappings(
            db, mapping_type="theory_support", review_status="approved"
        )
        assert result.total == 1
        assert result.mappings[0].case_id == "case_a"

    def test_all_filters_combined_no_match(self, db):
        q = _make_question(db, "qcf4")
        _make_mapping(db, q, "case_a", MappingType.THEORY_SUPPORT, ReviewStatus.APPROVED)
        db.commit()

        result = get_question_case_mappings(
            db,
            question_id="qcf4",
            case_id="case_a",
            mapping_type="case_reinforcement",   # doesn't match
            review_status="approved",
        )
        assert result.total == 0


# ── TestOrdering ──────────────────────────────────────────────────────────────

class TestOrdering:
    def test_ordered_by_question_id_then_case_id(self, db):
        """
        question_id ordering: 'alpha' before 'beta'.
        Within 'alpha': case_id 'case_1' before 'case_2'.
        """
        qa = _make_question(db, "beta_q")
        qb = _make_question(db, "alpha_q")
        _make_mapping(db, qa, "case_a")
        _make_mapping(db, qb, "case_2")
        _make_mapping(db, qb, "case_1")
        db.commit()

        result = get_question_case_mappings(db)
        assert result.total == 3
        qids = [m.question_id for m in result.mappings]
        # alpha_q must come before beta_q
        assert qids.index("alpha_q") < qids.index("beta_q")
        # within alpha_q: case_1 before case_2
        alpha_cases = [m.case_id for m in result.mappings if m.question_id == "alpha_q"]
        assert alpha_cases == ["case_1", "case_2"]


# ── TestMetadata ──────────────────────────────────────────────────────────────

class TestMetadata:
    def test_computed_at_ends_with_z(self, db):
        result = get_question_case_mappings(db)
        assert result.computed_at.endswith("Z")

    def test_computed_at_is_parseable(self, db):
        import datetime as dt
        result = get_question_case_mappings(db)
        dt.datetime.fromisoformat(result.computed_at.rstrip("Z"))

    def test_total_always_equals_len_mappings(self, db):
        q = _make_question(db, "qtot")
        _make_mapping(db, q, "c1")
        _make_mapping(db, q, "c2")
        _make_mapping(db, q, "c3")
        db.commit()

        result = get_question_case_mappings(db)
        assert result.total == len(result.mappings) == 3

    def test_question_text_included(self, db):
        q = _make_question(db, "qtext", question_text="What causes lesions?")
        _make_mapping(db, q, "case_x")
        db.commit()

        result = get_question_case_mappings(db)
        assert result.mappings[0].question_text == "What causes lesions?"

    def test_open_ended_question_type_reported(self, db):
        q = _make_question(db, "qoe_map", question_type=QuestionType.OPEN_ENDED)
        _make_mapping(db, q, "case_oe")
        db.commit()

        result = get_question_case_mappings(db)
        assert result.mappings[0].question_type == "OPEN_ENDED"
