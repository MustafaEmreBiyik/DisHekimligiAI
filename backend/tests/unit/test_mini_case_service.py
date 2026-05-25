"""Tests for mini-case service (T-5B)."""

import pytest

from db.database import MiniCase
from app.services.mini_case_service import list_mini_cases, get_mini_case


def _seed_mini_case(db, mini_case_id="mc_test_001", title="Test Case", difficulty="medium", is_active=True):
    mc = MiniCase(
        mini_case_id=mini_case_id,
        title=title,
        linked_topic_ids=["oral_pathology"],
        clinical_vignette="Patient presents with...",
        key_findings=["Finding 1", "Finding 2"],
        question_ids=["Q-001", "Q-002"],
        learning_objectives=["Objective 1"],
        difficulty=difficulty,
        is_active=is_active,
    )
    db.add(mc)
    db.commit()
    return mc


class TestListMiniCases:
    def test_returns_active_cases(self, db):
        _seed_mini_case(db, mini_case_id="mc_1", title="Alpha")
        _seed_mini_case(db, mini_case_id="mc_2", title="Beta")
        _seed_mini_case(db, mini_case_id="mc_3", title="Gamma", is_active=False)

        result = list_mini_cases(db)
        assert len(result) == 2
        assert result[0].title == "Alpha"
        assert result[1].title == "Beta"

    def test_empty_when_no_cases(self, db):
        result = list_mini_cases(db)
        assert result == []

    def test_question_count(self, db):
        _seed_mini_case(db)
        result = list_mini_cases(db)
        assert result[0].question_count == 2


class TestGetMiniCase:
    def test_returns_detail(self, db):
        _seed_mini_case(db, mini_case_id="mc_detail")
        result = get_mini_case("mc_detail", db)
        assert result is not None
        assert result.mini_case_id == "mc_detail"
        assert len(result.key_findings) == 2
        assert len(result.question_ids) == 2

    def test_not_found_returns_none(self, db):
        result = get_mini_case("nonexistent", db)
        assert result is None

    def test_detail_includes_vignette(self, db):
        _seed_mini_case(db, mini_case_id="mc_vig")
        result = get_mini_case("mc_vig", db)
        assert "Patient presents" in result.clinical_vignette
