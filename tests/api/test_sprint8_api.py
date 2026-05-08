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


def test_s8b_instructor_can_create_open_ended_question_and_students_receive_safe_view(quiz_client):
    client, db_factory = quiz_client

    from tests.security.test_quiz_hardening_b7 import _create_user, _auth, _token

    _create_user(db_factory, "inst_author", UserRole.INSTRUCTOR)
    _create_user(db_factory, "stu_author", UserRole.STUDENT)

    payload = {
        "question_text": "A 52-year-old patient presents with a non-healing white-red lesion on the lateral tongue. Explain how you would prioritize the differential diagnosis and the next diagnostic step.",
        "topic_id": "Oral Patoloji",
        "competency_areas": ["differential diagnosis", "lesion triage"],
        "bloom_level": "analyze",
        "difficulty": "hard",
        "safety_category": "high",
        "rubric_guide": "Award full credit when the answer identifies malignant potential, prioritizes erythroleukoplakia or SCC, and recommends urgent biopsy or specialist referral.",
        "model_answer_outline": "Recognize red-flag features, discuss malignant disorders in the differential, justify urgency, and recommend biopsy/referral.",
        "instructor_explanation": "This item checks whether the learner can distinguish a dangerous lesion from benign white lesions.",
        "max_score": 12,
        "is_active": True,
    }

    create_response = client.post(
        "/api/quiz/instructor/questions",
        json=payload,
        headers=_auth(_token("inst_author", UserRole.INSTRUCTOR)),
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["question_type"] == "OPEN_ENDED"
    assert created["question_id"].startswith("oe-")
    assert created["rubric_guide"] == payload["rubric_guide"]
    assert created["model_answer_outline"] == payload["model_answer_outline"]

    list_response = client.get(
        "/api/quiz/instructor/questions",
        headers=_auth(_token("inst_author", UserRole.INSTRUCTOR)),
    )
    assert list_response.status_code == 200
    listed = list_response.json()
    assert any(item["question_id"] == created["question_id"] for item in listed)

    student_response = client.get(
        "/api/quiz/questions",
        headers=_auth(_token("stu_author", UserRole.STUDENT)),
    )
    assert student_response.status_code == 200
    student_questions = student_response.json()
    matching = next(item for item in student_questions if item["id"] == created["question_id"])
    assert matching["question_type"] == "OPEN_ENDED"
    assert matching["options"] == []
    assert "rubric_guide" not in matching
    assert "model_answer_outline" not in matching
    assert "instructor_explanation" not in matching


def test_s8b_instructor_can_create_mcq_and_student_receives_safe_payload(quiz_client):
    client, db_factory = quiz_client

    from tests.security.test_quiz_hardening_b7 import _create_user, _auth, _token

    _create_user(db_factory, "inst_mcq", UserRole.INSTRUCTOR)
    _create_user(db_factory, "stu_mcq", UserRole.STUDENT)

    payload = {
        "question_type": "MCQ",
        "question_text": "A mixed red-white lesion on the lateral tongue is found during routine examination. Which next step is most appropriate?",
        "topic_id": "Oral Patoloji",
        "competency_areas": ["lesion triage", "clinical decision making"],
        "bloom_level": "apply",
        "difficulty": "medium",
        "safety_category": "high",
        "options": [
            "Reassure the patient and review in 12 months",
            "Prescribe antifungal therapy without further workup",
            "Arrange urgent biopsy or specialist referral",
            "Polish the area and reassess only if it enlarges",
        ],
        "correct_option": "Arrange urgent biopsy or specialist referral",
        "instructor_explanation": "Persistent red-white lateral tongue lesions carry malignant potential and need prompt tissue diagnosis.",
        "max_score": 1,
        "is_active": True,
    }

    create_response = client.post(
        "/api/quiz/instructor/questions",
        json=payload,
        headers=_auth(_token("inst_mcq", UserRole.INSTRUCTOR)),
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["question_type"] == "MCQ"
    assert created["question_id"].startswith("mcq-")
    assert created["correct_option"] == payload["correct_option"]
    assert created["options"] == payload["options"]

    list_response = client.get(
        "/api/quiz/instructor/questions?question_type=MCQ",
        headers=_auth(_token("inst_mcq", UserRole.INSTRUCTOR)),
    )
    assert list_response.status_code == 200
    listed = list_response.json()
    assert any(item["question_id"] == created["question_id"] for item in listed)

    student_response = client.get(
        "/api/quiz/questions",
        headers=_auth(_token("stu_mcq", UserRole.STUDENT)),
    )
    assert student_response.status_code == 200
    student_questions = student_response.json()
    matching = next(item for item in student_questions if item["id"] == created["question_id"])
    assert matching["question_type"] == "MCQ"
    assert matching["options"] == payload["options"]
    assert "correct_option" not in matching
    assert "instructor_explanation" not in matching
