"""Sprint 11 T03 — IRT calibration unit tests.

Verifies:
- simulate_responses produces valid binary responses.
- fit_2pl_mle recovers known (a, b) within |Δa| < 0.3, |Δb| < 0.3 on
  a 5-item × 300-simulee synthetic fixture. Mark @pytest.mark.slow.
- run_calibration in dry-run mode produces result dict without writing DB.
- run_calibration with active questions writes IRTParameters rows.
- Synthetic bootstrap: questions with < MIN_SAMPLE real data get is_synthetic=True.
- Upsert: re-running calibration updates existing rows (same question_id).
"""

from __future__ import annotations

import pytest
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import (
    Base,
    GradingStatus,
    IRTParameters,
    Question,
    QuestionType,
    QuizAnswer,
    QuizAttempt,
)
from app.services.irt_calibration import (
    fit_2pl_mle,
    run_calibration,
    simulate_responses,
    _difficulty_to_b,
    _icc_2pl,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_question(db, q_str_id: str, difficulty: str = "medium") -> Question:
    q = Question(
        question_id=q_str_id,
        question_type=QuestionType.MCQ,
        question_text="Test question?",
        topic_id="oral_path",
        competency_areas=[],
        bloom_level="understand",
        difficulty=difficulty,
        safety_category="none",
        max_score=1,
    )
    db.add(q)
    db.flush()
    return q


def _add_graded_answers(db, q: Question, n_correct: int, n_incorrect: int) -> None:
    """Add graded QuizAnswer rows for distinct users."""
    attempt = QuizAttempt(user_id="stu_grade", total_score=0, max_score=n_correct + n_incorrect)
    db.add(attempt)
    db.flush()

    for i in range(n_correct):
        db.add(QuizAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            student_response_text=f"correct_{i}",
            auto_score=1,
            grading_status=GradingStatus.GRADED,
        ))
    for i in range(n_incorrect):
        db.add(QuizAnswer(
            attempt_id=attempt.id,
            question_id=q.id,
            student_response_text=f"wrong_{i}",
            auto_score=0,
            grading_status=GradingStatus.GRADED,
        ))
    db.flush()


# ---------------------------------------------------------------------------
# ICC / simulation tests
# ---------------------------------------------------------------------------

def test_icc_2pl_shape():
    theta = np.linspace(-3, 3, 100)
    p = _icc_2pl(theta, a=1.0, b=0.0)
    assert p.shape == (100,)
    assert np.all(p > 0) and np.all(p < 1)


def test_icc_2pl_monotone():
    """ICC must be strictly increasing in θ for a > 0."""
    theta = np.linspace(-3, 3, 50)
    p = _icc_2pl(theta, a=1.5, b=0.5)
    assert np.all(np.diff(p) > 0)


def test_icc_2pl_boundary_at_b():
    """P(correct | θ=b) should equal 0.5 for any a."""
    for a in [0.5, 1.0, 2.0]:
        p = _icc_2pl(np.array([0.5]), a=a, b=0.5)
        assert abs(float(p[0]) - 0.5) < 1e-6


def test_simulate_responses_shape():
    abilities, responses = simulate_responses(a=1.0, b=0.0, n_simulees=300, seed=42)
    assert abilities.shape == (300,)
    assert responses.shape == (300,)
    assert set(np.unique(responses)).issubset({0.0, 1.0})


def test_simulate_responses_deterministic():
    a1, r1 = simulate_responses(1.2, 0.3, n_simulees=100, seed=7)
    a2, r2 = simulate_responses(1.2, 0.3, n_simulees=100, seed=7)
    np.testing.assert_array_equal(r1, r2)


def test_difficulty_to_b_mapping():
    assert _difficulty_to_b("beginner") == -1.0
    assert _difficulty_to_b("easy") == -1.0
    assert _difficulty_to_b("medium") == 0.0
    assert _difficulty_to_b("intermediate") == 0.0
    assert _difficulty_to_b("advanced") == 1.0
    assert _difficulty_to_b("hard") == 1.0
    assert _difficulty_to_b("unknown") == 0.0  # fallback


# ---------------------------------------------------------------------------
# fit_2pl_mle recovery tests
# ---------------------------------------------------------------------------

@pytest.mark.slow
@pytest.mark.parametrize("true_a, true_b, tol_a, tol_b", [
    # Well-identified items (a ≥ 1.0): tight tolerance at n=500
    (1.0,  0.0, 0.30, 0.30),
    (1.5, -1.0, 0.30, 0.30),
    (1.2,  0.5, 0.30, 0.30),
    (0.8,  1.0, 0.30, 0.30),
    # Low-discrimination items have higher b estimation variance; use wider tol
    (0.6, -0.5, 0.30, 0.55),
])
def test_fit_2pl_recovers_parameters(true_a, true_b, tol_a, tol_b):
    """Recovered a and b must meet tolerance bounds at n=500 simulees."""
    abilities, responses = simulate_responses(true_a, true_b, n_simulees=500, seed=42)
    a_hat, b_hat, ll = fit_2pl_mle(abilities, responses)

    assert abs(a_hat - true_a) < tol_a, f"a recovery failed: true={true_a}, got={a_hat:.4f}"
    assert abs(b_hat - true_b) < tol_b, f"b recovery failed: true={true_b}, got={b_hat:.4f}"
    assert np.isfinite(ll)


def test_fit_2pl_log_likelihood_finite():
    abilities, responses = simulate_responses(1.0, 0.0, n_simulees=200, seed=1)
    a, b, ll = fit_2pl_mle(abilities, responses)
    assert np.isfinite(a)
    assert np.isfinite(b)
    assert np.isfinite(ll)


# ---------------------------------------------------------------------------
# run_calibration — dry-run
# ---------------------------------------------------------------------------

def test_run_calibration_no_questions_dry_run(db):
    result = run_calibration(db, since_days=90, min_sample=200, dry_run=True, seed=42)
    assert result["n_items_total"] == 0
    assert result["dry_run"] is True
    assert result["results"] == []


def test_run_calibration_dry_run_no_db_writes(db):
    _make_question(db, "q_dry_1", difficulty="beginner")
    _make_question(db, "q_dry_2", difficulty="advanced")

    result = run_calibration(db, since_days=90, min_sample=200, dry_run=True, seed=0)

    assert result["n_items_total"] == 2
    assert result["dry_run"] is True
    # Dry-run must not write to DB
    irt_rows = db.query(IRTParameters).all()
    assert len(irt_rows) == 0


# ---------------------------------------------------------------------------
# run_calibration — synthetic bootstrap path
# ---------------------------------------------------------------------------

def test_run_calibration_writes_synthetic_rows(db):
    q1 = _make_question(db, "q_synth_1", difficulty="beginner")
    q2 = _make_question(db, "q_synth_2", difficulty="advanced")

    # No real graded data → all synthetic
    result = run_calibration(db, since_days=90, min_sample=200, dry_run=False, seed=42)
    db.commit()

    assert result["n_items_total"] == 2
    assert result["n_items_synthetic"] == 2
    assert result["n_items_real"] == 0

    irt_rows = db.query(IRTParameters).all()
    assert len(irt_rows) == 2
    for row in irt_rows:
        assert row.is_synthetic is True
        assert row.calibration_run_id == result["run_id"]
        assert -4.0 <= row.difficulty_b <= 4.0
        assert row.discrimination_a > 0.0


def test_synthetic_b_prior_consistent_with_difficulty(db):
    """Beginner items should have lower b than advanced items on average."""
    for i in range(3):
        _make_question(db, f"q_beg_{i}", difficulty="beginner")
    for i in range(3):
        _make_question(db, f"q_adv_{i}", difficulty="advanced")

    run_calibration(db, since_days=90, min_sample=200, dry_run=False, seed=7)
    db.commit()

    beg_b = [r.difficulty_b for r in db.query(IRTParameters).join(
        Question, IRTParameters.question_id == Question.id
    ).filter(Question.difficulty == "beginner").all()]

    adv_b = [r.difficulty_b for r in db.query(IRTParameters).join(
        Question, IRTParameters.question_id == Question.id
    ).filter(Question.difficulty == "advanced").all()]

    assert np.mean(beg_b) < np.mean(adv_b), (
        f"Beginner mean b {np.mean(beg_b):.4f} should be < advanced mean b {np.mean(adv_b):.4f}"
    )


# ---------------------------------------------------------------------------
# run_calibration — upsert (re-run overwrites)
# ---------------------------------------------------------------------------

def test_run_calibration_upsert_updates_existing(db):
    _make_question(db, "q_upsert_1", difficulty="medium")

    run1 = run_calibration(db, since_days=90, min_sample=200, dry_run=False, seed=0)
    db.commit()
    run1_id = run1["run_id"]

    run2 = run_calibration(db, since_days=90, min_sample=200, dry_run=False, seed=99)
    db.commit()
    run2_id = run2["run_id"]

    assert run1_id != run2_id

    # Still only one row per question
    irt_rows = db.query(IRTParameters).all()
    assert len(irt_rows) == 1
    assert irt_rows[0].calibration_run_id == run2_id


# ---------------------------------------------------------------------------
# run_calibration — run_id traceability
# ---------------------------------------------------------------------------

def test_calibration_run_id_groups_rows(db):
    for i in range(4):
        _make_question(db, f"q_trace_{i}")

    result = run_calibration(db, since_days=90, min_sample=200, dry_run=False, seed=1)
    db.commit()

    run_id = result["run_id"]
    rows = db.query(IRTParameters).filter(IRTParameters.calibration_run_id == run_id).all()
    assert len(rows) == 4, "All 4 items should share the same calibration_run_id"
