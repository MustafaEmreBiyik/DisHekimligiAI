"""Sprint 14 T07 — BKT EM prior-fitting unit tests.

Verifies:
- _forward_backward returns valid gamma probabilities (∈ [0, 1]) and finite LL.
- fit_topic_em recovers known P(T) within |Δ| < 0.15 on a synthetic 30-student
  fixture where the true P(T)=0.25 and the sequences are long enough. @slow.
- fit_topic_em converges on a perfectly-correct sequence (all 1s).
- fit_topic_em handles an empty sequences list gracefully.
- run_em_fitting dry_run returns results without writing DB rows.
- run_em_fitting with real DB data writes BKTTopicPrior rows (is_synthetic=False
  when thresholds exceeded, True when below).
- Upsert: re-running updates existing BKTTopicPrior rows in place.
- get_topic_prior falls back to global defaults when no fitted row exists.
- get_topic_prior returns fitted row values when a real fit exists.
"""

from __future__ import annotations

import datetime
import math

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import (
    Base,
    BKTTopicPrior,
    GradingStatus,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
    User,
    UserRole,
)
from app.constants import BKT_P_GUESS, BKT_P_INIT, BKT_P_SLIP, BKT_P_TRANSIT
from app.services.bkt_em_service import (
    EMParams,
    _forward_backward,
    fit_topic_em,
    get_topic_prior,
    run_em_fitting,
)


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


def _add_user(db, uid: str) -> User:
    u = User(
        user_id=uid,
        display_name=uid,
        email=f"{uid}@test.com",
        hashed_password="x",
        role=UserRole.STUDENT,
    )
    db.add(u)
    db.flush()
    return u


def _add_question(db, qid: str, topic: str = "oral_pathology") -> Question:
    q = Question(
        question_id=qid,
        question_type=QuestionType.MCQ,
        question_text="Q?",
        topic_id=topic,
        competency_areas=[],
        bloom_level="remember",
        difficulty="medium",
        safety_category="non_critical",
        max_score=1.0,
    )
    db.add(q)
    db.flush()
    return q


def _add_attempt(db, user_id: str) -> QuizAttempt:
    attempt = QuizAttempt(user_id=user_id)
    db.add(attempt)
    db.flush()
    return attempt


def _add_answer(db, attempt_id: int, question_id: int, correct: bool) -> QuizAnswer:
    ans = QuizAnswer(
        attempt_id=attempt_id,
        question_id=question_id,
        student_response_text="ans",
        auto_score=1 if correct else 0,
        instructor_score=None,
        grading_status=GradingStatus.GRADED,
    )
    db.add(ans)
    db.flush()
    return ans


# ── _forward_backward tests ───────────────────────────────────────────────────


class TestForwardBackward:
    def test_gamma_in_unit_interval(self):
        seq = [1, 0, 1, 1, 0, 1, 0, 0, 1, 1]
        gamma, ll = _forward_backward(seq, 0.2, 0.1, 0.1, 0.2)
        assert len(gamma) == len(seq)
        for g in gamma:
            assert 0.0 <= g <= 1.0, f"gamma={g} out of [0,1]"
        assert math.isfinite(ll)

    def test_all_correct_increases_mastery(self):
        seq = [1] * 20
        gamma, ll = _forward_backward(seq, 0.2, 0.3, 0.05, 0.2)
        # Mastery should be higher at end than start for all-correct sequence
        assert gamma[-1] > gamma[0]
        assert math.isfinite(ll)

    def test_all_wrong_low_guess_yields_low_mastery(self):
        # All wrong + very low guess (0.05) → P(correct | unmastered) is tiny
        # so consistent wrong answers strongly indicate unmastered state
        seq = [0] * 20
        gamma, ll = _forward_backward(seq, 0.5, 0.05, 0.05, 0.05)
        # Final mastery should be well below initial prior of 0.5
        assert gamma[-1] < 0.3
        assert math.isfinite(ll)

    def test_length_1_sequence(self):
        gamma, ll = _forward_backward([1], 0.3, 0.1, 0.1, 0.2)
        assert len(gamma) == 1
        assert 0.0 <= gamma[0] <= 1.0
        assert math.isfinite(ll)

    def test_empty_sequence_returns_empty(self):
        gamma, ll = _forward_backward([], 0.2, 0.1, 0.1, 0.2)
        assert gamma == []
        assert ll == 0.0


# ── fit_topic_em tests ────────────────────────────────────────────────────────


class TestFitTopicEM:
    def test_converges_on_all_correct(self):
        """All-correct sequences → slip should go near floor, guess near ceil."""
        seqs = [[1] * 15 for _ in range(20)]
        params, ll, converged, n_iter = fit_topic_em(seqs, max_iter=100)
        assert converged
        assert math.isfinite(ll)
        assert params.p_slip < 0.15  # should learn low slip

    def test_returns_valid_params(self):
        seqs = [[1, 0, 1, 0, 1] * 4 for _ in range(10)]
        params, ll, converged, n_iter = fit_topic_em(seqs)
        for attr in ("p_init", "p_transit", "p_slip", "p_guess"):
            v = getattr(params, attr)
            assert 0.0 < v < 1.0, f"{attr}={v} out of (0,1)"
        assert math.isfinite(ll)
        assert n_iter >= 1

    def test_empty_sequences_list(self):
        """Empty list should not raise and returns valid EMParams."""
        params, ll, converged, n_iter = fit_topic_em([])
        assert isinstance(params, EMParams)
        assert n_iter >= 1

    def test_single_student_single_obs(self):
        params, ll, converged, n_iter = fit_topic_em([[1]])
        assert isinstance(params, EMParams)

    @pytest.mark.slow
    def test_recovers_transit_probability(self):
        """
        Generate synthetic sequences with known P(T)=0.25 and verify that
        EM recovers P(T) within |Δ| < 0.15.

        Uses 30 students × 20 observations each.
        """
        import random

        rng = random.Random(42)
        TRUE_TRANSIT = 0.25
        TRUE_SLIP = 0.08
        TRUE_GUESS = 0.15

        seqs = []
        for _ in range(30):
            mastered = False
            seq = []
            for _ in range(20):
                if not mastered and rng.random() < TRUE_TRANSIT:
                    mastered = True
                if mastered:
                    obs = 0 if rng.random() < TRUE_SLIP else 1
                else:
                    obs = 1 if rng.random() < TRUE_GUESS else 0
                seq.append(obs)
            seqs.append(seq)

        params, ll, converged, _ = fit_topic_em(seqs, max_iter=200)
        assert abs(params.p_transit - TRUE_TRANSIT) < 0.15, (
            f"P(T) recovery failed: got {params.p_transit:.4f}, expected ~{TRUE_TRANSIT}"
        )


# ── run_em_fitting tests ──────────────────────────────────────────────────────


class TestRunEMFitting:
    def test_dry_run_does_not_write_db(self, db):
        summary = run_em_fitting(db, dry_run=True)
        assert summary.dry_run is True
        # No rows should be written
        assert db.query(BKTTopicPrior).count() == 0

    def test_no_data_returns_empty_summary(self, db):
        summary = run_em_fitting(db, dry_run=False)
        assert summary.n_topics_total == 0
        assert summary.n_topics_fitted == 0
        assert summary.n_topics_synthetic == 0
        assert summary.results == []

    def test_below_threshold_writes_synthetic_row(self, db):
        """2 students < min_students=5 → is_synthetic=True."""
        u1 = _add_user(db, "u1")
        u2 = _add_user(db, "u2")
        q = _add_question(db, "q1", topic="oral_pathology")

        for uid in [u1.user_id, u2.user_id]:
            attempt = _add_attempt(db, uid)
            for correct in [True, False, True]:
                _add_answer(db, attempt.id, q.id, correct)

        db.flush()
        summary = run_em_fitting(db, min_students=5, min_observations=20, dry_run=False)
        db.commit()

        assert summary.n_topics_synthetic == 1
        assert summary.n_topics_fitted == 0

        row = db.query(BKTTopicPrior).filter_by(topic_id="oral_pathology").first()
        assert row is not None
        assert row.is_synthetic is True
        assert row.p_init == pytest.approx(BKT_P_INIT)
        assert row.p_transit == pytest.approx(BKT_P_TRANSIT)

    def test_above_threshold_writes_fitted_row(self, db):
        """6 students, 5 obs each = 30 obs ≥ min — should run EM and write real row."""
        q = _add_question(db, "q_fit", topic="infectious_diseases")
        for i in range(6):
            u = _add_user(db, f"fit_u{i}")
            attempt = _add_attempt(db, u.user_id)
            for correct in [True, False, True, True, False]:
                _add_answer(db, attempt.id, q.id, correct)

        db.flush()
        summary = run_em_fitting(db, min_students=5, min_observations=20, dry_run=False)
        db.commit()

        assert summary.n_topics_fitted == 1
        row = db.query(BKTTopicPrior).filter_by(topic_id="infectious_diseases").first()
        assert row is not None
        assert row.is_synthetic is False
        assert 0.0 < row.p_transit < 1.0
        assert 0.0 < row.p_slip < 1.0
        assert 0.0 < row.p_guess < 1.0

    def test_upsert_updates_existing_row(self, db):
        """Running EM twice for the same topic updates the existing row."""
        q = _add_question(db, "q_upsert", topic="traumatic")
        for i in range(6):
            u = _add_user(db, f"up_u{i}")
            attempt = _add_attempt(db, u.user_id)
            for correct in [True, True, False, True, True]:
                _add_answer(db, attempt.id, q.id, correct)

        db.flush()
        run_em_fitting(db, min_students=5, min_observations=20, dry_run=False)
        db.commit()

        first_count = db.query(BKTTopicPrior).filter_by(topic_id="traumatic").count()
        assert first_count == 1

        run_em_fitting(db, min_students=5, min_observations=20, dry_run=False)
        db.commit()

        second_count = db.query(BKTTopicPrior).filter_by(topic_id="traumatic").count()
        assert second_count == 1  # still one row, not two

    def test_run_id_is_unique_per_run(self, db):
        q = _add_question(db, "q_rid", topic="oral_pathology")
        for i in range(6):
            u = _add_user(db, f"rid_u{i}")
            attempt = _add_attempt(db, u.user_id)
            for correct in [True, False, True, True, False]:
                _add_answer(db, attempt.id, q.id, correct)

        db.flush()
        s1 = run_em_fitting(db, min_students=5, min_observations=20, dry_run=False)
        db.commit()
        s2 = run_em_fitting(db, min_students=5, min_observations=20, dry_run=False)
        db.commit()

        assert s1.run_id != s2.run_id


# ── get_topic_prior tests ─────────────────────────────────────────────────────


class TestGetTopicPrior:
    def test_unknown_topic_returns_global_defaults(self, db):
        prior = get_topic_prior(db, "nonexistent_topic")
        assert prior.p_init == pytest.approx(BKT_P_INIT)
        assert prior.p_transit == pytest.approx(BKT_P_TRANSIT)
        assert prior.p_slip == pytest.approx(BKT_P_SLIP)
        assert prior.p_guess == pytest.approx(BKT_P_GUESS)

    def test_synthetic_row_returns_global_defaults(self, db):
        db.add(
            BKTTopicPrior(
                topic_id="synth_topic",
                p_init=BKT_P_INIT,
                p_transit=BKT_P_TRANSIT,
                p_slip=BKT_P_SLIP,
                p_guess=BKT_P_GUESS,
                n_students=2,
                n_observations=5,
                log_likelihood=None,
                converged=False,
                is_synthetic=True,
                calibration_run_id="run-001",
                fitted_at=datetime.datetime.utcnow(),
            )
        )
        db.commit()
        prior = get_topic_prior(db, "synth_topic")
        # Synthetic rows are excluded → returns global defaults
        assert prior.p_init == pytest.approx(BKT_P_INIT)

    def test_fitted_row_returns_fitted_values(self, db):
        db.add(
            BKTTopicPrior(
                topic_id="fitted_topic",
                p_init=0.35,
                p_transit=0.22,
                p_slip=0.07,
                p_guess=0.18,
                n_students=10,
                n_observations=100,
                log_likelihood=-42.5,
                converged=True,
                is_synthetic=False,
                calibration_run_id="run-002",
                fitted_at=datetime.datetime.utcnow(),
            )
        )
        db.commit()
        prior = get_topic_prior(db, "fitted_topic")
        assert prior.p_init == pytest.approx(0.35)
        assert prior.p_transit == pytest.approx(0.22)
        assert prior.p_slip == pytest.approx(0.07)
        assert prior.p_guess == pytest.approx(0.18)

    def test_topic_id_canonicalised(self, db):
        """get_topic_prior strips and lowercases the topic_id."""
        db.add(
            BKTTopicPrior(
                topic_id="oral_pathology",
                p_init=0.30,
                p_transit=0.15,
                p_slip=0.08,
                p_guess=0.12,
                n_students=10,
                n_observations=80,
                log_likelihood=-30.0,
                converged=True,
                is_synthetic=False,
                calibration_run_id="run-003",
                fitted_at=datetime.datetime.utcnow(),
            )
        )
        db.commit()
        prior = get_topic_prior(db, "  Oral_Pathology  ")
        assert prior.p_transit == pytest.approx(0.15)
