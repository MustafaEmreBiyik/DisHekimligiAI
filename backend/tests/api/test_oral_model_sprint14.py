"""Sprint 14-A: oral_model passthrough tests for GET /api/cases/{id}."""

from __future__ import annotations

import json
import datetime

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


SAMPLE_ORAL_MODEL = {
    "model_file": "assets/models/oral_cavity_base.glb",
    "lesion_regions": [
        {
            "region_id": "bukkal_mukoza_sag",
            "label": "Sağ bukkal mukoza",
            "highlight_color": "#e8d5b7",
            "reveal_on": "perform_oral_exam",
        },
        {
            "region_id": "dil_lateral",
            "label": "Dil lateral",
            "highlight_color": "#ffcccc",
            "reveal_on": "perform_oral_exam",
            "highlight_teeth": [14, 15],
            "position": [-0.1, 0.0, 0.25],
        },
    ],
}


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
    app.dependency_overrides[cases_router.get_current_user] = lambda: "student_s14a"

    manager = ScenarioManager(
        session_factory=testing_session_local,
        allow_json_fallback=False,
    )
    monkeypatch.setattr(cases_router, "scenario_manager", manager)

    with TestClient(app) as client:
        yield client, testing_session_local, manager

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_case(db_factory, *, case_id: str, oral_model: dict | None = None) -> None:
    payload = {
        "case_id": case_id,
        "title": f"Test Case {case_id}",
        "category": "oral_pathology",
        "difficulty": "beginner",
        "patient_info": {"age": 30, "chief_complaint": "Test"},
    }
    if oral_model is not None:
        payload["oral_model"] = oral_model

    db = db_factory()
    try:
        db.add(
            CaseDefinition(
                case_id=case_id,
                schema_version="2.0",
                title=f"Test Case {case_id}",
                category="oral_pathology",
                difficulty="beginner",
                estimated_duration_minutes=20,
                is_active=True,
                learning_objectives=[],
                prerequisite_competencies=[],
                competency_tags=[],
                initial_state="consultation",
                states_json={"consultation": {}},
                patient_info_json={"age": 30, "chief_complaint": "Test"},
                source_payload=payload,
                is_archived=False,
                archived_at=None,
            )
        )
        db.commit()
    finally:
        db.close()


def test_oral_model_returned_in_case_detail(cases_client):
    """oral_model with lesion_regions must be present in GET /api/cases/{id} response."""
    client, db_factory, _ = cases_client
    _create_case(db_factory, case_id="olp_test", oral_model=SAMPLE_ORAL_MODEL)

    resp = client.get("/api/cases/olp_test")
    assert resp.status_code == 200

    data = resp.json()
    assert data["case_id"] == "olp_test"
    assert data["oral_model"] is not None, "oral_model must not be null"

    om = data["oral_model"]
    assert om["model_file"] == "assets/models/oral_cavity_base.glb"
    assert len(om["lesion_regions"]) == 2

    lr0 = om["lesion_regions"][0]
    assert lr0["region_id"] == "bukkal_mukoza_sag"
    assert lr0["reveal_on"] == "perform_oral_exam"

    lr1 = om["lesion_regions"][1]
    assert lr1["highlight_teeth"] == [14, 15]
    assert lr1["position"] == [-0.1, 0.0, 0.25]


def test_oral_model_null_when_absent(cases_client):
    """oral_model must be null when the case has none defined."""
    client, db_factory, _ = cases_client
    _create_case(db_factory, case_id="no_model_case", oral_model=None)

    resp = client.get("/api/cases/no_model_case")
    assert resp.status_code == 200
    assert resp.json()["oral_model"] is None


def test_case_not_found_returns_404(cases_client):
    client, _, _ = cases_client
    resp = client.get("/api/cases/nonexistent_xyz")
    assert resp.status_code == 404
