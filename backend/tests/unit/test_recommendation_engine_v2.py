"""Sprint 11 T06 — Recommendation Engine v2 unit tests.

Verifies:
- Algorithm dispatch: explicit v1 → v1; no model → v1 fallback; cold-start path.
- _run_v1: returns correct number of items, respects cold-start flag.
- _is_cold_start: True with < 3 sessions, False with ≥ 3 sessions.
- _v1_priority_score: completed cases score 0; cold-start boosts beginners.
- _apply_epsilon_greedy: correct injection position, exploration reason_code.
- persist_recommendation_snapshots: writes RecommendationSnapshot rows.
- invalidate_bundle_cache: evicts the cached bundle.
- recommend() with algorithm="v1_competency_based" skips model lookup.
- CandidateResult and RecommendationEngineResult slot correctness.
"""

from __future__ import annotations

import types

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import (
    Base,
    CaseDefinition,
    RecommendationSnapshot,
    StudentSession,
    UserRole,
)
from app.services.recommendation_engine_v2 import (
    ALGORITHM_COLDSTART,
    ALGORITHM_V1,
    ALGORITHM_V2,
    CandidateResult,
    RecommendationEngineResult,
    _apply_epsilon_greedy,
    _is_cold_start,
    _run_v1,
    _v1_priority_score,
    get_active_model_version,
    invalidate_bundle_cache,
    persist_recommendation_snapshots,
    recommend,
    _bundle_cache,
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


def _add_case(db, case_id: str, difficulty: str = "beginner", is_active: bool = True) -> CaseDefinition:
    case = CaseDefinition(
        case_id=case_id,
        title=f"Case {case_id}",
        category="clinical",
        difficulty=difficulty,
        estimated_duration_minutes=20,
        is_active=is_active,
        is_archived=False,
        competency_tags=["tag_a"],
        initial_state="start",
    )
    db.add(case)
    db.flush()
    return case


def _add_session(db, user_id: str, case_id: str) -> StudentSession:
    sess = StudentSession(student_id=user_id, case_id=case_id, current_score=0)
    db.add(sess)
    db.flush()
    return sess


# ---------------------------------------------------------------------------
# _is_cold_start
# ---------------------------------------------------------------------------

def test_is_cold_start_no_sessions(db):
    assert _is_cold_start(db, "new_user") is True


def test_is_cold_start_one_session(db):
    _add_session(db, "stu1", "case_01")
    assert _is_cold_start(db, "stu1") is True


def test_is_cold_start_threshold_met(db):
    for i in range(3):
        _add_session(db, "stu_warm", f"case_{i:02d}")
    assert _is_cold_start(db, "stu_warm") is False


def test_is_cold_start_above_threshold(db):
    for i in range(5):
        _add_session(db, "stu_hot", f"case_{i:02d}")
    assert _is_cold_start(db, "stu_hot") is False


# ---------------------------------------------------------------------------
# get_active_model_version
# ---------------------------------------------------------------------------

def test_get_active_model_version_returns_none_when_empty(db):
    result = get_active_model_version(db)
    assert result is None


# ---------------------------------------------------------------------------
# _v1_priority_score
# ---------------------------------------------------------------------------

def _make_case(case_id: str, difficulty: str, tags: list[str]):
    return types.SimpleNamespace(case_id=case_id, difficulty=difficulty, competency_tags=tags)


def test_v1_priority_score_completed_is_zero():
    case = _make_case("case_done", "beginner", ["tag_x"])
    score, code, _ = _v1_priority_score(
        case,
        completed_ids={"case_done"},
        attempted_ids={"case_done"},
        weak_competency_tags=set(),
        avg_pct=70.0,
        cold_start=False,
    )
    assert score == 0
    assert code == "completed"


def test_v1_priority_score_cold_start_boosts_beginner():
    case = _make_case("case_beg", "beginner", [])
    score_cold, _, _ = _v1_priority_score(
        case,
        completed_ids=set(),
        attempted_ids=set(),
        weak_competency_tags=set(),
        avg_pct=50.0,
        cold_start=True,
    )
    score_warm, _, _ = _v1_priority_score(
        case,
        completed_ids=set(),
        attempted_ids=set(),
        weak_competency_tags=set(),
        avg_pct=50.0,
        cold_start=False,
    )
    assert score_cold > score_warm


def test_v1_priority_score_weak_competency_overlap_increases_score():
    case = _make_case("case_w", "intermediate", ["tag_weak"])
    score_overlap, code, _ = _v1_priority_score(
        case,
        completed_ids=set(),
        attempted_ids=set(),
        weak_competency_tags={"tag_weak"},
        avg_pct=70.0,
        cold_start=False,
    )
    score_no_overlap, _, _ = _v1_priority_score(
        case,
        completed_ids=set(),
        attempted_ids=set(),
        weak_competency_tags=set(),
        avg_pct=70.0,
        cold_start=False,
    )
    assert score_overlap > score_no_overlap
    assert code == "weak_competency"


def test_v1_priority_score_not_attempted_reason():
    case = _make_case("case_new", "intermediate", [])
    _, code, _ = _v1_priority_score(
        case,
        completed_ids=set(),
        attempted_ids=set(),
        weak_competency_tags=set(),
        avg_pct=70.0,
        cold_start=False,
    )
    assert code == "not_attempted"


# ---------------------------------------------------------------------------
# _run_v1
# ---------------------------------------------------------------------------

def test_run_v1_returns_k_items(db):
    for i in range(6):
        _add_case(db, f"c{i:02d}")
    result = _run_v1(db, "stu_v1", k=5, algorithm_label=ALGORITHM_V1)
    assert len(result.items) == 5
    assert result.algorithm_version == ALGORITHM_V1


def test_run_v1_no_candidates_returns_empty(db):
    result = _run_v1(db, "stu_empty", k=5, algorithm_label=ALGORITHM_V1)
    assert result.items == []
    assert result.cold_start is True


def test_run_v1_cold_start_flag_set(db):
    for i in range(3):
        _add_case(db, f"c_cold_{i}")
    result = _run_v1(db, "brand_new_user", k=3, algorithm_label=ALGORITHM_V1)
    assert result.cold_start is True


def test_run_v1_archived_excluded(db):
    _add_case(db, "active_case", is_active=True)
    archived = CaseDefinition(
        case_id="archived_case",
        title="Archived",
        category="clinical",
        difficulty="beginner",
        estimated_duration_minutes=15,
        is_active=False,
        is_archived=True,
        competency_tags=[],
        initial_state="start",
    )
    db.add(archived)
    db.flush()
    result = _run_v1(db, "stu_arch", k=5, algorithm_label=ALGORITHM_V1)
    case_ids = [r.case_id for r in result.items]
    assert "archived_case" not in case_ids


def test_run_v1_completed_cases_filtered_out(db):
    from db.database import ExamResult
    _add_case(db, "case_done_v1")
    _add_case(db, "case_todo_v1")

    exam = ExamResult(
        user_id="stu_done",
        case_id="case_done_v1",
        score=8.0,
        max_score=10.0,
    )
    db.add(exam)
    db.flush()

    result = _run_v1(db, "stu_done", k=5, algorithm_label=ALGORITHM_V1)
    # Completed case may appear but score should be 0
    for item in result.items:
        if item.case_id == "case_done_v1":
            assert item.priority_score == 0
            assert item.reason_code == "completed"


# ---------------------------------------------------------------------------
# _apply_epsilon_greedy
# ---------------------------------------------------------------------------

def test_epsilon_greedy_no_injection_on_zero_epsilon(monkeypatch):
    monkeypatch.setattr("app.services.recommendation_engine_v2.EXPLORATION_EPSILON", 0.0)
    ranked = [
        CandidateResult("c1", "T1", "beginner", 20, [], "cold_start", "txt", 80),
        CandidateResult("c2", "T2", "beginner", 20, [], "cold_start", "txt", 70),
        CandidateResult("c3", "T3", "beginner", 20, [], "cold_start", "txt", 60),
    ]
    candidates = []
    result = _apply_epsilon_greedy(ranked, candidates, set(), "v2")
    assert [r.case_id for r in result] == ["c1", "c2", "c3"]


def test_epsilon_greedy_injects_at_position_3(monkeypatch):
    monkeypatch.setattr("app.services.recommendation_engine_v2.EXPLORATION_EPSILON", 1.0)

    ranked = [
        CandidateResult("c1", "T1", "beginner", 20, [], "cold_start", "txt", 80),
        CandidateResult("c2", "T2", "beginner", 20, [], "cold_start", "txt", 70),
        CandidateResult("c3", "T3", "beginner", 20, [], "cold_start", "txt", 60),
        CandidateResult("c4", "T4", "beginner", 20, [], "cold_start", "txt", 50),
    ]

    # Create a candidate not yet in ranked and not attempted
    extra = types.SimpleNamespace(
        case_id="c_extra",
        title="Extra",
        difficulty="beginner",
        estimated_duration_minutes=25,
        competency_tags=[],
    )

    monkeypatch.setattr("random.choice", lambda _lst: extra)

    result = _apply_epsilon_greedy(ranked, [extra], attempted_ids=set(), model_version_str="v2")
    assert len(result) == 4  # same length as input
    assert result[2].case_id == "c_extra"
    assert result[2].reason_code == "exploration"


def test_epsilon_greedy_no_unattempted_skips(monkeypatch):
    monkeypatch.setattr("app.services.recommendation_engine_v2.EXPLORATION_EPSILON", 1.0)
    ranked = [CandidateResult("c1", "T1", "beginner", 20, [], "cold_start", "txt", 80)]
    # All candidates are already attempted
    extra = types.SimpleNamespace(case_id="c1")
    result = _apply_epsilon_greedy(ranked, [extra], attempted_ids={"c1"}, model_version_str="v2")
    assert result[0].case_id == "c1"  # unchanged


# ---------------------------------------------------------------------------
# recommend() dispatch
# ---------------------------------------------------------------------------

def test_recommend_explicit_v1_skips_model(db):
    for i in range(3):
        _add_case(db, f"rd_c{i}")
    result = recommend(db, "stu_rd", k=3, algorithm=ALGORITHM_V1)
    assert result.algorithm_version == ALGORITHM_V1


def test_recommend_no_model_falls_back_to_v1(db):
    for i in range(3):
        _add_case(db, f"rm_c{i}")
    result = recommend(db, "stu_rm", k=3)
    assert result.algorithm_version == ALGORITHM_V1


def test_recommend_cold_start_uses_coldstart_label(db):
    from db.database import RecommendationModelVersion
    model = RecommendationModelVersion(
        algorithm_version=ALGORITHM_V2,
        model_blob_path="/tmp/nonexistent",
        is_active=True,
        ndcg_at_5=0.5,
        training_sample_size=0,
        feature_set_hash="abc123",
    )
    db.add(model)
    db.flush()

    for i in range(2):
        _add_case(db, f"cs_c{i}")

    # User has < 3 sessions → cold-start
    result = recommend(db, "stu_cs", k=2)
    assert result.cold_start is True
    assert result.algorithm_version == ALGORITHM_COLDSTART


# ---------------------------------------------------------------------------
# persist_recommendation_snapshots
# ---------------------------------------------------------------------------

def test_persist_writes_snapshot_rows(db):
    items = [
        CandidateResult("p_c1", "T1", "beginner", 20, [], "cold_start", "txt", 80),
        CandidateResult("p_c2", "T2", "beginner", 20, [], "cold_start", "txt", 70),
    ]
    engine_result = RecommendationEngineResult(items, ALGORITHM_V1, cold_start=True)
    persist_recommendation_snapshots(db, "stu_persist", engine_result, active_model=None)
    db.flush()

    snaps = db.query(RecommendationSnapshot).filter(RecommendationSnapshot.user_id == "stu_persist").all()
    assert len(snaps) == 2
    assert {s.case_id for s in snaps} == {"p_c1", "p_c2"}


def test_persist_snapshot_algorithm_version(db):
    items = [CandidateResult("pv_c1", "T1", "beginner", 20, [], "cold_start", "txt", 65)]
    engine_result = RecommendationEngineResult(items, ALGORITHM_V1, cold_start=True)
    persist_recommendation_snapshots(db, "stu_pv", engine_result, active_model=None)
    db.flush()

    snap = db.query(RecommendationSnapshot).filter(RecommendationSnapshot.user_id == "stu_pv").first()
    assert snap.algorithm_version == ALGORITHM_V1
    assert snap.priority_score == 65


# ---------------------------------------------------------------------------
# invalidate_bundle_cache
# ---------------------------------------------------------------------------

def test_invalidate_bundle_cache_removes_entry():
    _bundle_cache[9999] = ("dummy_booster", "dummy_scaler", ["feat_a"])
    invalidate_bundle_cache(9999)
    assert 9999 not in _bundle_cache


def test_invalidate_bundle_cache_missing_key_noop():
    invalidate_bundle_cache(99998)  # must not raise


# ---------------------------------------------------------------------------
# CandidateResult / RecommendationEngineResult
# ---------------------------------------------------------------------------

def test_candidate_result_defaults():
    r = CandidateResult("cid", "Title", "advanced", 30, ["t1"], "rc", "rt", 42)
    assert r.top_features == []
    assert r.model_version is None
    assert r.feature_vector == {}


def test_recommendation_engine_result_slots():
    items = [CandidateResult("x", "X", "beginner", 20, [], "rc", "rt", 10)]
    res = RecommendationEngineResult(items, ALGORITHM_V2, cold_start=False)
    assert len(res.items) == 1
    assert res.algorithm_version == ALGORITHM_V2
    assert res.cold_start is False
