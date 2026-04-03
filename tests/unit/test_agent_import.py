"""Smoke tests for agent/module imports."""


def test_import_dental_education_agent():
    from app.agent import DentalEducationAgent

    assert DentalEducationAgent.__name__ == "DentalEducationAgent"


def test_import_core_agent_dependencies():
    from app.assessment_engine import AssessmentEngine
    from app.scenario_manager import ScenarioManager

    assert AssessmentEngine is not None
    assert ScenarioManager is not None


def test_agent_initializes_with_mocked_external_sdks():
    from app.agent import DentalEducationAgent

    agent = DentalEducationAgent(api_key="test-gemini-key")
    assert hasattr(agent, "process_student_input")
