"""
Shared Constants
================
Single source of truth for topic labels, scoring thresholds, and composite weights.
"""

from __future__ import annotations

import os

TOPIC_LABELS: dict[str, str] = {
    "oral_pathology": "Oral Patoloji",
    "infectious_diseases": "Enfeksiyöz Hastalıklar",
    "traumatic": "Travmatik Lezyonlar",
    "untagged": "Etiketlenmemiş",
}

WEAK_THRESHOLD_PCT: float = float(os.getenv("DENTAI_WEAK_THRESHOLD", "60"))

COMPOSITE_WEIGHTS: dict[str, float] = {
    "mcq": 0.35,
    "oe": 0.40,
    "case": 0.25,
}
