import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import (
    Base,
    Question,
    QuestionType,
    QuestionCaseMapping,
    MappingType,
    ReviewStatus,
    QuizAttempt,
    QuizAnswer,
    GradingStatus,
)

@pytest.fixture(scope="module")
def schema_test_db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_sprint8_question_case_mapping_relationships(schema_test_db):
    session = schema_test_db
    
    # Create an Open-Ended question
    q = Question(
        question_id="test_oe_001",
        question_type=QuestionType.OPEN_ENDED,
        question_text="Explain oral lichen planus.",
        topic_id="oral_lichen_planus",
        bloom_level="analyze",
        difficulty="hard",
        safety_category="none",
        rubric_guide="Check for wickham striae mention.",
        max_score=20
    )
    session.add(q)
    session.commit()
    
    # Create multiple mappings for this question
    mapping1 = QuestionCaseMapping(
        question=q,
        case_id="olp_001",
        mapping_type=MappingType.ASSESSMENT_LINK,
        review_status=ReviewStatus.APPROVED
    )
    mapping2 = QuestionCaseMapping(
        question=q,
        case_id="olp_002_review",
        mapping_type=MappingType.THEORY_SUPPORT,
        review_status=ReviewStatus.BLOCKED_REVIEW_NEEDED
    )
    session.add_all([mapping1, mapping2])
    session.commit()
    
    # Verify relationships
    assert len(q.case_mappings) == 2
    assert q.case_mappings[0].case_id == "olp_001"
    assert q.case_mappings[1].review_status == ReviewStatus.BLOCKED_REVIEW_NEEDED

def test_sprint8_quiz_attempt_and_grading_status_default(schema_test_db):
    session = schema_test_db
    
    q = Question(
        question_id="test_mcq_001",
        question_type=QuestionType.MCQ,
        question_text="Which is correct?",
        topic_id="dummy_topic",
        bloom_level="remember",
        difficulty="easy",
        safety_category="none",
        options_json=["A", "B"],
        correct_option="A",
        max_score=10
    )
    session.add(q)
    
    attempt = QuizAttempt(
        user_id="student_001",
        total_score=0,
        max_score=10
    )
    session.add(attempt)
    session.commit()
    
    # Create an answer
    answer = QuizAnswer(
        attempt=attempt,
        question=q,
        student_response_text="A",
    )
    session.add(answer)
    session.commit()
    
    # Verify default grading status is PENDING
    assert answer.grading_status == GradingStatus.PENDING
    
    # Verify relationships
    assert len(attempt.answers) == 1
    assert attempt.answers[0].question.question_type == QuestionType.MCQ
