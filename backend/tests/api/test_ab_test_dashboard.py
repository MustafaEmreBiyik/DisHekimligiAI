"""Tests for A/B test dashboard endpoints on the instructor router (Sprint 14 T06)."""

from __future__ import annotations

import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.api.routers import instructor as instructor_router
from app.services.ab_test_service import ACTIVE_EXPERIMENTS
from db.database import (
    Base,
    ExperimentAssignment,
    MasteryState,
    QuizAttempt,
    StudentSession,
    User,
    UserRole,
)


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def ab_client(tmp_path):
    db_file = tmp_path / "ab_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(instructor_router.router, prefix="/api/instructor")
    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[instructor_router.get_db] = override_get_db

    with TestClient(app) as client:
        yield client, testing_session_local

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _token(user_id: str, role: UserRole) -> str:
    return deps.create_access_token(user_id=user_id, role=role, display_name=user_id)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _add_user(db_factory, *, user_id: str, role: UserRole) -> None:
    db = db_factory()
    try:
        db.add(
            User(
                user_id=user_id,
                display_name=user_id,
                email=f"{user_id}@example.com",
                hashed_password="hashed",
                role=role,
                is_archived=False,
            )
        )
        db.commit()
    finally:
        db.close()


def _add_assignment(db_factory, *, user_id: str, experiment_id: str, group_name: str) -> None:
    db = db_factory()
    try:
        db.add(
            ExperimentAssignment(
                user_id=user_id,
                experiment_id=experiment_id,
                group_name=group_name,
                assigned_at=datetime.datetime.utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()


def _add_session(db_factory, *, student_id: str) -> None:
    db = db_factory()
    try:
        db.add(
            StudentSession(
                student_id=student_id,
                case_id="olp_001",
                current_score=75.0,
                state_json="{}",
            )
        )
        db.commit()
    finally:
        db.close()


def _add_mastery(db_factory, *, user_id: str, mastery_prob: float) -> None:
    db = db_factory()
    try:
        db.add(
            MasteryState(
                user_id=user_id,
                topic_id="oral_pathology",
                mastery_prob=mastery_prob,
                updated_at=datetime.datetime.utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()


# ── role guard ────────────────────────────────────────────────────────────────


def test_list_experiments_student_forbidden(ab_client):
    client, db_factory = ab_client
    _add_user(db_factory, user_id="std_1", role=UserRole.STUDENT)
    resp = client.get(
        "/api/instructor/experiments",
        headers=_auth(_token("std_1", UserRole.STUDENT)),
    )
    assert resp.status_code == 403


def test_get_experiment_student_forbidden(ab_client):
    client, db_factory = ab_client
    _add_user(db_factory, user_id="std_2", role=UserRole.STUDENT)
    resp = client.get(
        "/api/instructor/experiments/recsys_ab_2026",
        headers=_auth(_token("std_2", UserRole.STUDENT)),
    )
    assert resp.status_code == 403


# ── list experiments ──────────────────────────────────────────────────────────


def test_list_experiments_returns_registered(ab_client):
    client, db_factory = ab_client
    _add_user(db_factory, user_id="inst_1", role=UserRole.INSTRUCTOR)

    resp = client.get(
        "/api/instructor/experiments",
        headers=_auth(_token("inst_1", UserRole.INSTRUCTOR)),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "experiments" in data
    exp_ids = [e["experiment_id"] for e in data["experiments"]]
    # All ACTIVE_EXPERIMENTS must appear in the list
    for eid in ACTIVE_EXPERIMENTS:
        assert eid in exp_ids


def test_list_experiments_has_required_fields(ab_client):
    client, db_factory = ab_client
    _add_user(db_factory, user_id="inst_2", role=UserRole.INSTRUCTOR)

    resp = client.get(
        "/api/instructor/experiments",
        headers=_auth(_token("inst_2", UserRole.INSTRUCTOR)),
    )
    assert resp.status_code == 200
    for exp in resp.json()["experiments"]:
        assert "experiment_id" in exp
        assert "name" in exp
        assert "groups" in exp
        assert "is_active" in exp


# ── get experiment dashboard ───────────────────────────────────────────────────


def test_get_experiment_unknown_returns_404(ab_client):
    client, db_factory = ab_client
    _add_user(db_factory, user_id="inst_3", role=UserRole.INSTRUCTOR)

    resp = client.get(
        "/api/instructor/experiments/does_not_exist",
        headers=_auth(_token("inst_3", UserRole.INSTRUCTOR)),
    )
    assert resp.status_code == 404


def test_get_experiment_empty_distribution(ab_client):
    """No assignments yet — all groups show 0 users, metrics are None."""
    client, db_factory = ab_client
    _add_user(db_factory, user_id="inst_4", role=UserRole.INSTRUCTOR)

    resp = client.get(
        "/api/instructor/experiments/recsys_ab_2026",
        headers=_auth(_token("inst_4", UserRole.INSTRUCTOR)),
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["experiment_id"] == "recsys_ab_2026"
    assert data["total_assigned"] == 0
    assert isinstance(data["group_distribution"], dict)
    assert isinstance(data["group_metrics"], dict)

    # All declared groups must be present even with 0 users
    for group in data["groups"]:
        assert group in data["group_distribution"]
        assert data["group_distribution"][group] == 0
        assert group in data["group_metrics"]
        assert data["group_metrics"][group]["user_count"] == 0


def test_get_experiment_with_assignments(ab_client):
    """Assigned users → distribution counts are correct."""
    client, db_factory = ab_client
    _add_user(db_factory, user_id="inst_5", role=UserRole.INSTRUCTOR)
    _add_user(db_factory, user_id="s1", role=UserRole.STUDENT)
    _add_user(db_factory, user_id="s2", role=UserRole.STUDENT)
    _add_user(db_factory, user_id="s3", role=UserRole.STUDENT)

    _add_assignment(db_factory, user_id="s1", experiment_id="recsys_ab_2026", group_name="control")
    _add_assignment(db_factory, user_id="s2", experiment_id="recsys_ab_2026", group_name="control")
    _add_assignment(db_factory, user_id="s3", experiment_id="recsys_ab_2026", group_name="treatment_v2")

    resp = client.get(
        "/api/instructor/experiments/recsys_ab_2026",
        headers=_auth(_token("inst_5", UserRole.INSTRUCTOR)),
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_assigned"] == 3
    assert data["group_distribution"]["control"] == 2
    assert data["group_distribution"]["treatment_v2"] == 1
    assert data["group_metrics"]["control"]["user_count"] == 2
    assert data["group_metrics"]["treatment_v2"]["user_count"] == 1


def test_get_experiment_metrics_sessions_and_mastery(ab_client):
    """Session count and avg mastery are reflected in group_metrics."""
    client, db_factory = ab_client
    _add_user(db_factory, user_id="inst_6", role=UserRole.INSTRUCTOR)
    _add_user(db_factory, user_id="s4", role=UserRole.STUDENT)
    _add_user(db_factory, user_id="s5", role=UserRole.STUDENT)

    _add_assignment(db_factory, user_id="s4", experiment_id="recsys_ab_2026", group_name="treatment_v2")
    _add_assignment(db_factory, user_id="s5", experiment_id="recsys_ab_2026", group_name="treatment_v2")

    _add_session(db_factory, student_id="s4")
    _add_session(db_factory, student_id="s5")

    _add_mastery(db_factory, user_id="s4", mastery_prob=0.8)
    _add_mastery(db_factory, user_id="s5", mastery_prob=0.6)

    resp = client.get(
        "/api/instructor/experiments/recsys_ab_2026",
        headers=_auth(_token("inst_6", UserRole.INSTRUCTOR)),
    )
    assert resp.status_code == 200
    data = resp.json()
    metrics = data["group_metrics"]["treatment_v2"]

    assert metrics["total_sessions"] == 2
    assert metrics["avg_mastery"] == pytest.approx(0.7, abs=0.01)


def test_get_experiment_accessible_by_admin(ab_client):
    """ADMIN role can also access the dashboard."""
    client, db_factory = ab_client
    _add_user(db_factory, user_id="admin_1", role=UserRole.ADMIN)

    resp = client.get(
        "/api/instructor/experiments/recsys_ab_2026",
        headers=_auth(_token("admin_1", UserRole.ADMIN)),
    )
    assert resp.status_code == 200
