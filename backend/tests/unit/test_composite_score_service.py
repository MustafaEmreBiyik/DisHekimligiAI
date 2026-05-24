"""
Unit tests for composite_score_service.py
==========================================

Covers:
  - All three components present → correct weighted composite
  - One component missing (MCQ only, OE only, Case only)
  - Two components missing (MCQ+Case only, MCQ+OE only, OE+Case only)
  - No components present → cold-start (composite_pct is None)
  - Zero-score component (student has published records but earned 0 points)
  - Weighted calculation correctness with known numbers
  - Rounding to 2 decimal places
  - Component metadata: available, earned, max_possible, pct, design_weight, effective_weight
  - Legacy 'quiz_global' ExamResult rows are excluded from case component
  - PENDING/GRADED answers are NOT counted (only PUBLISHED)

All tests use an in-memory SQLite database and operate directly on the
service function — no FastAPI test client required.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import (
    Base,
    ExamResult,
    GradingStatus,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
)
from app.services.composite_score_service import (
    _MCQ_WEIGHT,
    _OE_WEIGHT,
    _CASE_WEIGHT,
    calculate_composite_score,
)


# ── Shared fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def db():
    """Fresh in-memory SQLite session for each test."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


# ── Helper factories ─────────────────────────────────────────────────────────

def _make_mcq_question(db, qid: str, max_score: int = 1) -> Question:
    q = Question(
        question_id=qid,
        question_type=QuestionType.MCQ,
        question_text=f"MCQ question {qid}",
        topic_id="test_topic",
        bloom_level="apply",
        difficulty="medium",
        safety_category="none",
        options_json=["A", "B", "C"],
        correct_option="A",
        max_score=max_score,
    )
    db.add(q)
    db.flush()
    return q


def _make_oe_question(db, qid: str, max_score: int = 10) -> Question:
    q = Question(
        question_id=qid,
        question_type=QuestionType.OPEN_ENDED,
        question_text=f"OE question {qid}",
        topic_id="test_topic",
        bloom_level="analyze",
        difficulty="hard",
        safety_category="none",
        rubric_guide="Some rubric",
        model_answer_outline="Some outline",
        max_score=max_score,
    )
    db.add(q)
    db.flush()
    return q


def _make_attempt(db, user_id: str) -> QuizAttempt:
    attempt = QuizAttempt(user_id=user_id, total_score=0, max_score=0)
    db.add(attempt)
    db.flush()
    return attempt


def _add_mcq_answer(
    db,
    attempt: QuizAttempt,
    question: Question,
    auto_score: int,
    published: bool = True,
) -> QuizAnswer:
    ans = QuizAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        student_response_text="A",
        auto_score=auto_score,
        grading_status=GradingStatus.PUBLISHED if published else GradingStatus.PENDING,
    )
    db.add(ans)
    db.flush()
    return ans


def _add_oe_answer(
    db,
    attempt: QuizAttempt,
    question: Question,
    instructor_score: int,
    published: bool = True,
) -> QuizAnswer:
    ans = QuizAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        student_response_text="Some answer",
        instructor_score=instructor_score,
        grading_status=GradingStatus.PUBLISHED if published else GradingStatus.PENDING,
    )
    db.add(ans)
    db.flush()
    return ans


def _add_case_result(db, user_id: str, case_id: str, score: int, max_score: int) -> ExamResult:
    r = ExamResult(user_id=user_id, case_id=case_id, score=score, max_score=max_score)
    db.add(r)
    db.flush()
    return r


# ── Tests ────────────────────────────────────────────────────────────────────

class TestAllComponentsPresent:
    """All three components have published data."""

    def test_composite_uses_design_weights(self, db):
        """70% MCQ + 80% OE + 50% Case → composite = 70*0.35 + 80*0.40 + 50*0.25 = 69.0"""
        uid = "user_all"
        # MCQ: 7/10
        q_mcq = _make_mcq_question(db, "mcq_all_01", max_score=10)
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q_mcq, auto_score=7)
        # OE: 8/10
        q_oe = _make_oe_question(db, "oe_all_01", max_score=10)
        att2 = _make_attempt(db, uid)
        _add_oe_answer(db, att2, q_oe, instructor_score=8)
        # Case: 5/10
        _add_case_result(db, uid, "case_01", score=5, max_score=10)
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.mcq.available is True
        assert result.open_ended.available is True
        assert result.case.available is True
        assert result.all_components_available is True

        assert result.mcq.pct == pytest.approx(70.0, abs=0.01)
        assert result.open_ended.pct == pytest.approx(80.0, abs=0.01)
        assert result.case.pct == pytest.approx(50.0, abs=0.01)

        expected = 70.0 * _MCQ_WEIGHT + 80.0 * _OE_WEIGHT + 50.0 * _CASE_WEIGHT
        assert result.composite_pct == pytest.approx(expected, abs=0.01)

    def test_effective_weights_equal_design_weights_when_all_available(self, db):
        uid = "user_eff"
        q_mcq = _make_mcq_question(db, "mcq_eff_01")
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q_mcq, auto_score=1)

        q_oe = _make_oe_question(db, "oe_eff_01", max_score=10)
        att2 = _make_attempt(db, uid)
        _add_oe_answer(db, att2, q_oe, instructor_score=5)

        _add_case_result(db, uid, "case_eff_01", score=5, max_score=10)
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.mcq.effective_weight == pytest.approx(_MCQ_WEIGHT, abs=1e-6)
        assert result.open_ended.effective_weight == pytest.approx(_OE_WEIGHT, abs=1e-6)
        assert result.case.effective_weight == pytest.approx(_CASE_WEIGHT, abs=1e-6)

    def test_perfect_score_yields_100(self, db):
        uid = "user_perfect"
        q_mcq = _make_mcq_question(db, "mcq_perf_01", max_score=10)
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q_mcq, auto_score=10)

        q_oe = _make_oe_question(db, "oe_perf_01", max_score=10)
        att2 = _make_attempt(db, uid)
        _add_oe_answer(db, att2, q_oe, instructor_score=10)

        _add_case_result(db, uid, "case_perf_01", score=10, max_score=10)
        db.commit()

        result = calculate_composite_score(uid, db)
        assert result.composite_pct == pytest.approx(100.0, abs=0.01)


class TestMissingComponents:
    """One or more components have no data — weights redistribute."""

    def test_mcq_only(self, db):
        """Only MCQ data → effective weight becomes 1.0, composite = mcq_pct."""
        uid = "user_mcq_only"
        q = _make_mcq_question(db, "mcq_only_01", max_score=10)
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q, auto_score=6)
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.mcq.available is True
        assert result.open_ended.available is False
        assert result.case.available is False
        assert result.all_components_available is False

        assert result.mcq.effective_weight == pytest.approx(1.0, abs=1e-6)
        assert result.open_ended.effective_weight == pytest.approx(0.0, abs=1e-6)
        assert result.case.effective_weight == pytest.approx(0.0, abs=1e-6)

        assert result.composite_pct == pytest.approx(60.0, abs=0.01)
        assert result.composite_pct is not None  # available, not cold start

    def test_oe_only(self, db):
        """Only OE data → effective weight becomes 1.0, composite = oe_pct."""
        uid = "user_oe_only"
        q = _make_oe_question(db, "oe_only_01", max_score=20)
        att = _make_attempt(db, uid)
        _add_oe_answer(db, att, q, instructor_score=15)
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.open_ended.available is True
        assert result.mcq.available is False
        assert result.case.available is False

        assert result.open_ended.effective_weight == pytest.approx(1.0, abs=1e-6)
        assert result.composite_pct == pytest.approx(75.0, abs=0.01)

    def test_case_only(self, db):
        """Only Case data → effective weight becomes 1.0, composite = case_pct."""
        uid = "user_case_only"
        _add_case_result(db, uid, "c01", score=8, max_score=10)
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.case.available is True
        assert result.mcq.available is False
        assert result.open_ended.available is False

        assert result.case.effective_weight == pytest.approx(1.0, abs=1e-6)
        assert result.composite_pct == pytest.approx(80.0, abs=0.01)

    def test_mcq_and_case_no_oe(self, db):
        """
        MCQ (0.35) + Case (0.25) available; OE missing.
        Effective weights: MCQ = 0.35/0.60, Case = 0.25/0.60.
        MCQ 60%, Case 70% →
          composite = 60 * (0.35/0.60) + 70 * (0.25/0.60)
                    = 60 * 0.58333 + 70 * 0.41667
                    = 35.0 + 29.167
                    = 64.167 → rounded to 64.17
        """
        uid = "user_mcq_case"
        q_mcq = _make_mcq_question(db, "mcq_mc_01", max_score=10)
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q_mcq, auto_score=6)  # 60%

        _add_case_result(db, uid, "case_mc_01", score=7, max_score=10)  # 70%
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.mcq.available is True
        assert result.open_ended.available is False
        assert result.case.available is True

        total_design = _MCQ_WEIGHT + _CASE_WEIGHT
        expected_eff_mcq = _MCQ_WEIGHT / total_design
        expected_eff_case = _CASE_WEIGHT / total_design

        assert result.mcq.effective_weight == pytest.approx(expected_eff_mcq, abs=1e-6)
        assert result.case.effective_weight == pytest.approx(expected_eff_case, abs=1e-6)
        assert result.open_ended.effective_weight == pytest.approx(0.0, abs=1e-6)

        expected_composite = 60.0 * expected_eff_mcq + 70.0 * expected_eff_case
        assert result.composite_pct == pytest.approx(expected_composite, abs=0.01)

    def test_mcq_and_oe_no_case(self, db):
        """MCQ (0.35) + OE (0.40) available; Case missing. Total pool = 0.75."""
        uid = "user_mcq_oe"
        q_mcq = _make_mcq_question(db, "mcq_mo_01", max_score=10)
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q_mcq, auto_score=8)  # 80%

        q_oe = _make_oe_question(db, "oe_mo_01", max_score=10)
        att2 = _make_attempt(db, uid)
        _add_oe_answer(db, att2, q_oe, instructor_score=6)  # 60%
        db.commit()

        result = calculate_composite_score(uid, db)

        total_design = _MCQ_WEIGHT + _OE_WEIGHT
        expected_composite = 80.0 * (_MCQ_WEIGHT / total_design) + 60.0 * (_OE_WEIGHT / total_design)
        assert result.composite_pct == pytest.approx(expected_composite, abs=0.01)


class TestColdStart:
    """Student has zero history."""

    def test_no_components_composite_is_none(self, db):
        """No data at all → composite_pct must be None (not 0.0)."""
        result = calculate_composite_score("brand_new_student", db)

        assert result.mcq.available is False
        assert result.open_ended.available is False
        assert result.case.available is False
        assert result.all_components_available is False
        assert result.composite_pct is None  # None, NOT 0.0 — must distinguish cold start

    def test_cold_start_components_have_zero_earned_and_max(self, db):
        result = calculate_composite_score("cold_student", db)

        assert result.mcq.earned == 0
        assert result.mcq.max_possible == 0
        assert result.mcq.pct is None

        assert result.open_ended.earned == 0
        assert result.open_ended.max_possible == 0
        assert result.open_ended.pct is None

        assert result.case.earned == 0
        assert result.case.max_possible == 0
        assert result.case.pct is None


class TestZeroScoreDistinction:
    """Student has published records but earned zero points."""

    def test_zero_mcq_score_is_available_and_pct_zero(self, db):
        """
        An attempt exists and is published, but the student got every MCQ wrong.
        available must be True; pct must be 0.0; composite_pct must not be None.
        """
        uid = "user_zero_mcq"
        q = _make_mcq_question(db, "mcq_zero_01", max_score=5)
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q, auto_score=0)  # wrong answer, 0 points
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.mcq.available is True
        assert result.mcq.pct == pytest.approx(0.0, abs=0.001)
        # composite_pct should be 0.0 (has history, just earned nothing), not None
        assert result.composite_pct is not None
        assert result.composite_pct == pytest.approx(0.0, abs=0.001)

    def test_zero_oe_score_is_available_and_pct_zero(self, db):
        uid = "user_zero_oe"
        q = _make_oe_question(db, "oe_zero_01", max_score=10)
        att = _make_attempt(db, uid)
        _add_oe_answer(db, att, q, instructor_score=0)
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.open_ended.available is True
        assert result.open_ended.pct == pytest.approx(0.0, abs=0.001)
        assert result.composite_pct is not None

    def test_zero_case_score_is_available_and_pct_zero(self, db):
        uid = "user_zero_case"
        _add_case_result(db, uid, "case_zero_01", score=0, max_score=10)
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.case.available is True
        assert result.case.pct == pytest.approx(0.0, abs=0.001)
        assert result.composite_pct is not None


class TestPendingAnswersExcluded:
    """PENDING and GRADED answers must NOT be counted in the composite."""

    def test_pending_mcq_answer_not_counted(self, db):
        uid = "user_pending_mcq"
        q = _make_mcq_question(db, "mcq_pend_01", max_score=10)
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q, auto_score=8, published=False)  # PENDING
        db.commit()

        result = calculate_composite_score(uid, db)

        # PENDING answer must not count → MCQ component is unavailable
        assert result.mcq.available is False
        assert result.mcq.pct is None

    def test_graded_but_unpublished_oe_answer_not_counted(self, db):
        """GRADED (not PUBLISHED) OE answers must also be excluded."""
        uid = "user_graded_oe"
        q = _make_oe_question(db, "oe_graded_01", max_score=10)
        att = _make_attempt(db, uid)
        # Manually set GRADED (not PUBLISHED)
        ans = QuizAnswer(
            attempt_id=att.id,
            question_id=q.id,
            student_response_text="My answer",
            instructor_score=7,
            grading_status=GradingStatus.GRADED,
        )
        db.add(ans)
        db.commit()

        result = calculate_composite_score(uid, db)

        # GRADED (not PUBLISHED) should not count
        assert result.open_ended.available is False

    def test_mix_of_pending_and_published_counts_only_published(self, db):
        """When a student has one PUBLISHED and one PENDING MCQ, only the published one counts."""
        uid = "user_mix_mcq"
        q1 = _make_mcq_question(db, "mcq_mix_01", max_score=10)
        q2 = _make_mcq_question(db, "mcq_mix_02", max_score=10)
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q1, auto_score=8, published=True)   # counts
        _add_mcq_answer(db, att, q2, auto_score=10, published=False)  # ignored
        db.commit()

        result = calculate_composite_score(uid, db)

        # Only q1 contributes: 8/10 = 80%
        assert result.mcq.available is True
        assert result.mcq.earned == 8
        assert result.mcq.max_possible == 10
        assert result.mcq.pct == pytest.approx(80.0, abs=0.01)


class TestLegacyExclusion:
    """Legacy 'quiz_global' ExamResult rows must be excluded from the case component."""

    def test_quiz_global_exam_result_excluded(self, db):
        uid = "user_legacy"
        # This is the legacy MCQ submission row (old path before S8B)
        _add_case_result(db, uid, "quiz_global", score=9, max_score=10)
        db.commit()

        result = calculate_composite_score(uid, db)

        # quiz_global must not count as a case score
        assert result.case.available is False
        assert result.case.pct is None

    def test_real_case_alongside_legacy_quiz_global(self, db):
        uid = "user_mixed_legacy"
        _add_case_result(db, uid, "quiz_global", score=10, max_score=10)  # excluded
        _add_case_result(db, uid, "oral_lichen_planus_01", score=6, max_score=10)  # counted
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.case.available is True
        assert result.case.earned == 6
        assert result.case.max_possible == 10
        assert result.case.pct == pytest.approx(60.0, abs=0.01)


class TestMultipleRecordsAggregation:
    """Multiple attempts/results for the same user are summed correctly."""

    def test_multiple_mcq_attempts_summed(self, db):
        uid = "user_multi_mcq"
        q1 = _make_mcq_question(db, "mcq_m1", max_score=10)
        q2 = _make_mcq_question(db, "mcq_m2", max_score=10)

        att1 = _make_attempt(db, uid)
        att2 = _make_attempt(db, uid)
        _add_mcq_answer(db, att1, q1, auto_score=6)
        _add_mcq_answer(db, att2, q2, auto_score=8)
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.mcq.earned == 14
        assert result.mcq.max_possible == 20
        assert result.mcq.pct == pytest.approx(70.0, abs=0.01)

    def test_multiple_case_results_summed(self, db):
        uid = "user_multi_case"
        _add_case_result(db, uid, "case_a", score=7, max_score=10)
        _add_case_result(db, uid, "case_b", score=5, max_score=10)
        db.commit()

        result = calculate_composite_score(uid, db)

        assert result.case.earned == 12
        assert result.case.max_possible == 20
        assert result.case.pct == pytest.approx(60.0, abs=0.01)


class TestComponentMetadata:
    """Verify all metadata fields are populated correctly."""

    def test_design_weights_always_present(self, db):
        """Design weights are constants regardless of data availability."""
        result = calculate_composite_score("meta_user_cold", db)

        assert result.mcq.design_weight == pytest.approx(_MCQ_WEIGHT, abs=1e-9)
        assert result.open_ended.design_weight == pytest.approx(_OE_WEIGHT, abs=1e-9)
        assert result.case.design_weight == pytest.approx(_CASE_WEIGHT, abs=1e-9)

    def test_computed_at_is_iso_string(self, db):
        result = calculate_composite_score("meta_user_ts", db)

        assert isinstance(result.computed_at, str)
        assert result.computed_at.endswith("Z")
        # Must parse without error
        from datetime import datetime as _dt
        _dt.fromisoformat(result.computed_at.replace("Z", "+00:00"))

    def test_all_components_available_flag(self, db):
        uid = "meta_user_all"
        q_mcq = _make_mcq_question(db, "meta_mcq_01")
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q_mcq, auto_score=1)

        q_oe = _make_oe_question(db, "meta_oe_01", max_score=10)
        att2 = _make_attempt(db, uid)
        _add_oe_answer(db, att2, q_oe, instructor_score=8)

        _add_case_result(db, uid, "meta_case_01", score=5, max_score=10)
        db.commit()

        result = calculate_composite_score(uid, db)
        assert result.all_components_available is True

    def test_all_components_available_false_when_any_missing(self, db):
        uid = "meta_user_partial"
        q_mcq = _make_mcq_question(db, "meta_mcq_02")
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q_mcq, auto_score=1)
        db.commit()

        result = calculate_composite_score(uid, db)
        assert result.all_components_available is False


class TestRounding:
    """Composite and pct values should be rounded to 2 decimal places."""

    def test_composite_pct_has_at_most_2_decimal_places(self, db):
        """
        1/3 scores (33.333...%) should be rounded to 2 dp in the final output.
        """
        uid = "user_round"
        q = _make_mcq_question(db, "mcq_round_01", max_score=3)
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q, auto_score=1)  # 33.333...%
        db.commit()

        result = calculate_composite_score(uid, db)

        pct_str = str(result.mcq.pct)
        decimal_part = pct_str.split(".")[1] if "." in pct_str else ""
        assert len(decimal_part) <= 2, (
            f"pct has more than 2 decimal places: {result.mcq.pct}"
        )

    def test_composite_rounded_when_redistribution_produces_repeating_decimal(self, db):
        """MCQ only: 1/3 of max → pct = 33.33, composite = 33.33."""
        uid = "user_round2"
        q = _make_mcq_question(db, "mcq_round_02", max_score=3)
        att = _make_attempt(db, uid)
        _add_mcq_answer(db, att, q, auto_score=1)
        db.commit()

        result = calculate_composite_score(uid, db)
        # Should not raise and should be a finite float rounded to 2 dp
        assert isinstance(result.composite_pct, float)
        assert result.composite_pct == pytest.approx(33.33, abs=0.01)


class TestUserIsolation:
    """Scores for one student must not leak into another student's result."""

    def test_different_users_are_isolated(self, db):
        # Student A: good MCQ result
        q1 = _make_mcq_question(db, "mcq_iso_01", max_score=10)
        att_a = _make_attempt(db, "user_A")
        _add_mcq_answer(db, att_a, q1, auto_score=9)

        # Student B: no data at all
        db.commit()

        result_a = calculate_composite_score("user_A", db)
        result_b = calculate_composite_score("user_B", db)

        assert result_a.mcq.available is True
        assert result_a.mcq.earned == 9

        assert result_b.mcq.available is False
        assert result_b.composite_pct is None
