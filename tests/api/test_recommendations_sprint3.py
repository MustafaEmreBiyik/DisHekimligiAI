"""Sprint 3 recommendation API tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.api.routers import recommendations as recommendations_router
from db.database import (
    Base,
    ChatLog,
    RecommendationSnapshot,
    StudentSession,
    User,
    UserRole,
)


@pytest.fixture
def recommendations_client(tmp_path):
    db_file = tmp_path / "recommendations_test.db"
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
    app.include_router(recommendations_router.router, prefix="/api/recommendations")
    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as client:
        yield client, testing_session_local

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_user(db_factory, user_id: str, role: UserRole, is_archived: bool = False) -> None:
    db = db_factory()
    try:
        db.add(
            User(
                user_id=user_id,
                display_name=user_id,
                email=f"{user_id}@example.com",
                hashed_password="hashed",
                role=role,
                is_archived=is_archived,
                archived_at=None,
            )
        )
        db.commit()
    finally:
        db.close()


def _create_session_with_critical_violation(db_factory, student_id: str, case_id: str) -> None:
    db = db_factory()
    try:
        session = StudentSession(
            student_id=student_id,
            case_id=case_id,
            current_score=10.0,
            state_json="{}",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        db.add(
            ChatLog(
                session_id=session.id,
                role="assistant",
                content="critical event",
                metadata_json={
                    "score": -20,
                    "interpreted_action": "prescribe_antibiotics",
                    "silent_evaluation": {"safety_violation": True},
                },
            )
        )
        db.commit()
    finally:
        db.close()


def _token(user_id: str, role: UserRole) -> str:
    return deps.create_access_token(
        user_id=user_id,
        role=role,
        display_name=user_id,
    )


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_recommendations_me_student_only_and_snapshot_written(recommendations_client):
    client, db_factory = recommendations_client
    _create_user(db_factory, user_id="student_r", role=UserRole.STUDENT)
    _create_user(db_factory, user_id="inst_r", role=UserRole.INSTRUCTOR)

    _create_session_with_critical_violation(db_factory, student_id="student_r", case_id="herpes_primary_01")

    student_response = client.get(
        "/api/recommendations/me",
        headers=_auth_header(_token("student_r", UserRole.STUDENT)),
    )
    assert student_response.status_code == 200
    payload = student_response.json()

    assert payload["meta"]["algorithm_version"] == "v1_competency_based"
    assert payload["meta"]["cold_start"] is False
    assert 0 < len(payload["recommendations"]) <= 5

    first = payload["recommendations"][0]
    assert first["reason_code"] in {
        "weak_competency",
        "not_attempted",
        "difficulty_match",
        "cold_start",
    }
    assert isinstance(first["priority_score"], int)

    db = db_factory()
    try:
        snapshots = db.query(RecommendationSnapshot).filter_by(user_id="student_r").all()
        assert len(snapshots) == len(payload["recommendations"])
        assert all(s.algorithm_version == "v1_competency_based" for s in snapshots)
    finally:
        db.close()

    instructor_response = client.get(
        "/api/recommendations/me",
        headers=_auth_header(_token("inst_r", UserRole.INSTRUCTOR)),
    )
    assert instructor_response.status_code == 403


def test_recommendations_me_cold_start_prioritizes_beginner(recommendations_client):
    client, db_factory = recommendations_client
    _create_user(db_factory, user_id="student_cold", role=UserRole.STUDENT)

    response = client.get(
        "/api/recommendations/me",
        headers=_auth_header(_token("student_cold", UserRole.STUDENT)),
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["meta"]["cold_start"] is True
    assert len(payload["recommendations"]) > 0

    # Cold start fallback reason should be explicit for all top recommendations.
    assert all(item["reason_code"] == "cold_start" for item in payload["recommendations"])

    # If beginner cases exist, they must be prioritized first.
    first_difficulty = payload["recommendations"][0]["difficulty"]
    difficulties = {item["difficulty"] for item in payload["recommendations"]}
    if "beginner" in difficulties:
        assert first_difficulty == "beginner"


def test_archived_user_cannot_access_recommendations(recommendations_client):
    client, db_factory = recommendations_client
    _create_user(db_factory, user_id="student_archived", role=UserRole.STUDENT, is_archived=True)

    response = client.get(
        "/api/recommendations/me",
        headers=_auth_header(_token("student_archived", UserRole.STUDENT)),
    )
    assert response.status_code == 401
