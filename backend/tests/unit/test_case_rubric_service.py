"""
Unit tests for case_rubric_service (T-3C)
==========================================
All tests use mocked scoring_rules data — no disk I/O, no DB.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

from app.services.case_rubric_service import (
    CaseNotFoundError,
    DecisionPoint,
    CaseRubric,
    get_all_case_rubrics,
    get_case_rubric,
    list_available_case_ids,
    _build_rubric,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_RULES = [
    {
        "case_id": "case_alpha",
        "schema_version": "2.0",
        "rules": [
            {
                "target_action": "check_vitals",
                "score": 20,
                "rule_outcome": "Vital signs checked.",
                "competency_tags": ["anamnesis", "clinical_safety"],
                "is_critical_safety_rule": True,
                "safety_category": "high",
            },
            {
                "target_action": "gather_history",
                "score": 10,
                "rule_outcome": "History gathered.",
                "competency_tags": ["anamnesis"],
                "is_critical_safety_rule": False,
                "safety_category": None,
            },
            {
                "target_action": "wrong_medication",
                "score": -15,
                "rule_outcome": "Incorrect medication prescribed.",
                "competency_tags": ["pharmacology"],
                "is_critical_safety_rule": False,
                "safety_category": "high",
            },
        ],
    },
    {
        "case_id": "case_beta",
        "schema_version": "2.0",
        "rules": [
            {
                "target_action": "inspect_lesion",
                "score": 15,
                "rule_outcome": "Lesion inspected.",
                "competency_tags": ["diagnosis"],
                "is_critical_safety_rule": False,
                "safety_category": None,
            },
        ],
    },
]


def patch_rules(monkeypatch):
    """Patch _cached_rules to return MOCK_RULES without disk access."""
    import app.services.case_rubric_service as svc
    monkeypatch.setattr(svc, "_cached_rules", lambda: MOCK_RULES)


# ---------------------------------------------------------------------------
# TestBuildRubric — unit test _build_rubric directly
# ---------------------------------------------------------------------------

class TestBuildRubric:
    def test_case_id_preserved(self):
        rubric = _build_rubric(MOCK_RULES[0])
        assert rubric.case_id == "case_alpha"

    def test_total_max_score_sums_positive_only(self):
        rubric = _build_rubric(MOCK_RULES[0])
        # 20 + 10 = 30 (penalty -15 excluded)
        assert rubric.total_max_score == 30

    def test_critical_count(self):
        rubric = _build_rubric(MOCK_RULES[0])
        assert rubric.critical_count == 1

    def test_positive_count(self):
        rubric = _build_rubric(MOCK_RULES[0])
        assert rubric.positive_count == 2

    def test_penalty_count(self):
        rubric = _build_rubric(MOCK_RULES[0])
        assert rubric.penalty_count == 1

    def test_decision_points_count(self):
        rubric = _build_rubric(MOCK_RULES[0])
        assert len(rubric.decision_points) == 3

    def test_computed_at_is_iso_string(self):
        rubric = _build_rubric(MOCK_RULES[0])
        assert rubric.computed_at.endswith("Z")
        # Should be parseable
        from datetime import datetime
        datetime.fromisoformat(rubric.computed_at.rstrip("Z"))

    def test_single_rule_case(self):
        rubric = _build_rubric(MOCK_RULES[1])
        assert rubric.total_max_score == 15
        assert rubric.critical_count == 0
        assert rubric.penalty_count == 0
        assert len(rubric.decision_points) == 1


# ---------------------------------------------------------------------------
# TestRubricLevel — rubric_level classification
# ---------------------------------------------------------------------------

class TestRubricLevel:
    def _dp_by_action(self, rubric: CaseRubric, action: str) -> DecisionPoint:
        return next(dp for dp in rubric.decision_points if dp.target_action == action)

    def test_critical_rule_gets_critical_level(self):
        rubric = _build_rubric(MOCK_RULES[0])
        dp = self._dp_by_action(rubric, "check_vitals")
        assert dp.rubric_level == "critical"

    def test_positive_non_critical_gets_standard(self):
        rubric = _build_rubric(MOCK_RULES[0])
        dp = self._dp_by_action(rubric, "gather_history")
        assert dp.rubric_level == "standard"

    def test_negative_score_gets_penalty(self):
        rubric = _build_rubric(MOCK_RULES[0])
        dp = self._dp_by_action(rubric, "wrong_medication")
        assert dp.rubric_level == "penalty"


# ---------------------------------------------------------------------------
# TestSortOrder — critical first, then standard desc score, then penalties
# ---------------------------------------------------------------------------

class TestSortOrder:
    def test_critical_is_first(self):
        rubric = _build_rubric(MOCK_RULES[0])
        assert rubric.decision_points[0].rubric_level == "critical"

    def test_penalty_is_last(self):
        rubric = _build_rubric(MOCK_RULES[0])
        assert rubric.decision_points[-1].rubric_level == "penalty"

    def test_standard_between_critical_and_penalty(self):
        rubric = _build_rubric(MOCK_RULES[0])
        assert rubric.decision_points[1].rubric_level == "standard"


# ---------------------------------------------------------------------------
# TestDecisionPointFields — field values round-trip correctly
# ---------------------------------------------------------------------------

class TestDecisionPointFields:
    def test_target_action(self):
        rubric = _build_rubric(MOCK_RULES[0])
        actions = {dp.target_action for dp in rubric.decision_points}
        assert actions == {"check_vitals", "gather_history", "wrong_medication"}

    def test_score_values(self):
        rubric = _build_rubric(MOCK_RULES[0])
        scores = {dp.target_action: dp.score for dp in rubric.decision_points}
        assert scores["check_vitals"] == 20
        assert scores["gather_history"] == 10
        assert scores["wrong_medication"] == -15

    def test_is_critical_flag(self):
        rubric = _build_rubric(MOCK_RULES[0])
        dp_critical = next(dp for dp in rubric.decision_points if dp.is_critical)
        assert dp_critical.target_action == "check_vitals"

    def test_competency_tags_preserved(self):
        rubric = _build_rubric(MOCK_RULES[0])
        dp = next(dp for dp in rubric.decision_points if dp.target_action == "check_vitals")
        assert "anamnesis" in dp.competency_tags
        assert "clinical_safety" in dp.competency_tags

    def test_safety_category_none_for_standard(self):
        rubric = _build_rubric(MOCK_RULES[0])
        dp = next(dp for dp in rubric.decision_points if dp.target_action == "gather_history")
        assert dp.safety_category is None

    def test_safety_category_preserved(self):
        rubric = _build_rubric(MOCK_RULES[0])
        dp = next(dp for dp in rubric.decision_points if dp.target_action == "check_vitals")
        assert dp.safety_category == "high"

    def test_rule_outcome_preserved(self):
        rubric = _build_rubric(MOCK_RULES[0])
        dp = next(dp for dp in rubric.decision_points if dp.target_action == "check_vitals")
        assert dp.rule_outcome == "Vital signs checked."


# ---------------------------------------------------------------------------
# TestGetCaseRubric — public API with monkeypatched _cached_rules
# ---------------------------------------------------------------------------

class TestGetCaseRubric:
    def test_returns_correct_case(self, monkeypatch):
        patch_rules(monkeypatch)
        rubric = get_case_rubric("case_alpha")
        assert rubric.case_id == "case_alpha"

    def test_second_case(self, monkeypatch):
        patch_rules(monkeypatch)
        rubric = get_case_rubric("case_beta")
        assert rubric.case_id == "case_beta"
        assert rubric.total_max_score == 15

    def test_unknown_case_raises(self, monkeypatch):
        patch_rules(monkeypatch)
        with pytest.raises(CaseNotFoundError):
            get_case_rubric("nonexistent_case")

    def test_blank_case_id_raises(self, monkeypatch):
        patch_rules(monkeypatch)
        with pytest.raises(CaseNotFoundError):
            get_case_rubric("   ")


# ---------------------------------------------------------------------------
# TestGetAllCaseRubrics
# ---------------------------------------------------------------------------

class TestGetAllCaseRubrics:
    def test_returns_all_cases(self, monkeypatch):
        patch_rules(monkeypatch)
        rubrics = get_all_case_rubrics()
        assert len(rubrics) == 2

    def test_sorted_by_case_id(self, monkeypatch):
        patch_rules(monkeypatch)
        rubrics = get_all_case_rubrics()
        ids = [r.case_id for r in rubrics]
        assert ids == sorted(ids)

    def test_all_are_case_rubric_instances(self, monkeypatch):
        patch_rules(monkeypatch)
        rubrics = get_all_case_rubrics()
        for r in rubrics:
            assert isinstance(r, CaseRubric)


# ---------------------------------------------------------------------------
# TestListAvailableCaseIds
# ---------------------------------------------------------------------------

class TestListAvailableCaseIds:
    def test_returns_sorted_ids(self, monkeypatch):
        patch_rules(monkeypatch)
        ids = list_available_case_ids()
        assert ids == ["case_alpha", "case_beta"]

    def test_returns_list_of_strings(self, monkeypatch):
        patch_rules(monkeypatch)
        ids = list_available_case_ids()
        assert all(isinstance(i, str) for i in ids)


# ---------------------------------------------------------------------------
# TestEmptyRules — edge case: case with zero rules
# ---------------------------------------------------------------------------

class TestEmptyRules:
    EMPTY_CASE = [{"case_id": "empty_case", "schema_version": "2.0", "rules": []}]

    def test_empty_rules_case(self, monkeypatch):
        import app.services.case_rubric_service as svc
        monkeypatch.setattr(svc, "_cached_rules", lambda: self.EMPTY_CASE)
        rubric = get_case_rubric("empty_case")
        assert rubric.total_max_score == 0
        assert rubric.critical_count == 0
        assert rubric.decision_points == []
