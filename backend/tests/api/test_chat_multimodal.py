"""
S13-M1 — Multimodal Chat Endpoint Tests
Tests multipart/form-data support, image size validation, and visual_findings_observed extraction.
"""

import io
import json
import types
from unittest.mock import patch, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import deps
from app.api.routers import chat as chat_router
from db.database import Base, User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt(user_id: str = "s1", role: str = "student") -> str:
    """Return a signed JWT for test auth."""
    return deps.create_access_token(user_id=user_id, role=role, display_name=user_id)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
def mock_agent():
    """A pre-built mock DentalEducationAgent that returns a canned result."""
    agent = MagicMock()
    agent.process_student_input.return_value = {
        "student_id": "s1",
        "case_id": "olp_001",
        "llm_interpretation": {
            "intent_type": "ACTION",
            "interpreted_action": "perform_oral_exam",
            "clinical_intent": "diagnosis_gathering",
            "priority": "medium",
            "safety_concerns": [],
            "explanatory_feedback": "Oral muayene yapılıyor.",
            "structured_args": {},
            "visual_findings_observed": [],
        },
        "assessment": {"score": 5.0, "score_change": 5.0, "rule_outcome": "match"},
        "silent_evaluation": {
            "safety_flags": [],
            "missing_critical_steps": [],
            "clinical_accuracy": "high",
            "faculty_notes": "",
            "image_finding_match": None,
            "safety_violation": False,
            "reasoning_deviation": False,
            "audit": {"validator_used": "medgemma", "response_time_ms": 0, "error_message": None, "attempts": 0},
        },
        "final_feedback": "Oral muayene yapılıyor.",
        "llm_safety": {"sanitization": {}, "prompt_injection": {"detected": False}},
        "safety_events": [],
        "updated_state": {
            "case_id": "olp_001",
            "revealed_findings": [],
            "revealed_media": [],
            "current_score": 5.0,
        },
    }
    return agent


@pytest.fixture
def client(engine, student_token, mock_agent):
    Session = sessionmaker(bind=engine)

    def _override_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(chat_router.router, prefix="/api/chat")
    app.dependency_overrides[deps.get_db] = _override_db
    app.dependency_overrides[deps.get_current_user_context] = lambda: MagicMock(
        user_id="s1", role="student"
    )

    with patch("app.api.routers.chat._get_or_create_agent", return_value=mock_agent):
        with TestClient(app) as c:
            c.headers.update({"Authorization": f"Bearer {student_token}"})
            yield c, mock_agent


# ---------------------------------------------------------------------------
# Gemini mock that handles both str and list (multimodal parts) prompts
# ---------------------------------------------------------------------------

def _multimodal_gemini_response(visual_findings: list | None = None):
    """Return a mock Gemini response including visual_findings_observed."""
    payload = {
        "intent_type": "ACTION",
        "interpreted_action": "perform_oral_exam",
        "clinical_intent": "diagnosis_gathering",
        "priority": "high",
        "safety_concerns": [],
        "explanatory_feedback": "Oral muayene yapılıyor.",
        "structured_args": {},
        "visual_findings_observed": visual_findings or ["Wickham striae görülüyor", "Beyaz ağ desenli lezyon"],
    }
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# Tests — existing JSON path (no regression)
# ---------------------------------------------------------------------------

class TestJsonPathNoRegression:
    def test_json_send_returns_200(self, client):
        c, agent = client
        resp = c.post("/api/chat/send", json={"message": "Agiz ici muayene yapiyorum", "case_id": "olp_001"})
        assert resp.status_code == 200
        data = resp.json()
        assert "ai_response" in data
        assert "visual_findings_observed" in data
        assert isinstance(data["visual_findings_observed"], list)

    def test_json_send_has_revealed_media_field(self, client):
        c, agent = client
        resp = c.post("/api/chat/send", json={"message": "Tibbi gecmis aliyorum", "case_id": "olp_001"})
        assert resp.status_code == 200
        assert "revealed_media" in resp.json()
        assert isinstance(resp.json()["revealed_media"], list)


# ---------------------------------------------------------------------------
# Tests — multipart endpoint
# ---------------------------------------------------------------------------

class TestMultipartEndpoint:
    def test_multipart_with_valid_jpeg_returns_200(self, client):
        c, agent = client
        # Set agent to return visual_findings_observed
        agent.process_student_input.return_value["llm_interpretation"]["visual_findings_observed"] = [
            "Wickham striae goruluyor"
        ]
        jpeg_bytes = bytes([0xFF, 0xD8, 0xFF, 0xE0] + [0x00] * 100)
        resp = c.post(
            "/api/chat/send-multipart",
            data={"message": "Oral mukozayi muayene ediyorum", "case_id": "olp_001"},
            files={"image": ("test.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "visual_findings_observed" in data
        assert isinstance(data["visual_findings_observed"], list)

    def test_multipart_visual_findings_populated_when_image_attached(self, client):
        c, agent = client
        agent.process_student_input.return_value["llm_interpretation"]["visual_findings_observed"] = [
            "Wickham striae goruluyor"
        ]
        jpeg_bytes = bytes([0xFF, 0xD8, 0xFF, 0xE0] + [0x00] * 100)
        resp = c.post(
            "/api/chat/send-multipart",
            data={"message": "Oral mukoza muayenesi yapiyorum", "case_id": "olp_001"},
            files={"image": ("test.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")},
        )
        assert resp.status_code == 200
        assert len(resp.json()["visual_findings_observed"]) >= 1

    def test_multipart_no_image_returns_200(self, client):
        c, _ = client
        resp = c.post(
            "/api/chat/send-multipart",
            data={"message": "Muayene yapiyorum", "case_id": "olp_001"},
        )
        assert resp.status_code == 200

    def test_image_over_5mb_returns_413(self, client):
        c, _ = client
        large_image = b"\xFF\xD8\xFF" + b"\x00" * (5 * 1024 * 1024 + 1)
        resp = c.post(
            "/api/chat/send-multipart",
            data={"message": "Test", "case_id": "olp_001"},
            files={"image": ("big.jpg", io.BytesIO(large_image), "image/jpeg")},
        )
        assert resp.status_code == 413

    def test_unsupported_mime_type_returns_415(self, client):
        c, _ = client
        resp = c.post(
            "/api/chat/send-multipart",
            data={"message": "Test", "case_id": "olp_001"},
            files={"image": ("file.gif", io.BytesIO(b"GIF89a"), "image/gif")},
        )
        assert resp.status_code == 415


# ---------------------------------------------------------------------------
# Tests — _normalize_interpretation_payload with visual_findings_observed
# ---------------------------------------------------------------------------

class TestNormalizeVisualFindings:
    def test_visual_findings_extracted_and_truncated(self):
        from app.agent import _normalize_interpretation_payload

        data = {
            "intent_type": "ACTION",
            "interpreted_action": "perform_oral_exam",
            "clinical_intent": "diagnosis_gathering",
            "priority": "medium",
            "safety_concerns": [],
            "explanatory_feedback": "Feedback",
            "structured_args": {},
            "visual_findings_observed": ["Finding 1", "Finding 2", "A" * 200],
        }
        result = _normalize_interpretation_payload(data)
        assert "visual_findings_observed" in result
        assert len(result["visual_findings_observed"]) == 3
        # Each item capped at 120 chars
        assert all(len(f) <= 120 for f in result["visual_findings_observed"])

    def test_visual_findings_max_10_items(self):
        from app.agent import _normalize_interpretation_payload

        data = {
            "intent_type": "ACTION",
            "interpreted_action": "perform_oral_exam",
            "clinical_intent": "diagnosis_gathering",
            "priority": "medium",
            "safety_concerns": [],
            "explanatory_feedback": "Feedback",
            "structured_args": {},
            "visual_findings_observed": [f"Finding {i}" for i in range(15)],
        }
        result = _normalize_interpretation_payload(data)
        assert len(result["visual_findings_observed"]) <= 10

    def test_visual_findings_absent_returns_empty_list(self):
        from app.agent import _normalize_interpretation_payload

        data = {
            "intent_type": "CHAT",
            "interpreted_action": "general_chat",
            "clinical_intent": "other",
            "priority": "low",
            "safety_concerns": [],
            "explanatory_feedback": "Merhaba",
            "structured_args": {},
        }
        result = _normalize_interpretation_payload(data)
        assert result["visual_findings_observed"] == []
