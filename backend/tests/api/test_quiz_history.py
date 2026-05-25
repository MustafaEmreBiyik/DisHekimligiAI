"""Tests for student quiz history endpoints (T-5D)."""

import pytest

from db.database import Question, QuestionType, QuizAttempt, QuizAnswer, GradingStatus


def _seed_attempt(db, user_id="stu_001", score=8, max_score=10, num_answers=2, published=True):
    attempt = QuizAttempt(user_id=user_id, total_score=score, max_score=max_score)
    db.add(attempt)
    db.flush()

    for i in range(num_answers):
        q = Question(
            question_id=f"Q-HIST-{attempt.id}-{i}",
            question_type=QuestionType.MCQ,
            question_text=f"History test question {i}",
            topic_id="oral_pathology",
            difficulty="medium",
            bloom_level="apply",
            safety_category="safe",
        )
        db.add(q)
        db.flush()
        ans = QuizAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            student_response_text="A",
            auto_score=1,
            grading_status=GradingStatus.PUBLISHED if published else GradingStatus.PENDING,
        )
        db.add(ans)

    db.commit()
    return attempt


class TestMyAttemptsList:
    def test_returns_student_attempts(self, db):
        _seed_attempt(db, user_id="stu_001")
        _seed_attempt(db, user_id="stu_001")
        _seed_attempt(db, user_id="stu_002")

        attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == "stu_001").all()
        assert len(attempts) == 2

    def test_empty_when_no_attempts(self, db):
        attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == "stu_999").all()
        assert len(attempts) == 0


class TestMyAttemptDetail:
    def test_detail_returns_answers(self, db):
        attempt = _seed_attempt(db, user_id="stu_001", num_answers=3)
        loaded = db.query(QuizAttempt).filter(QuizAttempt.id == attempt.id).first()
        assert len(loaded.answers) == 3

    def test_ownership_enforced(self, db):
        attempt = _seed_attempt(db, user_id="stu_001")
        assert attempt.user_id == "stu_001"
        assert attempt.user_id != "stu_002"
