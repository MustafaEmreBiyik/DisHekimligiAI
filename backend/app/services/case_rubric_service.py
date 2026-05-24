"""
Case Rubric Service (T-3C — Sprint 3)
======================================
Derives a structured rubric for each clinical case from the existing
scoring_rules.json data.  No schema change is needed: the rubric is
computed dynamically from data that is already present on disk.

Rubric structure per case
--------------------------
CaseRubric
  case_id          : str
  total_max_score  : int          sum of all positive rule scores
  critical_count   : int          number of is_critical_safety_rule=True rules
  positive_count   : int          number of rules with score > 0
  penalty_count    : int          number of rules with score < 0
  computed_at      : str          ISO-8601 timestamp (UTC)
  decision_points  : list[DecisionPoint]

DecisionPoint
  target_action         : str
  score                 : int    (negative = penalty)
  rule_outcome          : str    explanation text from the JSON
  is_critical           : bool
  safety_category       : str | None
  competency_tags       : list[str]
  rubric_level          : str    "critical" | "standard" | "penalty"
"""
from __future__ import annotations

import datetime
import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_PROJECT_ROOT = _BACKEND_ROOT.parent
_SCORING_RULES_PATH = _PROJECT_ROOT / "data" / "scoring_rules.json"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DecisionPoint:
    target_action: str
    score: int
    rule_outcome: str
    is_critical: bool
    safety_category: Optional[str]
    competency_tags: List[str]
    rubric_level: str          # "critical" | "standard" | "penalty"


@dataclass
class CaseRubric:
    case_id: str
    total_max_score: int
    critical_count: int
    positive_count: int
    penalty_count: int
    computed_at: str
    decision_points: List[DecisionPoint] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class CaseNotFoundError(ValueError):
    """Raised when the requested case_id does not exist in scoring_rules.json."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_scoring_rules() -> List[dict]:
    """Read and parse scoring_rules.json.  Raises RuntimeError on IO failure."""
    try:
        with open(_SCORING_RULES_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise RuntimeError(f"scoring_rules.json not found at {_SCORING_RULES_PATH}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"scoring_rules.json is malformed: {exc}") from exc


@lru_cache(maxsize=1)
def _cached_rules() -> List[dict]:
    """Cache the parsed JSON so repeated API calls don't re-read disk."""
    return _load_scoring_rules()


def _rubric_level(score: int, is_critical: bool) -> str:
    if is_critical:
        return "critical"
    if score < 0:
        return "penalty"
    return "standard"


def _build_rubric(case_data: dict) -> CaseRubric:
    case_id: str = case_data["case_id"]
    rules: List[dict] = case_data.get("rules", [])

    decision_points: List[DecisionPoint] = []
    for rule in rules:
        score = int(rule.get("score", 0))
        is_critical = bool(rule.get("is_critical_safety_rule", False))
        dp = DecisionPoint(
            target_action=rule.get("target_action", ""),
            score=score,
            rule_outcome=rule.get("rule_outcome", ""),
            is_critical=is_critical,
            safety_category=rule.get("safety_category"),
            competency_tags=list(rule.get("competency_tags", [])),
            rubric_level=_rubric_level(score, is_critical),
        )
        decision_points.append(dp)

    # Sort: critical first, then standard (desc score), then penalties last
    def sort_key(dp: DecisionPoint) -> tuple:
        order = {"critical": 0, "standard": 1, "penalty": 2}
        return (order[dp.rubric_level], -dp.score)

    decision_points.sort(key=sort_key)

    total_max_score = sum(dp.score for dp in decision_points if dp.score > 0)
    critical_count = sum(1 for dp in decision_points if dp.is_critical)
    positive_count = sum(1 for dp in decision_points if dp.score > 0)
    penalty_count = sum(1 for dp in decision_points if dp.score < 0)

    return CaseRubric(
        case_id=case_id,
        total_max_score=total_max_score,
        critical_count=critical_count,
        positive_count=positive_count,
        penalty_count=penalty_count,
        computed_at=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
        decision_points=decision_points,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_all_case_rubrics() -> List[CaseRubric]:
    """Return rubrics for every case in scoring_rules.json."""
    rules = _cached_rules()
    rubrics = [_build_rubric(c) for c in rules]
    # Sort alphabetically by case_id for stable responses
    rubrics.sort(key=lambda r: r.case_id)
    return rubrics


def get_case_rubric(case_id: str) -> CaseRubric:
    """Return the rubric for a single case.  Raises CaseNotFoundError if missing."""
    case_id = case_id.strip()
    if not case_id:
        raise CaseNotFoundError("case_id must not be blank")
    rules = _cached_rules()
    for case_data in rules:
        if case_data.get("case_id") == case_id:
            return _build_rubric(case_data)
    raise CaseNotFoundError(
        f"No scoring rules found for case_id={case_id!r}. "
        f"Available: {[c['case_id'] for c in rules]}"
    )


def list_available_case_ids() -> List[str]:
    """Return sorted list of all case_ids that have scoring rules."""
    rules = _cached_rules()
    return sorted(c["case_id"] for c in rules)
