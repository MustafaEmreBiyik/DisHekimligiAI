"""
Shared Constants
================
Single source of truth for topic labels, scoring thresholds, and composite weights.

All numeric tunables are env-overridable so production can adjust without code changes:
  DENTAI_WEAK_THRESHOLD       — % below which a topic is "weak"         (default 60)
  DENTAI_WEIGHT_MCQ           — composite MCQ weight (0–1)              (default 0.35)
  DENTAI_WEIGHT_OE            — composite open-ended weight (0–1)       (default 0.40)
  DENTAI_WEIGHT_CASE          — composite case weight (0–1)             (default 0.25)
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

TOPIC_LABELS: dict[str, str] = {
    "oral_pathology": "Oral Patoloji",
    "infectious_diseases": "Enfeksiyöz Hastalıklar",
    "traumatic": "Travmatik Lezyonlar",
    "untagged": "Etiketlenmemiş",
}

WEAK_THRESHOLD_PCT: float = float(os.getenv("DENTAI_WEAK_THRESHOLD", "60"))


def _load_composite_weights() -> dict[str, float]:
    """Load and validate composite scoring weights from environment.

    Falls back to hardcoded defaults if env vars are absent or invalid.
    Logs a warning when custom weights don't sum to 1.0 so operators are
    aware of potential scoring anomalies without crashing at boot.
    """
    defaults = {"mcq": 0.35, "oe": 0.40, "case": 0.25}
    weights: dict[str, float] = {}

    for key, default in defaults.items():
        env_var = f"DENTAI_WEIGHT_{key.upper()}"
        raw = os.getenv(env_var, "").strip()
        if raw:
            try:
                weights[key] = float(raw)
            except ValueError:
                logger.warning("Invalid value for %s=%r — using default %.2f", env_var, raw, default)
                weights[key] = default
        else:
            weights[key] = default

    total = sum(weights.values())
    if abs(total - 1.0) > 0.001:
        logger.warning(
            "DENTAI composite weights sum to %.4f (expected 1.0). "
            "Set DENTAI_WEIGHT_MCQ / DENTAI_WEIGHT_OE / DENTAI_WEIGHT_CASE to correct this.",
            total,
        )

    return weights


COMPOSITE_WEIGHTS: dict[str, float] = _load_composite_weights()
