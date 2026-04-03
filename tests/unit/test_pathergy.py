"""Unit tests for pathergy action interpretation."""


def test_pathergy_action_is_interpreted_correctly(mock_gemini_response):
    from app.agent import DentalEducationAgent

    mock_gemini_response(
        {
            "intent_type": "ACTION",
            "interpreted_action": "perform_pathergy_test",
            "clinical_intent": "diagnosis_gathering",
            "priority": "medium",
            "safety_concerns": [],
            "explanatory_feedback": "Paterji testi istemen klinik olarak anlamli.",
            "structured_args": {},
        }
    )

    agent = DentalEducationAgent(api_key="test-gemini-key")
    state = {
        "case_id": "behcet_01",
        "patient": {"age": 32, "chief_complaint": "Oral ulcers"},
        "revealed_findings": [],
    }

    interpretation = agent.interpret_action("Paterji testi yapiyorum", state)

    assert interpretation["intent_type"] == "ACTION"
    assert interpretation["interpreted_action"] == "perform_pathergy_test"
    assert interpretation["clinical_intent"] == "diagnosis_gathering"
