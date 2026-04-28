"""
B-7 security regression tests: quiz answer-key hardening.

Verifies that:
- GET /api/quiz/questions never exposes correct_option or explanation.
- POST /api/quiz/submit grades answers server-side and returns only
    student-safe feedback (no answer keys).
- Both endpoints require authentication.
"""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api import deps
from db import database as database_module
from db.database import Base, User, UserRole

_SAMPLE_QUESTIONS = {
    "oral_pathology": [
        {
            "id": "q001",
            "question": "Which lesion carries malignant potential?",
            "options": ["Fibroma", "Leukoplakia", "Epulis", "Mucocele"],
            "correct_option": "Leukoplakia",
            "explanation": "Leukoplakia is a premalignant lesion.",
        },
        {
            "id": "q002",
            "question": "Which condition is caused by Candida albicans?",
            "options": ["Aphthous ulcer", "Oral thrush", "Lichen planus", "Geographic tongue"],
            "correct_option": "Oral thrush",
            "explanation": "Oral thrush (pseudomembranous candidiasis) is caused by Candida albicans.",
        },
    ]
}


@pytest.fixture
def quiz_client(tmp_path, monkeypatch, mock_external_ai_sdks):
    from app.api.routers import quiz as quiz_router

    questions_file = tmp_path / "mcq_questions.json"
    questions_file.write_text(json.dumps(_SAMPLE_QUESTIONS), encoding="utf-8")
    monkeypatch.setattr(quiz_router, "QUESTIONS_FILE", questions_file)

    db_file = tmp_path / "quiz_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(database_module, "SessionLocal", testing_session_local)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(quiz_router.router, prefix="/api/quiz")
    app.dependency_overrides[deps.get_db] = override_get_db

    with TestClient(app) as client:
        yield client, testing_session_local

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def _create_user(db_factory, user_id: str, role: UserRole) -> None:
    db = db_factory()
    try:
        db.add(User(
            user_id=user_id,
            display_name=user_id,
            email=f"{user_id}@example.com",
            hashed_password="hashed",
            role=role,
            is_archived=False,
            archived_at=None,
        ))
        db.commit()
    finally:
        db.close()


def _token(user_id: str, role: UserRole) -> str:
    return deps.create_access_token(user_id=user_id, role=role, display_name=user_id)


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Regression: answer-key leak ───────────────────────────────────────────────

def test_b7_student_questions_no_answer_key(quiz_client):
    """GET /api/quiz/questions must never expose correct_option or explanation."""
    client, db_factory = quiz_client
    _create_user(db_factory, "stu_leak", UserRole.STUDENT)

    resp = client.get("/api/quiz/questions", headers=_auth(_token("stu_leak", UserRole.STUDENT)))
    assert resp.status_code == 200
    questions = resp.json()

    assert len(questions) == 2, "Expected both sample questions"

    for q in questions:
        assert "correct_option" not in q, f"Answer key leaked in question {q['id']!r}"
        assert "explanation" not in q, f"Explanation leaked in question {q['id']!r}"
        assert "answer_key" not in q, f"Answer key alias leaked in question {q['id']!r}"
        # Only the safe fields must be present
        assert set(q.keys()) == {"id", "topic", "question", "options"}


def test_b7_instructor_questions_forbidden(quiz_client):
    """GET /api/quiz/questions is a student endpoint and forbids instructor role."""
    client, db_factory = quiz_client
    _create_user(db_factory, "inst_leak", UserRole.INSTRUCTOR)

    resp = client.get("/api/quiz/questions", headers=_auth(_token("inst_leak", UserRole.INSTRUCTOR)))
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Forbidden"


# ── Server-side grading ───────────────────────────────────────────────────────

def test_b7_submit_wrong_answer_graded_server_side(quiz_client):
    """POST /api/quiz/submit grades server-side and keeps payload student-safe."""
    client, db_factory = quiz_client
    _create_user(db_factory, "stu_wrong", UserRole.STUDENT)

    token = _token("stu_wrong", UserRole.STUDENT)
    resp = client.post(
        "/api/quiz/submit",
        json={"answers": {"q001": "Fibroma"}},  # deliberately wrong
        headers=_auth(token),
    )
    assert resp.status_code == 200
    result = resp.json()

    assert result["score"] == 0
    assert result["total"] == 1
    assert result["percentage"] == 0
    assert isinstance(result["attempt_id"], int)

    qr = result["results"][0]
    assert qr["id"] == "q001"
    assert qr["selected_option"] == "Fibroma"
    assert qr["is_correct"] is False
    assert "feedback" in qr
    assert "correct_option" not in qr
    assert "answer_key" not in qr
    assert "explanation" not in qr
    assert "evaluator_metadata" not in qr
    assert "medgemma" not in str(qr).lower()


def test_b7_wrong_answer_feedback_does_not_leak_explanation_semantics(quiz_client):
    """Wrong-answer feedback must not expose explanation text even if it contains answer strings."""
    client, db_factory = quiz_client
    _create_user(db_factory, "stu_semantic", UserRole.STUDENT)

    token = _token("stu_semantic", UserRole.STUDENT)
    resp = client.post(
        "/api/quiz/submit",
        json={"answers": {"q001": "Fibroma"}},
        headers=_auth(token),
    )
    assert resp.status_code == 200

    qr = resp.json()["results"][0]
    # The source explanation for q001 includes "Leukoplakia"; feedback must not include it.
    assert "Leukoplakia" not in qr["feedback"]
    assert "premalignant" not in qr["feedback"].lower()
    assert "correct_option" not in qr


def test_b7_submit_correct_answer_scores_100(quiz_client):
    """POST /api/quiz/submit with correct answers returns 100% safely."""
    client, db_factory = quiz_client
    _create_user(db_factory, "stu_right", UserRole.STUDENT)

    token = _token("stu_right", UserRole.STUDENT)
    resp = client.post(
        "/api/quiz/submit",
        json={"answers": {"q001": "Leukoplakia", "q002": "Oral thrush"}},
        headers=_auth(token),
    )
    assert resp.status_code == 200
    result = resp.json()

    assert result["score"] == 2
    assert result["total"] == 2
    assert result["percentage"] == 100
    assert "attempt_id" in result
    for qr in result["results"]:
        assert qr["is_correct"] is True
        assert "correct_option" not in qr
        assert "explanation" not in qr


def test_b7_submit_partial_answers_graded_correctly(quiz_client):
    """Submitting only a subset of questions grades only submitted ones."""
    client, db_factory = quiz_client
    _create_user(db_factory, "stu_partial", UserRole.STUDENT)

    token = _token("stu_partial", UserRole.STUDENT)
    resp = client.post(
        "/api/quiz/submit",
        json={"answers": {"q002": "Oral thrush"}},  # only q002
        headers=_auth(token),
    )
    assert resp.status_code == 200
    result = resp.json()

    assert result["total"] == 1
    assert result["score"] == 1
    assert result["results"][0]["id"] == "q002"
    assert "correct_option" not in result["results"][0]


def test_b7_submit_response_schema_is_student_safe(quiz_client):
    """Submit response must not include hidden evaluator objects or answer keys."""
    client, db_factory = quiz_client
    _create_user(db_factory, "stu_schema", UserRole.STUDENT)

    resp = client.post(
        "/api/quiz/submit",
        json={"answers": {"q001": "Fibroma"}},
        headers=_auth(_token("stu_schema", UserRole.STUDENT)),
    )
    assert resp.status_code == 200
    body = resp.json()

    assert set(body.keys()) == {"attempt_id", "score", "total", "percentage", "results"}
    assert isinstance(body["results"], list)
    assert body["results"]
    safe_keys = {"id", "topic", "question", "selected_option", "is_correct", "feedback"}
    assert set(body["results"][0].keys()) == safe_keys
    assert "raw_validator_output" not in body
    assert "evaluation" not in body


def test_b7_student_submit_forbidden_for_instructor_role(quiz_client):
    """POST /api/quiz/submit is a student endpoint and forbids instructor role."""
    client, db_factory = quiz_client
    _create_user(db_factory, "inst_submit", UserRole.INSTRUCTOR)

    resp = client.post(
        "/api/quiz/submit",
        json={"answers": {"q001": "Fibroma"}},
        headers=_auth(_token("inst_submit", UserRole.INSTRUCTOR)),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Forbidden"


def test_b7_attempt_ownership_and_staff_access(quiz_client):
    """Students can only fetch their own attempt; staff can fetch any attempt."""
    client, db_factory = quiz_client
    _create_user(db_factory, "owner_student", UserRole.STUDENT)
    _create_user(db_factory, "other_student", UserRole.STUDENT)
    _create_user(db_factory, "inst_staff", UserRole.INSTRUCTOR)
    _create_user(db_factory, "admin_staff", UserRole.ADMIN)

    owner_submit = client.post(
        "/api/quiz/submit",
        json={"answers": {"q001": "Fibroma"}},
        headers=_auth(_token("owner_student", UserRole.STUDENT)),
    )
    assert owner_submit.status_code == 200
    attempt_id = owner_submit.json()["attempt_id"]

    owner_get = client.get(
        f"/api/quiz/attempts/{attempt_id}",
        headers=_auth(_token("owner_student", UserRole.STUDENT)),
    )
    assert owner_get.status_code == 200
    assert owner_get.json()["attempt_id"] == attempt_id

    forbidden = client.get(
        f"/api/quiz/attempts/{attempt_id}",
        headers=_auth(_token("other_student", UserRole.STUDENT)),
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"] == "Forbidden"

    instructor_get = client.get(
        f"/api/quiz/attempts/{attempt_id}",
        headers=_auth(_token("inst_staff", UserRole.INSTRUCTOR)),
    )
    assert instructor_get.status_code == 200

    admin_get = client.get(
        f"/api/quiz/attempts/{attempt_id}",
        headers=_auth(_token("admin_staff", UserRole.ADMIN)),
    )
    assert admin_get.status_code == 200


def test_b7_attempt_retrieval_sanitizes_tampered_details_json(quiz_client):
    """Attempt retrieval must stay safe even if persisted details_json includes forbidden fields."""
    client, db_factory = quiz_client
    _create_user(db_factory, "tamper_owner", UserRole.STUDENT)
    _create_user(db_factory, "tamper_admin", UserRole.ADMIN)

    submit_resp = client.post(
        "/api/quiz/submit",
        json={"answers": {"q001": "Fibroma"}},
        headers=_auth(_token("tamper_owner", UserRole.STUDENT)),
    )
    assert submit_resp.status_code == 200
    attempt_id = submit_resp.json()["attempt_id"]

    db = db_factory()
    try:
        from db.database import ExamResult

        attempt = db.query(ExamResult).filter(ExamResult.id == attempt_id).first()
        assert attempt is not None
        attempt.details_json = json.dumps(
            {
                "results": [
                    {
                        "id": "q001",
                        "topic": "Oral Patoloji",
                        "question": "Which lesion carries malignant potential?",
                        "selected_option": "Fibroma",
                        "is_correct": False,
                        "feedback": "Safe feedback",
                        "correct_option": "Leukoplakia",
                        "explanation": "Leukoplakia is a premalignant lesion.",
                        "answer_key": "Leukoplakia",
                        "raw_validator_output": {"unsafe": True},
                        "evaluator_metadata": {"model": "medgemma"},
                    }
                ],
                "percentage": 0,
                "evaluation": {"internal": True},
            }
        )
        db.commit()
    finally:
        db.close()

    admin_get = client.get(
        f"/api/quiz/attempts/{attempt_id}",
        headers=_auth(_token("tamper_admin", UserRole.ADMIN)),
    )
    assert admin_get.status_code == 200
    body = admin_get.json()
    qr = body["results"][0]

    assert set(qr.keys()) == {"id", "topic", "question", "selected_option", "is_correct", "feedback"}
    assert "correct_option" not in qr
    assert "explanation" not in qr
    assert "answer_key" not in qr
    assert "raw_validator_output" not in qr
    assert "evaluator_metadata" not in qr
    assert "evaluation" not in body


# ── Auth enforcement ──────────────────────────────────────────────────────────

def test_b7_unauthenticated_questions_returns_401(quiz_client):
    """GET /api/quiz/questions without a token must return 401."""
    client, _ = quiz_client
    assert client.get("/api/quiz/questions").status_code == 401


def test_b7_unauthenticated_submit_returns_401(quiz_client):
    """POST /api/quiz/submit without a token must return 401."""
    client, _ = quiz_client
    assert client.post("/api/quiz/submit", json={"answers": {"q001": "Fibroma"}}).status_code == 401


def test_b7_unauthenticated_attempt_fetch_returns_401(quiz_client):
    """GET /api/quiz/attempts/{id} without a token must return 401."""
    client, _ = quiz_client
    assert client.get("/api/quiz/attempts/1").status_code == 401
