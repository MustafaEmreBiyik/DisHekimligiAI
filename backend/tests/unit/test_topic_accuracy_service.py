"""
Unit tests for topic_accuracy_service.py
=========================================

Covers:
  - Multiple topics in one result
  - Weak topic (pct < 60%) and strong topic (pct >= 60%)
  - Untagged/empty topic_id normalised to "untagged"
  - No MCQ history → has_any_data=False, topics=[]
  - Zero score for a topic → is_weak=True, pct=0.0
  - User isolation — different users' answers never leak
  - Exclusion of PENDING and GRADED (only PUBLISHED counted)
  - Exclusion of OPEN_ENDED answers (only MCQ counted)
  - Percentage calculation correctness
  - Sorting: weakest first, then strong ascending, None pct last
  - correct_count counts only full-marks answers
  - Metadata: has_any_data flag, computed_at is ISO-8601+Z string
  - topic_label falls back to topic_id for unknown topics
  - topic_label is translated for known topics

All tests use an in-memory SQLite database and call the service function
directly — no FastAPI test client required.
"""

from __future__ import annotations

import pytest

from db.database import (
    GradingStatus,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
)
from app.services.topic_accuracy_service import (
    _UNTAGGED_TOPIC_ID,
    _WEAK_THRESHOLD_PCT,
    get_topic_accuracy,
)


# ── Seed helpers ─────────────────────────────────────────────────────────────

def _make_question(
    db,
    question_id: str,
    topic_id: str,
    max_score: int = 1,
    question_type: QuestionType = QuestionType.MCQ,
) -> Question:
    q = Question(
        question_id=question_id,
        question_type=question_type,
        question_text=f"Question {question_id}",
        topic_id=topic_id,
        competency_areas=[],
        bloom_level="remember",
        difficulty="medium",
        safety_category="standard",
        max_score=max_score,
    )
    db.add(q)
    db.flush()
    return q


def _make_attempt(db, user_id: str) -> QuizAttempt:
    attempt = QuizAttempt(user_id=user_id)
    db.add(attempt)
    db.flush()
    return attempt


def _make_answer(
    db,
    attempt: QuizAttempt,
    question: Question,
    auto_score: int,
    status: GradingStatus = GradingStatus.PUBLISHED,
) -> QuizAnswer:
    ans = QuizAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        student_response_text="answer",
        auto_score=auto_score,
        grading_status=status,
    )
    db.add(ans)
    db.flush()
    return ans


# ── TestNoHistory ──────────────────────────────────────────────────────────────

class TestNoHistory:
    def test_no_mcq_answers_has_any_data_false(self, db):
        """A student with no published MCQ answers gets has_any_data=False."""
        result = get_topic_accuracy("stu_none", db)
        assert result.has_any_data is False

    def test_no_mcq_answers_topics_empty(self, db):
        result = get_topic_accuracy("stu_none", db)
        assert result.topics == []

    def test_no_mcq_answers_computed_at_present(self, db):
        result = get_topic_accuracy("stu_none", db)
        assert result.computed_at.endswith("Z")


# ── TestMultipleTopics ─────────────────────────────────────────────────────────

class TestMultipleTopics:
    def test_two_topics_both_returned(self, db):
        """Student with published MCQs across two topics sees both topics."""
        q1 = _make_question(db, "q1", "oral_pathology")
        q2 = _make_question(db, "q2", "traumatic")
        attempt = _make_attempt(db, "stu_multi")
        _make_answer(db, attempt, q1, auto_score=1)
        _make_answer(db, attempt, q2, auto_score=1)
        db.commit()

        result = get_topic_accuracy("stu_multi", db)
        topic_ids = {t.topic_id for t in result.topics}
        assert "oral_pathology" in topic_ids
        assert "traumatic" in topic_ids
        assert len(result.topics) == 2

    def test_has_any_data_true_when_answers_exist(self, db):
        q = _make_question(db, "q1", "oral_pathology")
        attempt = _make_attempt(db, "stu_data")
        _make_answer(db, attempt, q, auto_score=1)
        db.commit()

        result = get_topic_accuracy("stu_data", db)
        assert result.has_any_data is True

    def test_earned_and_max_aggregated_within_topic(self, db):
        """Two answers in the same topic are aggregated correctly."""
        q1 = _make_question(db, "q1", "oral_pathology", max_score=2)
        q2 = _make_question(db, "q2", "oral_pathology", max_score=2)
        attempt = _make_attempt(db, "stu_agg")
        _make_answer(db, attempt, q1, auto_score=2)  # full marks
        _make_answer(db, attempt, q2, auto_score=1)  # partial
        db.commit()

        result = get_topic_accuracy("stu_agg", db)
        assert len(result.topics) == 1
        t = result.topics[0]
        assert t.earned == 3
        assert t.max_possible == 4
        assert t.pct == 75.0


# ── TestWeakAndStrong ─────────────────────────────────────────────────────────

class TestWeakAndStrong:
    def test_weak_topic_flagged(self, db):
        """Topic with accuracy < 60% is marked is_weak=True."""
        # 1 out of 4 → 25%
        q = _make_question(db, "qw", "oral_pathology", max_score=4)
        attempt = _make_attempt(db, "stu_weak")
        _make_answer(db, attempt, q, auto_score=1)
        db.commit()

        result = get_topic_accuracy("stu_weak", db)
        assert result.topics[0].is_weak is True

    def test_strong_topic_not_flagged(self, db):
        """Topic with accuracy >= 60% is marked is_weak=False."""
        # 3 out of 4 → 75%
        q = _make_question(db, "qs", "oral_pathology", max_score=4)
        attempt = _make_attempt(db, "stu_strong")
        _make_answer(db, attempt, q, auto_score=3)
        db.commit()

        result = get_topic_accuracy("stu_strong", db)
        assert result.topics[0].is_weak is False

    def test_exactly_threshold_is_not_weak(self, db):
        """Accuracy exactly at 60.0% is not flagged as weak (threshold is exclusive)."""
        # 3 out of 5 → 60.0%
        q = _make_question(db, "qt", "oral_pathology", max_score=5)
        attempt = _make_attempt(db, "stu_thresh")
        _make_answer(db, attempt, q, auto_score=3)
        db.commit()

        result = get_topic_accuracy("stu_thresh", db)
        assert result.topics[0].pct == 60.0
        assert result.topics[0].is_weak is False

    def test_weak_topic_sorted_before_strong(self, db):
        """Weakest topics appear before strong topics in sorted output."""
        # Topic A: 2/10 → 20% (weak)
        # Topic B: 8/10 → 80% (strong)
        qa = _make_question(db, "qa", "oral_pathology", max_score=10)
        qb = _make_question(db, "qb", "traumatic", max_score=10)
        attempt = _make_attempt(db, "stu_sort")
        _make_answer(db, attempt, qa, auto_score=2)
        _make_answer(db, attempt, qb, auto_score=8)
        db.commit()

        result = get_topic_accuracy("stu_sort", db)
        assert len(result.topics) == 2
        # Weak (20%) must come before strong (80%)
        assert result.topics[0].is_weak is True
        assert result.topics[0].pct == 20.0
        assert result.topics[1].is_weak is False
        assert result.topics[1].pct == 80.0


# ── TestUntaggedTopic ─────────────────────────────────────────────────────────

class TestUntaggedTopic:
    def test_empty_string_topic_normalised_to_untagged(self, db):
        """A question with topic_id='' is grouped under 'untagged'."""
        q = _make_question(db, "q_empty", topic_id="")
        attempt = _make_attempt(db, "stu_ut")
        _make_answer(db, attempt, q, auto_score=1)
        db.commit()

        result = get_topic_accuracy("stu_ut", db)
        assert len(result.topics) == 1
        assert result.topics[0].topic_id == _UNTAGGED_TOPIC_ID

    def test_whitespace_only_topic_normalised_to_untagged(self, db):
        """A question with topic_id containing only whitespace is grouped under 'untagged'."""
        q = _make_question(db, "q_ws", topic_id="   ")
        attempt = _make_attempt(db, "stu_ws")
        _make_answer(db, attempt, q, auto_score=0)
        db.commit()

        result = get_topic_accuracy("stu_ws", db)
        assert result.topics[0].topic_id == _UNTAGGED_TOPIC_ID

    def test_untagged_topic_has_translated_label(self, db):
        q = _make_question(db, "q_ut_label", topic_id="")
        attempt = _make_attempt(db, "stu_ul")
        _make_answer(db, attempt, q, auto_score=1)
        db.commit()

        result = get_topic_accuracy("stu_ul", db)
        assert result.topics[0].topic_label == "Etiketlenmemiş"


# ── TestZeroScore ─────────────────────────────────────────────────────────────

class TestZeroScore:
    def test_zero_auto_score_pct_is_zero(self, db):
        q = _make_question(db, "qz", "oral_pathology", max_score=2)
        attempt = _make_attempt(db, "stu_zero")
        _make_answer(db, attempt, q, auto_score=0)
        db.commit()

        result = get_topic_accuracy("stu_zero", db)
        t = result.topics[0]
        assert t.pct == 0.0
        assert t.earned == 0
        assert t.max_possible == 2

    def test_zero_score_topic_is_weak(self, db):
        q = _make_question(db, "qz2", "oral_pathology")
        attempt = _make_attempt(db, "stu_zero2")
        _make_answer(db, attempt, q, auto_score=0)
        db.commit()

        result = get_topic_accuracy("stu_zero2", db)
        assert result.topics[0].is_weak is True

    def test_zero_score_has_any_data_true(self, db):
        """has_any_data must be True even when every answer scored zero."""
        q = _make_question(db, "qz3", "traumatic")
        attempt = _make_attempt(db, "stu_zero3")
        _make_answer(db, attempt, q, auto_score=0)
        db.commit()

        result = get_topic_accuracy("stu_zero3", db)
        assert result.has_any_data is True


# ── TestExclusion ─────────────────────────────────────────────────────────────

class TestExclusion:
    def test_pending_mcq_answer_excluded(self, db):
        q = _make_question(db, "qp", "oral_pathology")
        attempt = _make_attempt(db, "stu_pend")
        _make_answer(db, attempt, q, auto_score=1, status=GradingStatus.PENDING)
        db.commit()

        result = get_topic_accuracy("stu_pend", db)
        assert result.has_any_data is False
        assert result.topics == []

    def test_graded_but_unpublished_mcq_excluded(self, db):
        q = _make_question(db, "qg", "oral_pathology")
        attempt = _make_attempt(db, "stu_graded")
        _make_answer(db, attempt, q, auto_score=1, status=GradingStatus.GRADED)
        db.commit()

        result = get_topic_accuracy("stu_graded", db)
        assert result.has_any_data is False

    def test_open_ended_published_answer_excluded(self, db):
        """Published OPEN_ENDED answers must NOT appear in topic accuracy."""
        q_oe = _make_question(db, "qoe", "oral_pathology", question_type=QuestionType.OPEN_ENDED)
        attempt = _make_attempt(db, "stu_oe")
        ans = QuizAnswer(
            attempt_id=attempt.id,
            question_id=q_oe.id,
            student_response_text="essay answer",
            instructor_score=1,
            grading_status=GradingStatus.PUBLISHED,
        )
        db.add(ans)
        db.commit()

        result = get_topic_accuracy("stu_oe", db)
        assert result.has_any_data is False
        assert result.topics == []

    def test_mix_pending_and_published_counts_only_published(self, db):
        """Only the PUBLISHED answer contributes when mixed with PENDING."""
        q1 = _make_question(db, "qm1", "oral_pathology", max_score=4)
        q2 = _make_question(db, "qm2", "oral_pathology", max_score=4)
        attempt = _make_attempt(db, "stu_mix")
        _make_answer(db, attempt, q1, auto_score=4, status=GradingStatus.PUBLISHED)
        _make_answer(db, attempt, q2, auto_score=4, status=GradingStatus.PENDING)
        db.commit()

        result = get_topic_accuracy("stu_mix", db)
        assert len(result.topics) == 1
        t = result.topics[0]
        # Only q1 is published: earned=4, max=4
        assert t.earned == 4
        assert t.max_possible == 4
        assert t.pct == 100.0


# ── TestCorrectCount ──────────────────────────────────────────────────────────

class TestCorrectCount:
    def test_correct_count_full_marks_only(self, db):
        """correct_count increments only when auto_score >= max_score."""
        q1 = _make_question(db, "qc1", "traumatic", max_score=2)
        q2 = _make_question(db, "qc2", "traumatic", max_score=2)
        q3 = _make_question(db, "qc3", "traumatic", max_score=2)
        attempt = _make_attempt(db, "stu_cc")
        _make_answer(db, attempt, q1, auto_score=2)  # correct
        _make_answer(db, attempt, q2, auto_score=1)  # partial — not correct
        _make_answer(db, attempt, q3, auto_score=0)  # wrong
        db.commit()

        result = get_topic_accuracy("stu_cc", db)
        t = result.topics[0]
        assert t.answered_count == 3
        assert t.correct_count == 1

    def test_answered_count_matches_published_answers(self, db):
        q1 = _make_question(db, "qa1", "oral_pathology")
        q2 = _make_question(db, "qa2", "oral_pathology")
        attempt = _make_attempt(db, "stu_ac")
        _make_answer(db, attempt, q1, auto_score=1)
        _make_answer(db, attempt, q2, auto_score=0)
        db.commit()

        result = get_topic_accuracy("stu_ac", db)
        assert result.topics[0].answered_count == 2


# ── TestUserIsolation ─────────────────────────────────────────────────────────

class TestUserIsolation:
    def test_different_users_are_isolated(self, db):
        """User A's answers must not appear in User B's topic accuracy."""
        q = _make_question(db, "qi", "oral_pathology", max_score=10)
        attempt_a = _make_attempt(db, "stu_iso_a")
        attempt_b = _make_attempt(db, "stu_iso_b")
        # A scores 10/10; B scores 0/10
        _make_answer(db, attempt_a, q, auto_score=10)
        _make_answer(db, attempt_b, q, auto_score=0)
        db.commit()

        result_a = get_topic_accuracy("stu_iso_a", db)
        result_b = get_topic_accuracy("stu_iso_b", db)

        assert result_a.topics[0].pct == 100.0
        assert result_b.topics[0].pct == 0.0

    def test_unknown_user_gets_no_data(self, db):
        q = _make_question(db, "qu", "oral_pathology")
        attempt = _make_attempt(db, "stu_known")
        _make_answer(db, attempt, q, auto_score=1)
        db.commit()

        result = get_topic_accuracy("stu_unknown_xyz", db)
        assert result.has_any_data is False


# ── TestPercentageAndRounding ─────────────────────────────────────────────────

class TestPercentageAndRounding:
    def test_percentage_rounded_to_2_decimal_places(self, db):
        """1 out of 3 → 33.33% (not 33.333...)"""
        q = _make_question(db, "qr", "oral_pathology", max_score=3)
        attempt = _make_attempt(db, "stu_round")
        _make_answer(db, attempt, q, auto_score=1)
        db.commit()

        result = get_topic_accuracy("stu_round", db)
        pct = result.topics[0].pct
        assert pct == 33.33
        # Verify it really is rounded, not truncated
        assert str(pct) == "33.33"

    def test_100_pct_correct(self, db):
        q = _make_question(db, "q100", "traumatic", max_score=5)
        attempt = _make_attempt(db, "stu_100")
        _make_answer(db, attempt, q, auto_score=5)
        db.commit()

        result = get_topic_accuracy("stu_100", db)
        assert result.topics[0].pct == 100.0

    def test_multiple_answers_same_topic_correct_pct(self, db):
        """4 answers: 3 correct (max_score=1), 1 wrong → 75.0%"""
        qs = [_make_question(db, f"qpct{i}", "oral_pathology") for i in range(4)]
        attempt = _make_attempt(db, "stu_pct")
        for i, q in enumerate(qs):
            _make_answer(db, attempt, q, auto_score=1 if i < 3 else 0)
        db.commit()

        result = get_topic_accuracy("stu_pct", db)
        assert result.topics[0].pct == 75.0


# ── TestSorting ───────────────────────────────────────────────────────────────

class TestSorting:
    def test_three_topics_sorted_weak_first(self, db):
        """
        Topic A: 10% (very weak)
        Topic B: 50% (weak)
        Topic C: 90% (strong)
        Expected order: A, B, C.
        """
        qa = _make_question(db, "sort_a", "oral_pathology", max_score=10)
        qb = _make_question(db, "sort_b", "traumatic", max_score=10)
        qc = _make_question(db, "sort_c", "infectious_diseases", max_score=10)
        attempt = _make_attempt(db, "stu_sort3")
        _make_answer(db, attempt, qa, auto_score=1)   # 10%
        _make_answer(db, attempt, qb, auto_score=5)   # 50%
        _make_answer(db, attempt, qc, auto_score=9)   # 90%
        db.commit()

        result = get_topic_accuracy("stu_sort3", db)
        pcts = [t.pct for t in result.topics]
        assert pcts == [10.0, 50.0, 90.0]

    def test_strong_topics_sorted_ascending_after_weak(self, db):
        """Among strong topics, lower pct appears before higher pct."""
        q65 = _make_question(db, "s65", "oral_pathology", max_score=100)
        q85 = _make_question(db, "s85", "traumatic", max_score=100)
        attempt = _make_attempt(db, "stu_strong_ord")
        _make_answer(db, attempt, q65, auto_score=65)
        _make_answer(db, attempt, q85, auto_score=85)
        db.commit()

        result = get_topic_accuracy("stu_strong_ord", db)
        assert result.topics[0].pct == 65.0
        assert result.topics[1].pct == 85.0


# ── TestTopicLabel ────────────────────────────────────────────────────────────

class TestTopicLabel:
    def test_known_topic_id_returns_translated_label(self, db):
        q = _make_question(db, "ql_known", "oral_pathology")
        attempt = _make_attempt(db, "stu_lbl_known")
        _make_answer(db, attempt, q, auto_score=1)
        db.commit()

        result = get_topic_accuracy("stu_lbl_known", db)
        assert result.topics[0].topic_label == "Oral Patoloji"

    def test_unknown_topic_id_falls_back_to_topic_id(self, db):
        q = _make_question(db, "ql_unk", "rare_unknown_topic_xyz")
        attempt = _make_attempt(db, "stu_lbl_unk")
        _make_answer(db, attempt, q, auto_score=1)
        db.commit()

        result = get_topic_accuracy("stu_lbl_unk", db)
        t = result.topics[0]
        assert t.topic_id == "rare_unknown_topic_xyz"
        assert t.topic_label == "rare_unknown_topic_xyz"


# ── TestMetadata ──────────────────────────────────────────────────────────────

class TestMetadata:
    def test_computed_at_is_iso_string_ending_with_z(self, db):
        result = get_topic_accuracy("stu_meta", db)
        assert isinstance(result.computed_at, str)
        assert result.computed_at.endswith("Z")

    def test_computed_at_is_parseable(self, db):
        import datetime as dt
        result = get_topic_accuracy("stu_meta2", db)
        # Should not raise
        dt.datetime.fromisoformat(result.computed_at.rstrip("Z"))

    def test_weak_threshold_constant_is_sixty(self):
        """Guard against accidental threshold changes."""
        assert _WEAK_THRESHOLD_PCT == 60.0
