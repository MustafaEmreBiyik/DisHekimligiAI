"""Tests for the shared constants module."""

import os
import importlib


def test_constants_importable():
    from app.constants import TOPIC_LABELS, WEAK_THRESHOLD_PCT, COMPOSITE_WEIGHTS

    assert isinstance(TOPIC_LABELS, dict)
    assert len(TOPIC_LABELS) >= 3
    assert isinstance(WEAK_THRESHOLD_PCT, float)
    assert isinstance(COMPOSITE_WEIGHTS, dict)


def test_composite_weights_sum_to_one():
    from app.constants import COMPOSITE_WEIGHTS

    total = sum(COMPOSITE_WEIGHTS.values())
    assert abs(total - 1.0) < 1e-9


def test_weak_threshold_env_override(monkeypatch):
    monkeypatch.setenv("DENTAI_WEAK_THRESHOLD", "75")
    import app.constants as mod
    importlib.reload(mod)

    assert mod.WEAK_THRESHOLD_PCT == 75.0

    monkeypatch.delenv("DENTAI_WEAK_THRESHOLD", raising=False)
    importlib.reload(mod)
    assert mod.WEAK_THRESHOLD_PCT == 60.0
