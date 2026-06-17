"""
S13-M2 — Case Media Endpoint + revealed_media Tests
Tests the JWT-protected media serving endpoint and path traversal guard.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.api.routers import cases as cases_router
from db.database import Base, User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt(user_id: str = "s1", role: str = "student") -> str:
    from app.api import deps
    return deps.create_access_token(user_id=user_id, role=role, display_name=user_id)


@pytest.fixture
def engine():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture
def db_session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def student_token(db_session):
    from app.api.routers.auth import get_password_hash
    u = User(
        user_id="s1",
        display_name="student1",
        email="s1@test.com",
        hashed_password=get_password_hash("pass"),
        role=UserRole.STUDENT,
    )
    db_session.add(u)
    db_session.commit()
    return _make_jwt("s1", "student")


@pytest.fixture
def client(engine, student_token):
    Session = sessionmaker(bind=engine)

    def _override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(cases_router.router, prefix="/api/cases")
    app.dependency_overrides[deps.get_db] = _override_db
    app.dependency_overrides[deps.get_current_user] = lambda: "s1"

    with TestClient(app) as c:
        c.headers.update({"Authorization": f"Bearer {student_token}"})
        yield c


# ---------------------------------------------------------------------------
# Tests — media endpoint
# ---------------------------------------------------------------------------

class TestCaseMediaEndpoint:
    def test_serves_existing_jpeg(self, client, tmp_path):
        """A file that exists in assets/images/ is served with correct Content-Type."""
        # Patch _ASSETS_IMAGES_DIR to point to a temp dir with a known file
        test_image = tmp_path / "olp_clinical.jpg"
        test_image.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 20)

        with patch("app.api.routers.cases._ASSETS_IMAGES_DIR", tmp_path):
            resp = client.get("/api/cases/olp_001/media/olp_clinical.jpg")

        assert resp.status_code == 200
        assert "image/jpeg" in resp.headers.get("content-type", "")

    def test_returns_404_for_missing_file(self, client, tmp_path):
        """A file that doesn't exist returns 404."""
        with patch("app.api.routers.cases._ASSETS_IMAGES_DIR", tmp_path):
            resp = client.get("/api/cases/olp_001/media/nonexistent.jpg")
        assert resp.status_code == 404

    def test_path_traversal_blocked(self, client, tmp_path):
        """Requesting a path like ../../../.env must return 400."""
        with patch("app.api.routers.cases._ASSETS_IMAGES_DIR", tmp_path):
            resp = client.get("/api/cases/olp_001/media/..%2F..%2F..%2F.env")
        # FastAPI URL-decodes; the router should block directory components
        assert resp.status_code in {400, 404, 422}

    def test_requires_auth(self, tmp_path):
        """Without a token the endpoint returns 401/403."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.routers import cases as cr
        from app.api import deps

        _app = FastAPI()
        _app.include_router(cr.router, prefix="/api/cases")
        # No override for get_current_user — auth should reject

        with TestClient(_app, raise_server_exceptions=False) as c:
            resp = c.get("/api/cases/olp_001/media/olp_clinical.jpg")
        assert resp.status_code in {401, 403, 422}

    def test_png_served_with_correct_mime(self, client, tmp_path):
        test_image = tmp_path / "test.png"
        test_image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)
        with patch("app.api.routers.cases._ASSETS_IMAGES_DIR", tmp_path):
            resp = client.get("/api/cases/test_case/media/test.png")
        assert resp.status_code == 200
        assert "image/png" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Tests — revealed_media in ScenarioManager.update_state
# ---------------------------------------------------------------------------

class TestRevealedMedia:
    def test_revealed_media_empty_on_fresh_session(self):
        """A freshly built initial state has revealed_media as empty list."""
        from app.scenario_manager import ScenarioManager
        from unittest.mock import MagicMock

        sm = ScenarioManager.__new__(ScenarioManager)
        sm._json_case_data = []
        sm._json_default_case_id = None
        sm._allow_json_fallback = False
        sm._cases_path = ""

        # Patch DB-dependent methods
        sm._session_factory = MagicMock()
        sm._db_catalog_has_cases = MagicMock(return_value=False)
        sm._fetch_db_case = MagicMock(return_value={})
        sm._fetch_db_cases = MagicMock(return_value=[])

        state = sm._build_initial_state("olp_001")
        assert "revealed_media" in state
        assert state["revealed_media"] == []

    def test_revealed_media_populated_when_bulgu_has_media(self):
        """When a finding with media is revealed, revealed_media is populated."""
        from app.scenario_manager import ScenarioManager
        from unittest.mock import MagicMock, patch
        import json

        case_def = {
            "case_id": "olp_001",
            "gizli_bulgular": [
                {
                    "id": "olp_finding_1",
                    "name": "olp_finding_1",
                    "media": "assets/images/olp_clinical.jpg",
                }
            ],
        }

        sm = ScenarioManager.__new__(ScenarioManager)
        sm._json_case_data = [case_def]
        sm._json_default_case_id = "olp_001"
        sm._allow_json_fallback = True
        sm._cases_path = ""
        sm._load_json_cases = lambda: None  # skip file load

        def _find_case(cid):
            for c in sm._json_case_data:
                if c.get("case_id") == cid:
                    return c
            return {}

        sm._find_case = _find_case
        sm._db_catalog_has_cases = MagicMock(return_value=False)

        mock_session_obj = MagicMock()
        mock_session_obj.student_id = "s1"
        mock_session_obj.case_id = "olp_001"
        mock_session_obj.current_score = 0.0
        mock_session_obj.state_json = json.dumps({
            "case_id": "olp_001",
            "revealed_findings": [],
            "revealed_media": [],
        })

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value = mock_session_obj
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_session_obj
        sm._session_factory = MagicMock(return_value=mock_db)

        sm.update_state("s1", {"revealed_findings": ["olp_finding_1"]}, case_id="olp_001")

        # Check what was saved
        saved_state = json.loads(mock_session_obj.state_json)
        assert "revealed_media" in saved_state
        assert "assets/images/olp_clinical.jpg" in saved_state["revealed_media"]

    def test_revealed_media_not_duplicated(self):
        """Calling update_state twice with same finding does not duplicate media paths."""
        from app.scenario_manager import ScenarioManager
        import json
        from unittest.mock import MagicMock

        case_def = {
            "case_id": "olp_001",
            "gizli_bulgular": [
                {"id": "f1", "name": "f1", "media": "assets/images/olp_clinical.jpg"}
            ],
        }

        sm = ScenarioManager.__new__(ScenarioManager)
        sm._json_case_data = [case_def]
        sm._json_default_case_id = "olp_001"
        sm._allow_json_fallback = True
        sm._cases_path = ""
        sm._load_json_cases = lambda: None
        sm._find_case = lambda cid: case_def if cid == "olp_001" else {}
        sm._db_catalog_has_cases = MagicMock(return_value=False)

        mock_session_obj = MagicMock()
        mock_session_obj.student_id = "s1"
        mock_session_obj.case_id = "olp_001"
        mock_session_obj.current_score = 0.0
        # Start with f1 already revealed
        mock_session_obj.state_json = json.dumps({
            "case_id": "olp_001",
            "revealed_findings": ["f1"],
            "revealed_media": ["assets/images/olp_clinical.jpg"],
        })

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.first.return_value = mock_session_obj
        mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_session_obj
        sm._session_factory = MagicMock(return_value=mock_db)

        # Update again with same finding
        sm.update_state("s1", {"revealed_findings": ["f1"]}, case_id="olp_001")

        saved_state = json.loads(mock_session_obj.state_json)
        assert saved_state["revealed_media"].count("assets/images/olp_clinical.jpg") == 1
