"""Sprint 2 normalization and import regression tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base, CaseDefinition
from scripts.import_cases import CaseImportValidationError, import_cases, load_cases


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = PROJECT_ROOT / "data" / "case_scenarios.json"
RULES_PATH = PROJECT_ROOT / "data" / "scoring_rules.json"


def test_case_scenarios_normalized_to_canonical_schema_v2():
    cases = load_cases(CASES_PATH)
    assert cases, "case_scenarios.json should contain at least one case"

    required_fields = {
        "case_id",
        "schema_version",
        "title",
        "category",
        "difficulty",
        "estimated_duration_minutes",
        "is_active",
        "learning_objectives",
        "prerequisite_competencies",
        "competency_tags",
        "initial_state",
        "states",
        "patient_info",
    }

    for case in cases:
        assert case["schema_version"] == "2.0"
        assert required_fields.issubset(case.keys())
        assert case["difficulty"] in {"beginner", "intermediate", "advanced"}
        assert isinstance(case["estimated_duration_minutes"], int)
        assert case["estimated_duration_minutes"] > 0
        assert isinstance(case["learning_objectives"], list) and case["learning_objectives"]
        assert isinstance(case["prerequisite_competencies"], list) and case["prerequisite_competencies"]
        assert isinstance(case["competency_tags"], list) and case["competency_tags"]
        assert isinstance(case["states"], dict)
        assert isinstance(case["patient_info"], dict)


def test_scoring_rules_include_competency_and_critical_safety_flags():
    with open(RULES_PATH, "r", encoding="utf-8") as file:
        rule_sets = json.load(file)

    assert rule_sets, "scoring_rules.json should contain at least one rule set"

    critical_count = 0

    for rule_set in rule_sets:
        assert rule_set["schema_version"] == "2.0"
        for rule in rule_set.get("rules", []):
            assert isinstance(rule.get("competency_tags"), list)
            assert rule["competency_tags"], "competency_tags must be non-empty"
            assert isinstance(rule.get("is_critical_safety_rule"), bool)

            if rule.get("is_critical_safety_rule"):
                critical_count += 1
                assert rule.get("safety_category") in {
                    "premature_treatment",
                    "wrong_medication",
                    "missed_critical_step",
                    "contraindication_violation",
                }
            else:
                assert rule.get("safety_category") is None

            if rule.get("score", 0) < 0:
                assert rule["is_critical_safety_rule"] is True

    assert critical_count > 0


@pytest.fixture
def case_import_db(tmp_path):
    db_file = tmp_path / "case_import.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    try:
        yield SessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_import_cases_is_idempotent(case_import_db):
    cases = load_cases(CASES_PATH)

    db = case_import_db()
    try:
        dry_run_report = import_cases(db=db, case_payloads=cases, dry_run=True)
        assert dry_run_report.added == len(cases)
        assert dry_run_report.updated == 0
        assert dry_run_report.skipped == 0
        assert db.query(CaseDefinition).count() == 0

        apply_report = import_cases(db=db, case_payloads=cases, dry_run=False)
        assert apply_report.added == len(cases)
        assert apply_report.updated == 0
        assert apply_report.skipped == 0
        assert db.query(CaseDefinition).count() == len(cases)

        second_report = import_cases(db=db, case_payloads=cases, dry_run=False)
        assert second_report.added == 0
        assert second_report.updated == 0
        assert second_report.skipped == len(cases)
        assert db.query(CaseDefinition).count() == len(cases)
    finally:
        db.close()


def test_import_cases_validation_rejects_noncanonical_payload(case_import_db):
    invalid_case = {
        "case_id": "invalid_case",
        "schema_version": "1.0",
        "title": "Invalid",
    }

    db = case_import_db()
    try:
        with pytest.raises(CaseImportValidationError):
            import_cases(db=db, case_payloads=[invalid_case], dry_run=True)
    finally:
        db.close()
