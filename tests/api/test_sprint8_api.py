import pytest
from fastapi.testclient import TestClient

from app.api.deps import UserRole
from db.database import Question, QuestionType, QuizAnswer, GradingStatus

from tests.security.test_quiz_hardening_b7 import quiz_client

def test_s8b_student_open_ended_submission(quiz_client):
    """Student submits an OE question, which results in PENDING state."""
    client, db_factory = quiz_client
    
    # Create an OE question in DB
    db = db_factory()
    try:
        from tests.security.test_quiz_hardening_b7 import _create_user, _auth, _token
        _create_user(db_factory, "stu_oe", UserRole.STUDENT)
        _create_user(db_factory, "inst_oe", UserRole.INSTRUCTOR)
        
        q_oe = Question(
            question_id="oe_001",
            question_type=QuestionType.OPEN_ENDED,
            question_text="Explain clinical features of X.",
            topic_id="Oral Patoloji",
            bloom_level="analyze",
            difficulty="hard",
            safety_category="none",
            rubric_guide="Mention Y and Z.",
            max_score=10
        )
        db.add(q_oe)
        db.commit()
    finally:
        db.close()

    # Submit OE response
    token = _token("stu_oe", UserRole.STUDENT)
    resp = client.post(
        "/api/quiz/submit",
        json={"answers": {"oe_001": "My answer is Y and Z."}},
        headers=_auth(token)
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_status"] == "PENDING"
    assert data["score"] is None
    assert data["percentage"] is None
    
    qr = data["results"][0]
    assert qr["grading_status"] == "PENDING"
    assert qr["is_correct"] is None
    assert qr["instructor_score"] is None
    
    attempt_id = data["attempt_id"]
    
    # Fetch attempt as student - should still be PENDING and hide instructor feedback
    resp2 = client.get(f"/api/quiz/attempts/{attempt_id}", headers=_auth(token))
    assert resp2.json()["overall_status"] == "PENDING"
    
    # Check instructor queue
    inst_token = _token("inst_oe", UserRole.INSTRUCTOR)
    q_resp = client.get("/api/quiz/instructor/grading_queue", headers=_auth(inst_token))
    assert q_resp.status_code == 200
    queue = q_resp.json()
    assert len(queue) == 1
    item = queue[0]
    assert item["question_id"] == "oe_001"
    assert item["rubric_guide"] == "Mention Y and Z."
    answer_id = item["answer_id"]
    
    # Instructor grades it but doesn't publish
    grade_resp = client.post(
        f"/api/quiz/instructor/grade/{answer_id}",
        json={"instructor_score": 8, "instructor_feedback": "Good job.", "publish": False},
        headers=_auth(inst_token)
    )
    assert grade_resp.status_code == 200
    
    # Student checks again, should still be PENDING and no instructor feedback
    resp3 = client.get(f"/api/quiz/attempts/{attempt_id}", headers=_auth(token))
    assert resp3.json()["overall_status"] == "PENDING"
    assert resp3.json()["results"][0]["instructor_score"] is None
    
    # Instructor publishes
    grade_resp2 = client.post(
        f"/api/quiz/instructor/grade/{answer_id}",
        json={"instructor_score": 8, "instructor_feedback": "Good job.", "publish": True},
        headers=_auth(inst_token)
    )
    assert grade_resp2.status_code == 200
    
    # Student checks again, should be PUBLISHED
    resp4 = client.get(f"/api/quiz/attempts/{attempt_id}", headers=_auth(token))
    assert resp4.json()["overall_status"] == "PUBLISHED"
    assert resp4.json()["score"] == 8
    assert resp4.json()["results"][0]["instructor_score"] == 8
    assert resp4.json()["results"][0]["instructor_feedback"] == "Good job."
