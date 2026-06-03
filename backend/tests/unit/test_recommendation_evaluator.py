"""Sprint 11 T07 — Recommendation Evaluator unit tests.

Verifies:
- Metric helpers: DCG, NDCG, hit-rate, AP — correct values and edge cases.
- Bootstrap CI: deterministic under fixed seed, correct shape.
- _has_positive_outcome: window boundary conditions.
- evaluate(): early-exit paths (window too short, no snapshots, no positive labels).
- generate_report(): both PROMOTE and DO NOT PROMOTE verdicts render cleanly.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest

from app.services.recommendation_evaluator import (
    _ap_at_k,
    _bootstrap_mean_ci,
    _build_outcome_index,
    _dcg_at_k,
    _has_positive_outcome,
    _hit_at_k,
    _ndcg_at_k,
    evaluate,
    generate_report,
)
from db.database import (
    Base,
    ExamResult,
    RecommendationSnapshot,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ---------------------------------------------------------------------------
# DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Metric helpers — DCG / NDCG
# ---------------------------------------------------------------------------

def test_dcg_at_k_perfect_ranking():
    rel = [1.0, 0.0, 0.0]
    # position 0 → log2(2) = 1 → contribution = 1/1 = 1.0
    assert _dcg_at_k(rel, k=3) == pytest.approx(1.0)


def test_dcg_at_k_second_position():
    rel = [0.0, 1.0, 0.0]
    # position 1 → log2(3) ≈ 1.585 → 1/1.585
    expected = 1.0 / math.log2(3)
    assert _dcg_at_k(rel, k=3) == pytest.approx(expected)


def test_ndcg_at_k_perfect_is_one():
    # Only one relevant item at top position → NDCG = 1.0
    rel = [1.0, 0.0, 0.0]
    assert _ndcg_at_k(rel, k=3) == pytest.approx(1.0)


def test_ndcg_at_k_two_relevant_ideal_order():
    # Two relevant items in ideal order → NDCG = 1.0
    rel = [1.0, 1.0, 0.0]
    assert _ndcg_at_k(rel, k=3) == pytest.approx(1.0)


def test_ndcg_at_k_two_relevant_suboptimal_order():
    # Relevant item at position 2 instead of 1 → NDCG < 1.0
    rel = [1.0, 0.0, 1.0]
    ndcg = _ndcg_at_k(rel, k=3)
    assert 0.0 < ndcg < 1.0


def test_ndcg_at_k_no_positive_is_nan():
    rel = [0.0, 0.0, 0.0]
    assert math.isnan(_ndcg_at_k(rel, k=3))


def test_ndcg_truncates_at_k():
    # Positive label is only at position 5, k=3 → should not be counted
    rel = [0.0, 0.0, 0.0, 0.0, 1.0]
    # Ideal ranking: [1,0,0,0,0]; ideal DCG@3 = 1.0; actual DCG@3 = 0.0
    assert _ndcg_at_k(rel, k=3) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Metric helpers — hit-rate
# ---------------------------------------------------------------------------

def test_hit_at_k_found():
    assert _hit_at_k([0.0, 1.0, 0.0], k=3) == 1.0


def test_hit_at_k_not_found():
    assert _hit_at_k([0.0, 0.0, 0.0], k=3) == 0.0


def test_hit_at_k_outside_window():
    # Relevant item is at position 3 (0-indexed), k=3 → not found
    assert _hit_at_k([0.0, 0.0, 0.0, 1.0], k=3) == 0.0


# ---------------------------------------------------------------------------
# Metric helpers — average precision
# ---------------------------------------------------------------------------

def test_ap_at_k_single_hit_position_0():
    # P@1 = 1/1, num_hits=1 → AP = 1.0/1 = 1.0
    assert _ap_at_k([1.0, 0.0, 0.0], k=3) == pytest.approx(1.0)


def test_ap_at_k_single_hit_position_2():
    # P@3 = 1/3, num_hits=1 → AP = (1/3)/1 = 0.333
    assert _ap_at_k([0.0, 0.0, 1.0], k=3) == pytest.approx(1 / 3)


def test_ap_at_k_no_hits_is_nan():
    assert math.isnan(_ap_at_k([0.0, 0.0, 0.0], k=3))


def test_ap_at_k_two_hits():
    # Hits at 0 and 2: P@1=1/1, P@3=2/3 → AP = (1 + 2/3)/2 = 0.833
    ap = _ap_at_k([1.0, 0.0, 1.0], k=3)
    assert ap == pytest.approx((1.0 + 2 / 3) / 2)


# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------

def test_bootstrap_ci_deterministic():
    values = [0.1, 0.2, 0.3, 0.4, 0.5]
    lo1, hi1 = _bootstrap_mean_ci(values, n_boot=200, seed=42)
    lo2, hi2 = _bootstrap_mean_ci(values, n_boot=200, seed=42)
    assert lo1 == lo2
    assert hi1 == hi2


def test_bootstrap_ci_bounds_ordered():
    values = [0.1, 0.2, 0.3, 0.4, 0.5]
    lo, hi = _bootstrap_mean_ci(values, n_boot=500, seed=7)
    assert lo <= hi


def test_bootstrap_ci_empty_returns_nan():
    lo, hi = _bootstrap_mean_ci([])
    assert math.isnan(lo) and math.isnan(hi)


def test_bootstrap_ci_all_nan_returns_nan():
    lo, hi = _bootstrap_mean_ci([float("nan"), float("nan")])
    assert math.isnan(lo) and math.isnan(hi)


def test_bootstrap_ci_positive_mean_excludes_zero():
    # All-positive deltas → CI should exclude zero
    values = [0.15, 0.18, 0.20, 0.22, 0.17, 0.19, 0.21, 0.16, 0.20, 0.18]
    lo, hi = _bootstrap_mean_ci(values, n_boot=1000, seed=0)
    assert lo > 0.0, f"CI [{lo:.4f}, {hi:.4f}] should exclude zero for all-positive deltas"


# ---------------------------------------------------------------------------
# _has_positive_outcome — window boundary
# ---------------------------------------------------------------------------

def test_has_positive_outcome_within_window():
    asof = datetime(2025, 1, 1, 12, 0, 0)
    completion_ts = datetime(2025, 1, 10, 12, 0, 0)  # 9 days later — within 14d
    index = {("u1", "case_A"): [completion_ts]}
    assert _has_positive_outcome("u1", "case_A", asof, index) is True


def test_has_positive_outcome_exactly_at_cutoff_excluded():
    asof = datetime(2025, 1, 1, 12, 0, 0)
    completion_ts = asof + timedelta(days=14)  # exactly at cutoff → excluded
    index = {("u1", "case_A"): [completion_ts]}
    assert _has_positive_outcome("u1", "case_A", asof, index) is False


def test_has_positive_outcome_before_asof_excluded():
    asof = datetime(2025, 1, 10, 0, 0, 0)
    completion_ts = datetime(2025, 1, 5, 0, 0, 0)  # before asof
    index = {("u1", "case_A"): [completion_ts]}
    assert _has_positive_outcome("u1", "case_A", asof, index) is False


def test_has_positive_outcome_missing_user():
    index = {}
    asof = datetime(2025, 1, 1)
    assert _has_positive_outcome("u_unknown", "case_X", asof, index) is False


# ---------------------------------------------------------------------------
# evaluate() — early-exit paths
# ---------------------------------------------------------------------------

def test_evaluate_window_too_short_returns_error(db):
    # A 10-day window leaves no room for the 14-day label lag
    result = evaluate(db, window_days=10)
    assert "error" in result
    assert result["n_contexts"] == 0


def test_evaluate_no_snapshots_returns_note(db):
    result = evaluate(db, window_days=60)
    assert result.get("n_contexts", 0) == 0
    assert "note" in result or "error" in result


def test_evaluate_no_positive_labels(db):
    """Snapshots exist but no ExamResults → no positive labels → early exit."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # Insert a v1 snapshot in window (40 days ago)
    snap = RecommendationSnapshot(
        user_id="stu_eval",
        case_id="case_001",
        reason_code="cold_start",
        reason_text="test",
        priority_score=60,
        algorithm_version="v1_competency_based",
        created_at=now - timedelta(days=40),
    )
    db.add(snap)
    db.flush()

    result = evaluate(db, window_days=60)
    # n_contexts_with_positive_label should be 0 or note should indicate no positive labels
    evaluated = result.get("n_contexts_evaluated", 0)
    assert evaluated == 0


# ---------------------------------------------------------------------------
# _build_outcome_index
# ---------------------------------------------------------------------------

def test_build_outcome_index_counts_passing(db):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    exam = ExamResult(
        user_id="stu_idx",
        case_id="case_X",
        score=8.0,
        max_score=10.0,
        completed_at=now - timedelta(days=5),
    )
    db.add(exam)
    db.flush()

    window_start = now - timedelta(days=60)
    window_end = now - timedelta(days=14)

    index = _build_outcome_index(db, {"stu_idx"}, window_start, window_end)
    assert ("stu_idx", "case_X") in index
    assert len(index[("stu_idx", "case_X")]) == 1


def test_build_outcome_index_excludes_failing(db):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    exam = ExamResult(
        user_id="stu_fail",
        case_id="case_Y",
        score=5.0,   # 50% — below 70% threshold
        max_score=10.0,
        completed_at=now - timedelta(days=5),
    )
    db.add(exam)
    db.flush()

    window_start = now - timedelta(days=60)
    window_end = now - timedelta(days=14)

    index = _build_outcome_index(db, {"stu_fail"}, window_start, window_end)
    assert ("stu_fail", "case_Y") not in index


# ---------------------------------------------------------------------------
# generate_report()
# ---------------------------------------------------------------------------

def test_generate_report_error_path():
    result = {"error": "Window too short.", "n_contexts": 0}
    report = generate_report(result)
    assert "Error" in report
    assert "Window too short" in report


def test_generate_report_no_data_path():
    result = {
        "n_contexts": 0,
        "n_contexts_evaluated": 0,
        "note": "No v1 recommendation snapshots found.",
    }
    report = generate_report(result)
    assert "No evaluation possible" in report or "No v1 recommendation snapshots" in report


def test_generate_report_promote_verdict():
    result = {
        "window_days": 60,
        "window_start": "2025-01-01T00:00:00",
        "window_end": "2025-02-15T00:00:00",
        "n_contexts_total": 20,
        "n_contexts_evaluated": 15,
        "active_model_version": "v2_hybrid_xgb_irt_bkt",
        "v1": {"ndcg_at_5": 0.40, "hit_rate_at_5": 0.50, "map_at_10": 0.35},
        "v2": {"ndcg_at_5": 0.46, "hit_rate_at_5": 0.55, "map_at_10": 0.40},
        "delta_ndcg_at_5": 0.06,
        "bootstrap_ci_95": [0.01, 0.11],
        "required_ndcg_for_promotion": 0.44,
        "gate1_ndcg_lift_pass": True,
        "gate2_ci_excludes_zero_pass": True,
        "verdict": "PROMOTE",
    }
    report = generate_report(result)
    assert "PROMOTE" in report
    assert "NDCG@5" in report
    assert "0.4600" in report
    assert "0.4000" in report
    assert "PASS" in report


def test_generate_report_do_not_promote_verdict():
    result = {
        "window_days": 60,
        "window_start": "2025-01-01T00:00:00",
        "window_end": "2025-02-15T00:00:00",
        "n_contexts_total": 20,
        "n_contexts_evaluated": 15,
        "active_model_version": "v2_hybrid_xgb_irt_bkt",
        "v1": {"ndcg_at_5": 0.40, "hit_rate_at_5": 0.50, "map_at_10": 0.35},
        "v2": {"ndcg_at_5": 0.41, "hit_rate_at_5": 0.51, "map_at_10": 0.36},
        "delta_ndcg_at_5": 0.01,
        "bootstrap_ci_95": [-0.03, 0.05],
        "required_ndcg_for_promotion": 0.44,
        "gate1_ndcg_lift_pass": False,
        "gate2_ci_excludes_zero_pass": False,
        "verdict": "DO NOT PROMOTE",
    }
    report = generate_report(result)
    assert "DO NOT PROMOTE" in report
    assert "FAIL" in report


def test_generate_report_contains_markdown_structure():
    result = {
        "window_days": 60,
        "window_start": "2025-01-01T00:00:00",
        "window_end": "2025-02-15T00:00:00",
        "n_contexts_total": 10,
        "n_contexts_evaluated": 8,
        "active_model_version": "v2_hybrid_xgb_irt_bkt",
        "v1": {"ndcg_at_5": 0.30, "hit_rate_at_5": 0.40, "map_at_10": 0.25},
        "v2": {"ndcg_at_5": 0.35, "hit_rate_at_5": 0.45, "map_at_10": 0.30},
        "delta_ndcg_at_5": 0.05,
        "bootstrap_ci_95": [0.01, 0.09],
        "required_ndcg_for_promotion": 0.33,
        "gate1_ndcg_lift_pass": True,
        "gate2_ci_excludes_zero_pass": True,
        "verdict": "PROMOTE",
    }
    report = generate_report(result)
    assert report.startswith("# Sprint 11")
    assert "## Algorithm Comparison" in report
    assert "## Promotion Gates" in report
    assert "| Metric |" in report
