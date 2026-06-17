"""
S13-M3 — Visual Silent Validator Tests
Tests VisualClinicalValidator.validate() — mocking Gemini to avoid live API calls.
"""

import json
import types
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures — mock Gemini model
# ---------------------------------------------------------------------------

def _make_validator(response_text: str):
    """Create a VisualClinicalValidator with a mocked Gemini model."""
    import sys
    import types as _types

    # Build a minimal google.generativeai stub using protos.Part (matches production code)
    genai_mock = _types.ModuleType("google.generativeai")

    class _FakeBlob:
        def __init__(self, mime_type=None, data=None):
            self.mime_type = mime_type
            self.data = data

    class _FakePart:
        def __init__(self, text=None, inline_data=None):
            self.text = text
            self.inline_data = inline_data

    class _FakeProtos:
        Part = _FakePart
        Blob = _FakeBlob

    class _FakeModel:
        def __init__(self, *a, **kw): pass

        def generate_content(self, parts, request_options=None):
            return _types.SimpleNamespace(text=response_text)

    genai_mock.configure = lambda **kw: None
    genai_mock.GenerativeModel = _FakeModel
    genai_mock.protos = _FakeProtos

    with patch.dict(sys.modules, {"google": _types.ModuleType("google"), "google.generativeai": genai_mock}):
        from importlib import import_module, reload
        import app.services.visual_validator as vv_module
        reload(vv_module)
        validator = vv_module.VisualClinicalValidator(api_key="test-key")
        # Replace model with fake
        validator._model = _FakeModel()
    return validator


@pytest.fixture
def dummy_image_bytes():
    return bytes([0xFF, 0xD8, 0xFF, 0xE0] + [0x00] * 20)


# ---------------------------------------------------------------------------
# Tests — parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:
    def _parse(self, raw_text: str):
        from app.services.visual_validator import VisualClinicalValidator
        v = VisualClinicalValidator.__new__(VisualClinicalValidator)
        return v._parse_response(raw_text)

    def test_true_match(self):
        payload = json.dumps({
            "safety_flags": [],
            "missing_critical_steps": [],
            "clinical_accuracy": "high",
            "faculty_notes": "Wickham striae clearly visible.",
            "image_finding_match": True,
        })
        result = self._parse(payload)
        assert result["image_finding_match"] is True
        assert result["clinical_accuracy"] == "high"

    def test_false_match(self):
        payload = json.dumps({
            "safety_flags": ["visual_mismatch"],
            "missing_critical_steps": [],
            "clinical_accuracy": "low",
            "faculty_notes": "Claimed kavite not visible.",
            "image_finding_match": False,
        })
        result = self._parse(payload)
        assert result["image_finding_match"] is False
        assert "visual_mismatch" in result["safety_flags"]

    def test_null_match(self):
        payload = json.dumps({
            "safety_flags": [],
            "missing_critical_steps": [],
            "clinical_accuracy": None,
            "faculty_notes": "",
            "image_finding_match": None,
        })
        result = self._parse(payload)
        assert result["image_finding_match"] is None

    def test_string_true_coerced(self):
        payload = json.dumps({"image_finding_match": "true", "safety_flags": [],
                               "missing_critical_steps": [], "clinical_accuracy": None, "faculty_notes": ""})
        result = self._parse(payload)
        assert result["image_finding_match"] is True

    def test_string_false_coerced(self):
        payload = json.dumps({"image_finding_match": "false", "safety_flags": [],
                               "missing_critical_steps": [], "clinical_accuracy": None, "faculty_notes": ""})
        result = self._parse(payload)
        assert result["image_finding_match"] is False

    def test_malformed_json_returns_null(self):
        result = self._parse("not json at all")
        assert result["image_finding_match"] is None
        assert "_fail_reason" in result

    def test_faculty_notes_truncated_at_200(self):
        payload = json.dumps({
            "safety_flags": [],
            "missing_critical_steps": [],
            "clinical_accuracy": "medium",
            "faculty_notes": "X" * 300,
            "image_finding_match": True,
        })
        result = self._parse(payload)
        assert len(result["faculty_notes"]) <= 200

    def test_safety_flags_max_10(self):
        payload = json.dumps({
            "safety_flags": [f"flag_{i}" for i in range(15)],
            "missing_critical_steps": [],
            "clinical_accuracy": None,
            "faculty_notes": "",
            "image_finding_match": None,
        })
        result = self._parse(payload)
        assert len(result["safety_flags"]) <= 10


# ---------------------------------------------------------------------------
# Tests — null_result static method
# ---------------------------------------------------------------------------

class TestNullResult:
    def test_null_result_structure(self):
        from app.services.visual_validator import VisualClinicalValidator
        result = VisualClinicalValidator._null_result("test_reason")
        assert result["image_finding_match"] is None
        assert result["safety_flags"] == []
        assert result["_fail_reason"] == "test_reason"


# ---------------------------------------------------------------------------
# Tests — validate() fail-closed behaviour
# ---------------------------------------------------------------------------

class TestValidateFailClosed:
    def test_no_image_bytes_returns_null(self):
        """When image_bytes is None/empty, returns fail-closed null result."""
        import sys, types as _types
        genai_mock = _types.ModuleType("google.generativeai")
        genai_mock.configure = lambda **kw: None

        class _FakeModel:
            def __init__(self, *a, **kw): pass
            def generate_content(self, parts, request_options=None):
                raise AssertionError("Should not be called when no image")

        genai_mock.GenerativeModel = _FakeModel

        class _FakeBlob:
            def __init__(self, mime_type=None, data=None): pass

        class _FakePart:
            def __init__(self, text=None, inline_data=None): pass

        class _FakeProtos:
            Part = _FakePart
            Blob = _FakeBlob

        genai_mock.protos = _FakeProtos

        with patch.dict(sys.modules, {"google": _types.ModuleType("google"), "google.generativeai": genai_mock}):
            from importlib import reload
            import app.services.visual_validator as vvm
            reload(vvm)
            v = vvm.VisualClinicalValidator.__new__(vvm.VisualClinicalValidator)
            v._api_key = "test"
            v._model = _FakeModel()
            result = v.validate(
                student_text="Wickham striae görüyorum",
                visual_findings_observed=[],
                image_bytes=b"",  # empty bytes — should fail-closed
                image_mime="image/jpeg",
                rules={},
                context_summary="Test context",
            )
        assert result["image_finding_match"] is None

    def test_gemini_exception_returns_null(self, dummy_image_bytes):
        """If Gemini raises an exception, result is fail-closed (null match)."""
        import sys, types as _types
        genai_mock = _types.ModuleType("google.generativeai")
        genai_mock.configure = lambda **kw: None

        class _BrokenModel:
            def __init__(self, *a, **kw): pass
            def generate_content(self, parts, request_options=None):
                raise RuntimeError("Gemini quota exceeded")

        genai_mock.GenerativeModel = _BrokenModel

        class _FakeBlob:
            def __init__(self, mime_type=None, data=None): pass

        class _FakePart:
            def __init__(self, text=None, inline_data=None): pass

        class _FakeProtos:
            Part = _FakePart
            Blob = _FakeBlob

        genai_mock.protos = _FakeProtos

        with patch.dict(sys.modules, {"google": _types.ModuleType("google"), "google.generativeai": genai_mock}):
            from importlib import reload
            import app.services.visual_validator as vvm
            reload(vvm)
            v = vvm.VisualClinicalValidator.__new__(vvm.VisualClinicalValidator)
            v._api_key = "test"
            v._model = _BrokenModel()
            result = v.validate(
                student_text="Kavite görüyorum",
                visual_findings_observed=[],
                image_bytes=dummy_image_bytes,
                image_mime="image/jpeg",
                rules={},
                context_summary="OLP vakası",
            )
        assert result["image_finding_match"] is None


# ---------------------------------------------------------------------------
# Tests — agent._silent_evaluation with image_finding_match
# ---------------------------------------------------------------------------

class TestSilentEvaluationImageMatch:
    """Integration smoke: _silent_evaluation propagates image_finding_match=False to safety_flags."""

    def test_visual_mismatch_adds_flag(self):
        from app.services.visual_validator import VisualClinicalValidator
        from unittest.mock import patch, MagicMock
        import app.agent as agent_module

        # Build a minimal agent without real Gemini/MedGemma
        ag = agent_module.DentalEducationAgent.__new__(agent_module.DentalEducationAgent)
        ag.med_gemma = None  # skip MedGemma

        mock_medgemma_result = {
            "safety_flags": [],
            "missing_critical_steps": [],
            "clinical_accuracy": "medium",
            "faculty_notes": "OK",
            "audit": {"validator_used": "medgemma", "response_time_ms": 0, "error_message": None, "attempts": 0},
        }
        mock_vv_result = {
            "safety_flags": [],
            "missing_critical_steps": [],
            "clinical_accuracy": None,
            "faculty_notes": "",
            "image_finding_match": False,  # mismatch
        }
        with patch.object(
            agent_module.MedGemmaService, "build_fail_closed_result", return_value=mock_medgemma_result
        ):
            with patch(
                "app.services.visual_validator.VisualClinicalValidator"
            ) as MockVV:
                instance = MockVV.return_value
                instance.validate.return_value = mock_vv_result
                result = ag._silent_evaluation(
                    student_input="Kavite görüyorum",
                    interpreted_action="perform_oral_exam",
                    state={"case_id": "olp_001", "category": "OLP"},
                    assessment={"is_critical_safety_rule": False},
                    safety_scan=None,
                    image_bytes=b"\xff\xd8\xff",
                    image_mime="image/jpeg",
                    visual_findings_observed=["Wickham striae görülüyor"],
                )

        assert result["image_finding_match"] is False
        assert "visual_finding_mismatch" in result["safety_flags"]

    def test_no_image_image_finding_match_is_none(self):
        """When no image is attached, image_finding_match must be None."""
        import app.agent as agent_module
        from unittest.mock import patch, MagicMock

        ag = agent_module.DentalEducationAgent.__new__(agent_module.DentalEducationAgent)
        ag.med_gemma = None

        mock_result = {
            "safety_flags": [],
            "missing_critical_steps": [],
            "clinical_accuracy": "high",
            "faculty_notes": "",
            "audit": {"validator_used": "medgemma", "response_time_ms": 0, "error_message": None, "attempts": 0},
        }

        with patch.object(agent_module.MedGemmaService, "build_fail_closed_result", return_value=mock_result):
            result = ag._silent_evaluation(
                student_input="Tıbbi geçmiş alıyorum",
                interpreted_action="gather_medical_history",
                state={"case_id": "olp_001", "category": "OLP"},
                assessment={"is_critical_safety_rule": False},
                safety_scan=None,
                image_bytes=None,
                image_mime="image/jpeg",
                visual_findings_observed=None,
            )

        assert result["image_finding_match"] is None
        assert "visual_finding_mismatch" not in result["safety_flags"]
