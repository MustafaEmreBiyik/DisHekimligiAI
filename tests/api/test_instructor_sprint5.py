"""Sprint 5 instructor portal backend API tests."""

from __future__ import annotations

import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from app.api.routers import instructor as instructor_router
from db.database import (
    Base,
    CaseDefinition,
    ChatLog,
    CoachHint,
    RecommendationSnapshot,
    StudentSession,
    User,
    UserRole,
    ValidatorAuditLog,
)


@pytest.fixture
def instructor_client(tmp_path):
    db_file = tmp_path / "instructor_test.db"
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


def _create_user(db_factory, *, user_id: str, role: UserRole, archived: bool = False, name: str | None = None):
    db = db_factory()
    try:
        db.add(
            User(
                user_id=user_id,
                display_name=name or user_id,
                email=f"{user_id}@example.com",
                hashed_password="hashed",
                role=role,
                is_archived=archived,
                archived_at=datetime.datetime.utcnow() if archived else None,
            )
        )
        db.commit()
    finally:
        db.close()


def _create_case(db_factory, case_id: str, title: str):
    db = db_factory()
    try:
        db.add(
            CaseDefinition(
                case_id=case_id,
                schema_version="2.0",
                title=title,
                category="general",
                difficulty="beginner",
                estimated_duration_minutes=20,
                is_active=True,
                learning_objectives=[],
                prerequisite_competencies=[],
                competency_tags=["clinical_safety"],
                initial_state="{}",
                states_json={},
                patient_info_json={},
                source_payload={},
                is_archived=False,
                archived_at=None,
            )
        )
        db.commit()
    finally:
        db.close()


def _create_session(db_factory, *, student_id: str, case_id: str, score: float, state_json: str = "{}") -> int:
    db = db_factory()
    try:
        row = StudentSession(
            student_id=student_id,
            case_id=case_id,
            current_score=score,
            state_json=state_json,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row.id
    finally:
        db.close()


def _create_assistant_log(
    db_factory,
    *,
    session_id: int,
    interpreted_action: str,
    score: float,
    safety_violation: bool = False,
):
    db = db_factory()
    try:
        db.add(
            ChatLog(
                session_id=session_id,
                role="assistant",
                content="assistant",
                metadata_json={
                    "score": score,
                    "interpreted_action": interpreted_action,
                    "assessment": {
                        "is_critical_safety_rule": True,
                        "safety_category": "wrong_medication" if safety_violation else None,
                    },
                    "silent_evaluation": {
                        "safety_violation": safety_violation,
                        "missing_critical_steps": ["critical step"] if safety_violation else [],
                        "clinical_accuracy": "low" if safety_violation else "high",
                        "faculty_notes": "review" if safety_violation else "ok",
                    },
                },
                timestamp=datetime.datetime.utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()


def _create_user_log(db_factory, *, session_id: int, content: str):
    db = db_factory()
    try:
        db.add(
            ChatLog(
                session_id=session_id,
                role="user",
                content=content,
                metadata_json=None,
                timestamp=datetime.datetime.utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()


def _create_validator_audit(db_factory, *, session_id: int, safety_violation: bool):
    db = db_factory()
    try:
        db.add(
            ValidatorAuditLog(
                session_id=session_id,
                action="perform_oral_exam",
                validator_used="medgemma",
                safety_violation=safety_violation,
                clinical_accuracy="low" if safety_violation else "high",
                response_time_ms=7,
                error_message=None,
                created_at=datetime.datetime.utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()


def _create_hint(db_factory, *, session_id: int, user_id: str):
    db = db_factory()
    try:
        db.add(
            CoachHint(
                session_id=session_id,
                user_id=user_id,
                hint_level="light_nudge",
                content="ipucu",
                created_at=datetime.datetime.utcnow(),
            )
        )
        db.commit()
    finally:
        db.close()


def _create_snapshot(
    db_factory,
    *,
    user_id: str,
    case_id: str,
    reason_code: str,
    is_spotlight: bool,
):
    db = db_factory()
    try:
        db.add(
            RecommendationSnapshot(
                user_id=user_id,
                case_id=case_id,
                reason_code=reason_code,
                reason_text="reason",
                priority_score=50,
                algorithm_version="v1",
                is_spotlight=is_spotlight,
            )
        )
        db.commit()
    finally:
        db.close()


def _token(user_id: str, role: UserRole) -> str:
    return deps.create_access_token(user_id=user_id, role=role, display_name=user_id)


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_instructor_overview_guard_and_response(instructor_client):
    client, db_factory = instructor_client

    _create_user(db_factory, user_id="inst_1", role=UserRole.INSTRUCTOR, name="Instructor")
    _create_user(db_factory, user_id="std_1", role=UserRole.STUDENT, name="Student One")
    _create_user(db_factory, user_id="std_archived", role=UserRole.STUDENT, archived=True)

    session_id = _create_session(
        db_factory,
        student_id="std_1",
        case_id="herpes_primary_01",
        score=45.0,
        state_json='{"is_finished": true}',
    )
    _create_assistant_log(
        db_factory,
        session_id=session_id,
        interpreted_action="prescribe_antibiotics",
        score=-10,
        safety_violation=True,
    )
    _create_validator_audit(db_factory, session_id=session_id, safety_violation=True)

    student_response = client.get(
        "/api/instructor/overview",
        headers=_auth_header(_token("std_1", UserRole.STUDENT)),
    )
    assert student_response.status_code == 403

    response = client.get(
        "/api/instructor/overview",
        headers=_auth_header(_token("inst_1", UserRole.INSTRUCTOR)),
    )
    assert response.status_code == 200

    payload = response.json()
    assert len(payload["assigned_students"]) == 1
    student_item = payload["assigned_students"][0]
    assert student_item["user_id"] == "std_1"
    assert student_item["risk_level"] == "high"
    assert "clinical_safety" in student_item["weak_competencies"]

    assert len(payload["safety_flags"]) == 1
    assert payload["safety_flags"][0]["flag_type"] == "critical_safety_violation"

    assert "clinical_safety" in payload["competency_summary"]


def test_student_drilldown_and_session_detail(instructor_client):
    client, db_factory = instructor_client

    _create_user(db_factory, user_id="admin_1", role=UserRole.ADMIN)
    _create_user(db_factory, user_id="std_2", role=UserRole.STUDENT, name="Student Two")
    _create_case(db_factory, case_id="herpes_primary_01", title="Primary Herpes")

    session_id = _create_session(
        db_factory,
        student_id="std_2",
        case_id="herpes_primary_01",
        score=82.0,
        state_json='{"is_finished": true}',
    )
    _create_user_log(db_factory, session_id=session_id, content="oral muayene yapiyorum")
    _create_assistant_log(
        db_factory,
        session_id=session_id,
        interpreted_action="perform_oral_exam",
        score=20,
        safety_violation=False,
    )
    _create_hint(db_factory, session_id=session_id, user_id="std_2")
    _create_snapshot(
        db_factory,
        user_id="std_2",
        case_id="herpes_primary_01",
        reason_code="weak_competency",
        is_spotlight=False,
    )

    headers = _auth_header(_token("admin_1", UserRole.ADMIN))

    student_detail = client.get("/api/instructor/students/std_2", headers=headers)
    assert student_detail.status_code == 200
    detail_payload = student_detail.json()

    assert detail_payload["student"]["user_id"] == "std_2"
    assert len(detail_payload["sessions"]) == 1
    assert detail_payload["sessions"][0]["hint_count"] == 1
    assert detail_payload["sessions"][0]["case_title"] == "Primary Herpes"
    assert detail_payload["recommendation_history"][0]["is_spotlight"] is False

    session_detail = client.get(f"/api/instructor/sessions/{session_id}", headers=headers)
    assert session_detail.status_code == 200
    session_payload = session_detail.json()

    assert session_payload["session_id"] == str(session_id)
    assert session_payload["is_finished"] is True
    assert len(session_payload["actions"]) == 1
    assert session_payload["actions"][0]["student_message"] == "oral muayene yapiyorum"
    assert len(session_payload["validator_notes"]) == 1
    assert len(session_payload["coach_hints"]) == 1


def test_spotlight_writes_recommendation_snapshot(instructor_client):
    client, db_factory = instructor_client

    _create_user(db_factory, user_id="inst_2", role=UserRole.INSTRUCTOR)
    _create_user(db_factory, user_id="std_3", role=UserRole.STUDENT)
    _create_case(db_factory, case_id="perio_001", title="Periodontal Case")

    response = client.post(
        "/api/instructor/students/std_3/spotlight",
        json={
            "case_id": "perio_001",
            "reason": "Bu ogrenci klinik guvenlik alaninda zayif.",
        },
        headers=_auth_header(_token("inst_2", UserRole.INSTRUCTOR)),
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["success"] is True
    assert payload["message"] == "Vaka öneri listesine eklendi."

    db = db_factory()
    try:
        snapshots = db.query(RecommendationSnapshot).filter_by(user_id="std_3").all()
        assert len(snapshots) == 1
        row = snapshots[0]
        assert row.case_id == "perio_001"
        assert row.reason_code == "instructor_spotlight"
        assert row.is_spotlight is True
    finally:
        db.close()
