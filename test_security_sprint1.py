"""Sprint 1 security regression tests for backend hardening fixes."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from db import database as database_module
from db.database import Base, ChatLog, StudentSession, User, UserRole


class _DummyAgent:
    """Deterministic in-process chat agent for offline tests."""

    def process_student_input(self, student_id: str, raw_action: str, case_id: str) -> dict:
        return {
            "case_id": case_id,
            "final_feedback": "Muayene notunuza gore oral mukozada retikuler beyaz cizgiler goruyorum.",
            "llm_interpretation": {
                "interpreted_action": "perform_oral_exam",
                "clinical_intent": "diagnosis_gathering",
                "priority": "medium",
            },
            "assessment": {
                "score": 8.0,
                "rule_outcome": "correct_action",
            },
            "silent_evaluation": {
                "is_clinically_accurate": True,
                "safety_violation": False,
                "feedback": "internal_only",
            },
            "updated_state": {
                "is_finished": False,
                "revealed_findings": ["reticular white striae"],
                "current_score": 18.0,
            },
        }


class _DummyReasoningClassifier:
    def classify(self, session_id: int, action_history: list[dict]) -> dict:
        return {
            "pattern": "no_deviation",
            "confidence": 1.0,
        }


@pytest.fixture
def security_client(tmp_path, monkeypatch, mock_external_ai_sdks):
    from app.api.routers import analytics as analytics_router
    from app.api.routers import chat as chat_router

    db_file = tmp_path / "security_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(chat_router, "SessionLocal", testing_session_local)
    monkeypatch.setattr(analytics_router, "SessionLocal", testing_session_local)
    monkeypatch.setattr(database_module, "SessionLocal", testing_session_local)
    monkeypatch.setattr(chat_router, "agent", _DummyAgent())
    monkeypatch.setattr(chat_router, "reasoning_classifier", _DummyReasoningClassifier())

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(chat_router.router, prefix="/api/chat")
    app.include_router(chat_router.sessions_router, prefix="/api")
    app.include_router(analytics_router.router, prefix="/api/analytics")
    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as client:
        yield client, testing_session_local

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_user(db_factory, user_id: str, role: UserRole, display_name: str | None = None) -> None:
    db = db_factory()
    try:
        db.add(
            User(
                user_id=user_id,
                display_name=display_name or user_id,
                email=f"{user_id}@example.com",
                hashed_password="hashed",
                role=role,
                is_archived=False,
                archived_at=None,
            )
        )
        db.commit()
    finally:
        db.close()


def _create_session_with_assistant_log(
    db_factory,
    *,
    student_id: str,
    case_id: str,
    score: float = 12.0,
) -> int:
    db = db_factory()
    try:
        session = StudentSession(
            student_id=student_id,
            case_id=case_id,
            current_score=score,
            state_json="{}",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        db.add(
            ChatLog(
                session_id=session.id,
                role="assistant",
                content="Assistant internal evaluation content",
                metadata_json={
                    "score": 4.0,
                    "interpreted_action": "perform_oral_exam",
                    "assessment": {"score": 4.0, "rule_outcome": "ok"},
                    "silent_evaluation": {
                        "is_clinically_accurate": True,
                        "safety_violation": False,
                        "feedback": "internal_only",
                    },
                    "reasoning_pattern": {"pattern": "no_deviation"},
                },
            )
        )
        db.commit()
        return session.id
    finally:
        db.close()


def _token(user_id: str, role: UserRole, display_name: str | None = None) -> str:
    return deps.create_access_token(
        user_id=user_id,
        role=role,
        display_name=display_name or user_id,
    )


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_fix_a_auth_configuration_validation_success(monkeypatch):
    monkeypatch.setenv("DENTAI_SECRET_KEY", "security-test-secret")
    monkeypatch.setenv("DENTAI_ACCESS_TOKEN_EXPIRE_MINUTES", "90")

    deps.validate_auth_configuration()
    assert deps.get_secret_key() == "security-test-secret"
    assert deps.get_access_token_expire_minutes() == 90


def test_fix_a_missing_secret_key_raises_value_error(monkeypatch):
    monkeypatch.delenv("DENTAI_SECRET_KEY", raising=False)

    with pytest.raises(ValueError, match="DENTAI_SECRET_KEY"):
        deps.validate_auth_configuration()


def test_fix_b_history_owner_guard_success_and_403(security_client):
    client, db_factory = security_client
    _create_user(db_factory, user_id="student_a", role=UserRole.STUDENT)
    _create_user(db_factory, user_id="student_b", role=UserRole.STUDENT)
    _create_user(db_factory, user_id="inst_1", role=UserRole.INSTRUCTOR)

    _create_session_with_assistant_log(db_factory, student_id="student_a", case_id="olp_001")
    _create_session_with_assistant_log(db_factory, student_id="student_b", case_id="olp_001")

    student_token = _token("student_a", UserRole.STUDENT)

    own_history = client.get(
        "/api/chat/history/student_a/olp_001",
        headers=_auth_header(student_token),
    )
    assert own_history.status_code == 200
    own_payload = own_history.json()
    assert own_payload["student_id"] == "student_a"
    assert own_payload["messages"][0]["metadata"] is None

    forbidden_history = client.get(
        "/api/chat/history/student_b/olp_001",
        headers=_auth_header(student_token),
    )
    assert forbidden_history.status_code == 403
    assert forbidden_history.json()["detail"] == "Forbidden"

    instructor_token = _token("inst_1", UserRole.INSTRUCTOR)
    instructor_history = client.get(
        "/api/chat/history/student_b/olp_001",
        headers=_auth_header(instructor_token),
    )
    assert instructor_history.status_code == 200
    assert instructor_history.json()["messages"][0]["metadata"] is not None


def test_fix_c_export_role_guard_and_student_scope(security_client):
    client, db_factory = security_client
    _create_user(db_factory, user_id="student_export", role=UserRole.STUDENT)
    _create_user(db_factory, user_id="instructor_export", role=UserRole.INSTRUCTOR)

    session_id = _create_session_with_assistant_log(
        db_factory,
        student_id="student_export",
        case_id="olp_001",
    )
    assert session_id > 0

    student_token = _token("student_export", UserRole.STUDENT)
    student_export_response = client.get(
        "/api/analytics/export/actions",
        headers=_auth_header(student_token),
    )
    assert student_export_response.status_code == 403
    assert student_export_response.json()["detail"] == "Forbidden"

    student_stats_response = client.get(
        "/api/analytics/student-stats",
        headers=_auth_header(student_token),
    )
    assert student_stats_response.status_code == 200

    instructor_token = _token("instructor_export", UserRole.INSTRUCTOR)
    instructor_export_response = client.get(
        "/api/analytics/export/actions",
        headers=_auth_header(instructor_token),
    )
    assert instructor_export_response.status_code == 200
    assert "log_id" in instructor_export_response.text


def test_fix_d_student_safe_chat_response_and_internal_eval_endpoint(security_client):
    client, db_factory = security_client
    _create_user(db_factory, user_id="student_chat", role=UserRole.STUDENT)
    _create_user(db_factory, user_id="inst_chat", role=UserRole.INSTRUCTOR)

    student_token = _token("student_chat", UserRole.STUDENT)
    send_response = client.post(
        "/api/chat/send",
        json={
            "message": "Agi̇z ici muayene yapiyorum",
            "case_id": "olp_001",
        },
        headers=_auth_header(student_token),
    )
    assert send_response.status_code == 200

    payload = send_response.json()
    assert "ai_response" in payload
    assert "state_updates" in payload
    assert "revealed_findings" in payload
    assert "evaluation" not in payload
    assert "metadata" not in payload
    assert "score" not in payload
    assert "interpreted_action" not in payload

    session_id = payload.get("session_id")
    assert isinstance(session_id, int)

    student_eval_response = client.get(
        f"/api/sessions/{session_id}/evaluation",
        headers=_auth_header(student_token),
    )
    assert student_eval_response.status_code == 403
    assert student_eval_response.json()["detail"] == "Forbidden"

    instructor_token = _token("inst_chat", UserRole.INSTRUCTOR)
    instructor_eval_response = client.get(
        f"/api/sessions/{session_id}/evaluation",
        headers=_auth_header(instructor_token),
    )
    assert instructor_eval_response.status_code == 200
    eval_payload = instructor_eval_response.json()
    assert eval_payload["session_id"] == session_id
    assert len(eval_payload["evaluations"]) >= 1
    assert "assessment" in eval_payload["evaluations"][0]
