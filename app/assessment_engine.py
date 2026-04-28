from __future__ import annotations

import json
import os
import logging
from typing import Any, Dict, List, Optional

from db.database import CaseDefinition, SessionLocal

logger = logging.getLogger(__name__)


class AssessmentEngine:
    """
    Loads scoring rules from the DB-backed case catalog and evaluates
    interpreted actions against case-specific rules.

    Legacy JSON rules are treated as an opt-in fallback source only when
    DENTAI_ALLOW_RULE_JSON_FALLBACK is enabled.
    """

    def __init__(self, rules_path: Optional[str] = None) -> None:
        self._rules_path = rules_path or os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "data", "scoring_rules.json")
        )
        self._allow_json_fallback = (
            os.getenv("DENTAI_ALLOW_RULE_JSON_FALLBACK", "").strip().lower()
            in {"1", "true", "yes"}
        )
        self._json_rules_by_case: Optional[Dict[str, List[Dict[str, Any]]]] = None

    def _coerce_rules_list(self, payload: Any) -> List[Dict[str, Any]]:
        if not isinstance(payload, list):
            return []
        return [rule for rule in payload if isinstance(rule, dict)]

    def _load_rules_from_db(self, case_id: str) -> Optional[List[Dict[str, Any]]]:
        db = SessionLocal()
        try:
            case = (
                db.query(CaseDefinition)
                .filter(
                    CaseDefinition.case_id == case_id,
                    CaseDefinition.is_archived.is_(False),
                )
                .first()
            )
            if not case:
                return None
            return self._coerce_rules_list(case.rules_json)
        except Exception as exc:
            logger.warning("Failed to load DB rules for case_id '%s': %s", case_id, exc)
            return None
        finally:
            db.close()

    def _load_json_rules(self) -> Dict[str, List[Dict[str, Any]]]:
        if self._json_rules_by_case is not None:
            return self._json_rules_by_case

        try:
            with open(self._rules_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except FileNotFoundError:
            logger.warning("Legacy scoring rules file not found: %s", self._rules_path)
            self._json_rules_by_case = {}
            return self._json_rules_by_case
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse legacy scoring rules JSON: %s", exc)
            self._json_rules_by_case = {}
            return self._json_rules_by_case

        if not isinstance(data, list):
            logger.error("Invalid legacy rules format (expected list): %s", type(data).__name__)
            self._json_rules_by_case = {}
            return self._json_rules_by_case

        rules_by_case: Dict[str, List[Dict[str, Any]]] = {}
        for entry in data:
            if not isinstance(entry, dict):
                continue

            case_id = str(entry.get("case_id") or "").strip()
            if not case_id:
                continue

            rules_list = entry.get("rules")
            if rules_list is None:
                rules_list = entry.get("actions", [])

            rules_by_case[case_id] = self._coerce_rules_list(rules_list)

        self._json_rules_by_case = rules_by_case
        return self._json_rules_by_case

    def _load_rules_for_case(self, case_id: str) -> List[Dict[str, Any]]:
        db_rules = self._load_rules_from_db(case_id)
        if db_rules is not None:
            return db_rules

        if not self._allow_json_fallback:
            return []

        return self._load_json_rules().get(case_id, [])

    def _find_rule(self, case_id: str, interpreted_action: str) -> Optional[Dict[str, Any]]:
        """
        Find a rule matching the given case_id and interpreted_action.
        Looks inside 'rules' (preferred) or 'actions' (fallback) for entries where
        rule['target_action'] == interpreted_action.
        """
        if not case_id or not interpreted_action:
            return None

        for rule in self._load_rules_for_case(case_id):
            if rule.get("target_action") == interpreted_action:
                return rule

        return None

    def evaluate_action(self, case_id: str, interpretation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate an interpreted action for a specific case.

        Returns:
        - If matched:
            {
              "score": int|float,
              "score_change": int|float,
              "rule_outcome": str,
              "action_effect": Any
            }
        - If not matched:
            {
              "score": 0,
              "score_change": 0,
              "rule_outcome": "Unscored",
              "action_effect": None
            }
        """
        default_result: Dict[str, Any] = {
            "score": 0,
            "score_change": 0,
            "rule_outcome": "Unscored",
            "action_effect": None,
        }

        if not isinstance(interpretation, dict):
            return default_result

        interpreted_action = interpretation.get("interpreted_action")
        if not isinstance(interpreted_action, str) or not interpreted_action.strip():
            return default_result

        rule = self._find_rule(case_id, interpreted_action.strip())
        if not rule:
            return default_result

        score = rule.get("score", 0)
        outcome = rule.get("rule_outcome", "Unscored")
        effect = rule.get("action_effect")
        state_updates = rule.get("state_updates", {})

        return {
            "score": score,
            "score_change": score,
            "rule_outcome": outcome,
            "action_effect": effect,
            "state_updates": state_updates,
            "is_critical_safety_rule": bool(rule.get("is_critical_safety_rule", False)),
            "safety_category": rule.get("safety_category"),
            "competency_tags": rule.get("competency_tags", []) or [],
        }
