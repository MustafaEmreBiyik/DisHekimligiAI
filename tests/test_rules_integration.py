"""Integration tests for clinical rules + MedGemma service (mocked backend)."""

import json
from types import SimpleNamespace

import pytest

from app.rules.clinical_rules import get_rules_for_category


pytestmark = pytest.mark.integration


@pytest.fixture
def infectious_rules():
    rules = get_rules_for_category("INFECTIOUS")
    assert rules
    return rules


def _patch_medgemma_response(monkeypatch, service, payload):
    content = json.dumps(payload)
    fake_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )
    monkeypatch.setattr(service.client, "chat_completion", lambda **_kwargs: fake_response)


def test_infectious_rules_are_available(infectious_rules):
    assert isinstance(infectious_rules, dict)
    assert "critical_safety_rules" in infectious_rules
    assert infectious_rules["critical_safety_rules"]


def test_medgemma_flags_penicillin_allergy_violation(infectious_rules, monkeypatch):
    from app.services.med_gemma_service import MedGemmaService

    service = MedGemmaService()
    _patch_medgemma_response(
        monkeypatch,
        service,
        {
            "safety_flags": ["contraindication_violation"],
            "missing_critical_steps": ["verify_penicillin_allergy"],
            "clinical_accuracy": "low",
            "faculty_notes": "Penicillin allergy contraindication detected.",
        },
    )

    result = service.validate_clinical_action(
        student_text="I will prescribe Amoxicillin 500mg TID for 7 days.",
        rules=infectious_rules,
        context_summary="Patient has documented Penicillin allergy.",
    )

    assert result["is_clinically_accurate"] is False
    assert result["safety_violation"] is True


def test_medgemma_accepts_allergy_safe_alternative(infectious_rules, monkeypatch):
    from app.services.med_gemma_service import MedGemmaService

    service = MedGemmaService()
    _patch_medgemma_response(
        monkeypatch,
        service,
        {
            "safety_flags": [],
            "missing_critical_steps": [],
            "clinical_accuracy": "high",
            "faculty_notes": "Clindamycin is appropriate for Penicillin allergy.",
        },
    )

    result = service.validate_clinical_action(
        student_text="I will prescribe Clindamycin 300mg QID for 7 days.",
        rules=infectious_rules,
        context_summary="Patient has documented Penicillin allergy.",
    )

    assert result["is_clinically_accurate"] is True
    assert result["safety_violation"] is False
