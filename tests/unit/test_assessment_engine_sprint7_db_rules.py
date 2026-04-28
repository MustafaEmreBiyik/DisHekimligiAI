"""Sprint 7 rule-runtime tests for DB-backed AssessmentEngine behavior."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import assessment_engine as assessment_engine_module
from app.assessment_engine import AssessmentEngine
from db.database import Base, CaseDefinition


def _create_case(db_factory, *, case_id: str, rules_json: list[dict]) -> None:
    db = db_factory()
    try:
        db.add(
            CaseDefinition(
                case_id=case_id,
                schema_version="2.0",
                title="Runtime Rules Case",
                category="oral_pathology",
                difficulty="beginner",
                estimated_duration_minutes=20,
                is_active=True,
                learning_objectives=["obj"],
                prerequisite_competencies=["pre"],
                competency_tags=["clinical_reasoning"],
                initial_state="consultation",
                states_json={"consultation": {}},
                patient_info_json={"age": 30, "chief_complaint": "Agri"},
                rules_json=rules_json,
                source_payload={"case_id": case_id, "title": "Runtime Rules Case"},
                is_archived=False,
                archived_at=None,
            )
        )
        db.commit()
    finally:
        db.close()


def test_assessment_engine_prefers_live_db_rules_over_legacy_json(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    _create_case(
        testing_session_local,
        case_id="runtime_case_01",
        rules_json=[
            {
                "target_action": "perform_oral_exam",
                "score": 12,
                "rule_outcome": "DB rule applied",
                "state_updates": {"revealed_findings": ["db_finding"]},
                "competency_tags": ["clinical_reasoning"],
                "is_critical_safety_rule": False,
                "safety_category": None,
            }
        ],
    )

    monkeypatch.setattr(assessment_engine_module, "SessionLocal", testing_session_local)
    monkeypatch.delenv("DENTAI_ALLOW_RULE_JSON_FALLBACK", raising=False)

    assessment_engine = AssessmentEngine(rules_path="legacy_rules.json")
    monkeypatch.setattr(
        assessment_engine,
        "_load_json_rules",
        lambda: {
            "runtime_case_01": [
                {
                    "target_action": "perform_oral_exam",
                    "score": 999,
                    "rule_outcome": "Legacy file rule should not win",
                    "competency_tags": ["legacy"],
                    "is_critical_safety_rule": False,
                    "safety_category": None,
                }
            ]
        },
    )

    initial_result = assessment_engine.evaluate_action(
        "runtime_case_01",
        {"interpreted_action": "perform_oral_exam"},
    )
    assert initial_result["score"] == 12
    assert initial_result["rule_outcome"] == "DB rule applied"

    db = testing_session_local()
    try:
        case = db.query(CaseDefinition).filter(CaseDefinition.case_id == "runtime_case_01").first()
        assert case is not None
        case.rules_json = [
            {
                "target_action": "perform_oral_exam",
                "score": 25,
                "rule_outcome": "Updated DB rule applied",
                "competency_tags": ["clinical_reasoning", "clinical_safety"],
                "is_critical_safety_rule": True,
                "safety_category": "missed_critical_step",
            }
        ]
        db.commit()
    finally:
        db.close()

    updated_result = assessment_engine.evaluate_action(
        "runtime_case_01",
        {"interpreted_action": "perform_oral_exam"},
    )
    assert updated_result["score"] == 25
    assert updated_result["rule_outcome"] == "Updated DB rule applied"
    assert updated_result["is_critical_safety_rule"] is True

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
