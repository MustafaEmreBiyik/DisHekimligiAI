"""
B-7 security regression tests: quiz answer-key hardening.

Verifies that:
- GET /api/quiz/questions never exposes correct_option or explanation.
- POST /api/quiz/submit grades answers server-side and returns answer keys
  only in the submission response.
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
        # Only the safe fields must be present
        assert set(q.keys()) == {"id", "topic", "question", "options"}


def test_b7_instructor_questions_also_no_answer_key(quiz_client):
    """GET /api/quiz/questions must not leak answer keys even to instructors."""
    client, db_factory = quiz_client
    _create_user(db_factory, "inst_leak", UserRole.INSTRUCTOR)

    resp = client.get("/api/quiz/questions", headers=_auth(_token("inst_leak", UserRole.INSTRUCTOR)))
    assert resp.status_code == 200
    for q in resp.json():
        assert "correct_option" not in q
        assert "explanation" not in q


# ── Server-side grading ───────────────────────────────────────────────────────

def test_b7_submit_wrong_answer_graded_server_side(quiz_client):
    """POST /api/quiz/submit grades a wrong answer and reveals answer key in response."""
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

    qr = result["results"][0]
    assert qr["id"] == "q001"
    assert qr["correct_option"] == "Leukoplakia"
    assert "premalignant" in qr["explanation"]
    assert qr["selected_option"] == "Fibroma"
    assert qr["is_correct"] is False


def test_b7_submit_correct_answer_scores_100(quiz_client):
    """POST /api/quiz/submit with correct answer returns is_correct=True and 100%."""
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
    for qr in result["results"]:
        assert qr["is_correct"] is True


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


# ── Auth enforcement ──────────────────────────────────────────────────────────

def test_b7_unauthenticated_questions_returns_401(quiz_client):
    """GET /api/quiz/questions without a token must return 401."""
    client, _ = quiz_client
    assert client.get("/api/quiz/questions").status_code == 401


def test_b7_unauthenticated_submit_returns_401(quiz_client):
    """POST /api/quiz/submit without a token must return 401."""
    client, _ = quiz_client
    assert client.post("/api/quiz/submit", json={"answers": {"q001": "Fibroma"}}).status_code == 401
