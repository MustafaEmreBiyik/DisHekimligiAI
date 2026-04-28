"""Sprint 7 student case runtime tests for DB-first behavior."""

from __future__ import annotations

import datetime
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.api.routers import cases as cases_router
from app.scenario_manager import ScenarioManager
from db.database import Base, CaseDefinition, StudentSession

@pytest.fixture
def cases_client(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
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
    app.include_router(cases_router.router, prefix="/api/cases")
    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[cases_router.get_db] = override_get_db
    app.dependency_overrides[cases_router.get_current_user] = lambda: "student_case_tester"

    manager = ScenarioManager(
        session_factory=testing_session_local,
        allow_json_fallback=False,
    )
    monkeypatch.setattr(cases_router, "scenario_manager", manager)

    with TestClient(app) as client:
        yield client, testing_session_local, manager

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_case(
    db_factory,
    *,
    case_id: str,
    title: str,
    is_active: bool = True,
    source_payload: dict | None = None,
    patient_info: dict | None = None,
) -> None:
    db = db_factory()
    try:
        db.add(
            CaseDefinition(
                case_id=case_id,
                schema_version="2.0",
                title=title,
                category="oral_pathology",
                difficulty="beginner",
                estimated_duration_minutes=20,
                is_active=is_active,
                learning_objectives=["obj"],
                prerequisite_competencies=["pre"],
                competency_tags=["clinical_reasoning"],
                initial_state="consultation",
                states_json={"consultation": {}},
                patient_info_json=patient_info or {"age": 33, "chief_complaint": "Agri"},
                source_payload=source_payload or {"case_id": case_id, "title": title},
                is_archived=False,
                archived_at=None,
            )
        )
        db.commit()
    finally:
        db.close()


def _create_session(db_factory, *, student_id: str, case_id: str, current_score: float) -> int:
    db = db_factory()
    try:
        session = StudentSession(
            student_id=student_id,
            case_id=case_id,
            current_score=current_score,
            state_json=json.dumps({"case_id": case_id}, ensure_ascii=False),
            start_time=datetime.datetime.utcnow(),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id
    finally:
        db.close()


def test_cases_router_prefers_db_catalog_over_json_fallback(cases_client):
    client, db_factory, manager = cases_client
    manager._json_case_data = [
        {
            "case_id": "json_case_01",
            "title": "JSON Fallback Case",
            "category": "oral_pathology",
            "difficulty": "advanced",
            "initial_state": "consultation",
            "patient_info": {"age": 99, "chief_complaint": "Fallback"},
            "is_active": True,
        }
    ]
    manager._json_default_case_id = "json_case_01"

    _create_case(
        db_factory,
        case_id="db_case_01",
        title="DB Live Case",
        patient_info={"age": 42, "gender": "Kadin", "chief_complaint": "Canli katalog"},
        source_payload={
            "case_id": "db_case_01",
            "title": "Stale Payload Title",
            "category": "legacy",
            "difficulty": "advanced",
            "patient_info": {"age": 18, "chief_complaint": "Old"},
            "correct_diagnosis": "Should stay hidden",
        },
    )

    list_response = client.get("/api/cases")
    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "case_id": "db_case_01",
            "name": "DB Live Case",
            "difficulty": "beginner",
            "category": "oral_pathology",
            "patient": {
                "age": 42,
                "gender": "Kadin",
                "chief_complaint": "Canli katalog",
            },
        }
    ]

    detail_response = client.get("/api/cases/db_case_01")
    assert detail_response.status_code == 200
    payload = detail_response.json()
    assert payload["name"] == "DB Live Case"
    assert payload["correct_diagnosis"] is None


def test_cases_router_json_fallback_is_opt_in(cases_client, monkeypatch):
    client, _db_factory, _manager = cases_client
    fallback_cases = [
        {
            "case_id": "json_case_02",
            "title": "Seed Fallback Case",
            "category": "oral_pathology",
            "difficulty": "intermediate",
            "initial_state": "consultation",
            "patient_info": {"age": 27, "chief_complaint": "Seed import source"},
            "is_active": True,
        }
    ]

    disabled_manager = ScenarioManager(
        session_factory=cases_router.scenario_manager._session_factory,
        allow_json_fallback=False,
    )
    disabled_manager._json_case_data = list(fallback_cases)
    disabled_manager._json_default_case_id = "json_case_02"
    monkeypatch.setattr(cases_router, "scenario_manager", disabled_manager)

    no_fallback_list = client.get("/api/cases")
    assert no_fallback_list.status_code == 200
    assert no_fallback_list.json() == []

    no_fallback_start = client.post("/api/cases/json_case_02/start")
    assert no_fallback_start.status_code == 404

    enabled_manager = ScenarioManager(
        session_factory=cases_router.scenario_manager._session_factory,
        allow_json_fallback=True,
    )
    enabled_manager._json_case_data = list(fallback_cases)
    enabled_manager._json_default_case_id = "json_case_02"
    monkeypatch.setattr(cases_router, "scenario_manager", enabled_manager)

    fallback_list = client.get("/api/cases")
    assert fallback_list.status_code == 200
    assert fallback_list.json()[0]["case_id"] == "json_case_02"

    fallback_start = client.post("/api/cases/json_case_02/start")
    assert fallback_start.status_code == 201
    assert fallback_start.json()["case_id"] == "json_case_02"


def test_start_session_resumes_existing_session_for_inactive_case(cases_client):
    client, db_factory, _manager = cases_client
    _create_case(
        db_factory,
        case_id="inactive_case_01",
        title="Inactive Case",
        is_active=False,
    )
    session_id = _create_session(
        db_factory,
        student_id="student_case_tester",
        case_id="inactive_case_01",
        current_score=17.5,
    )

    response = client.post("/api/cases/inactive_case_01/start")
    assert response.status_code == 201
    assert response.json() == {
        "session_id": session_id,
        "case_id": "inactive_case_01",
        "current_score": 17.5,
        "is_active": True,
    }
