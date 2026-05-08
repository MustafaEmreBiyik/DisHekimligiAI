"""Unit tests for Sprint 3 analytics logic."""

import pandas as pd

from app.analytics_engine import analyze_performance, generate_report_text


SAMPLE_ACTIONS = [
    {"action": "take_anamnesis", "score": 9, "outcome": "Dogru"},
    {"action": "ask_symptom_onset", "score": 8, "outcome": "Dogru"},
    {"action": "ask_about_medications", "score": 9, "outcome": "Dogru"},
    {"action": "perform_oral_exam", "score": 9, "outcome": "Dogru"},
    {"action": "perform_nikolsky_test", "score": 8, "outcome": "Dogru"},
    {"action": "examine_skin", "score": 8, "outcome": "Dogru"},
    {"action": "diagnose_lichen_planus", "score": 4, "outcome": "Yanlis"},
    {"action": "diagnose_periodontitis", "score": 5, "outcome": "Kismen Dogru"},
    {"action": "diagnose_primary_herpes", "score": 3, "outcome": "Yanlis"},
    {"action": "prescribe_topical_steroids", "score": 7, "outcome": "Dogru"},
    {"action": "prescribe_antibiotics", "score": 6, "outcome": "Kismen Dogru"},
    {"action": "request_biopsy", "score": 8, "outcome": "Dogru"},
    {"action": "request_blood_tests", "score": 9, "outcome": "Dogru"},
]


def test_analyze_performance_detects_weakest_category():
    df = pd.DataFrame(SAMPLE_ACTIONS)

    analysis = analyze_performance(df)

    assert analysis["weakest_category"] == "diagnosis"
    assert analysis["weakest_score"] == 4.0
    assert "Tan\u0131 Koyma" in analysis["recommendation"]
    assert "diagnosis" in analysis["category_performance"]


def test_generate_report_text_contains_expected_sections():
    df = pd.DataFrame(SAMPLE_ACTIONS)
    analysis = analyze_performance(df)

    stats = {
        "action_history": SAMPLE_ACTIONS,
        "total_score": sum(item["score"] for item in SAMPLE_ACTIONS),
        "total_actions": len(SAMPLE_ACTIONS),
        "completed_cases": {"olp_001", "perio_001"},
    }

    report = generate_report_text(stats, analysis)

    assert "PERFORMANS KARNESI" in report
    assert "GENEL PERFORMANS" in report
    assert "GELISIM ONERISI" not in report
    assert "GEL\u0130\u015e\u0130M \u00d6NER\u0130S\u0130" in report
