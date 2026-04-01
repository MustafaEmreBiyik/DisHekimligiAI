import json
import sys
import types

import pytest


_DEFAULT_GEMINI_PAYLOAD = {
    "intent_type": "ACTION",
    "interpreted_action": "perform_pathergy_test",
    "clinical_intent": "diagnosis_gathering",
    "priority": "medium",
    "safety_concerns": [],
    "explanatory_feedback": "Mocked Gemini response",
    "structured_args": {},
}

_DEFAULT_MEDGEMMA_PAYLOAD = {
    "is_clinically_accurate": True,
    "safety_violation": False,
    "missing_critical_info": [],
    "feedback": "Mocked MedGemma response",
}


@pytest.fixture(autouse=True)
def set_auth_env_defaults(monkeypatch):
    """Keep JWT configuration deterministic for offline test runs."""
    monkeypatch.setenv("DENTAI_SECRET_KEY", "test-dentai-secret-key")
    monkeypatch.setenv("DENTAI_ACCESS_TOKEN_EXPIRE_MINUTES", "1440")


@pytest.fixture(autouse=True)
def block_live_network_calls(monkeypatch, request):
    """Keep default pytest profile fully offline."""
    if request.node.get_closest_marker("integration") or request.node.get_closest_marker("e2e"):
        return

    def _blocked_request(*_args, **_kwargs):
        raise RuntimeError(
            "Live HTTP calls are disabled in default pytest runs. "
            "Use -m integration or -m e2e for opt-in network tests."
        )

    try:
        import requests

        monkeypatch.setattr(requests.sessions.Session, "request", _blocked_request, raising=True)
    except Exception:
        # requests might not be installed in minimal environments.
        pass


@pytest.fixture(autouse=True)
def mock_external_ai_sdks(monkeypatch):
    """Provide deterministic Gemini + MedGemma SDK stubs for all tests."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("HUGGINGFACE_API_KEY", "test-hf-key")

    gemini_module = types.ModuleType("google.generativeai")
    gemini_module._response_text = json.dumps(_DEFAULT_GEMINI_PAYLOAD)

    def _configure(**_kwargs):
        return None

    class _DummyGenerativeModel:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def generate_content(self, _prompt):
            return types.SimpleNamespace(text=gemini_module._response_text)

    gemini_module.configure = _configure
    gemini_module.GenerativeModel = _DummyGenerativeModel

    google_module = sys.modules.get("google")
    if google_module is None:
        google_module = types.ModuleType("google")
        monkeypatch.setitem(sys.modules, "google", google_module)

    setattr(google_module, "generativeai", gemini_module)
    monkeypatch.setitem(sys.modules, "google.generativeai", gemini_module)

    hf_module = types.ModuleType("huggingface_hub")
    hf_module._response_text = json.dumps(_DEFAULT_MEDGEMMA_PAYLOAD)

    class _DummyMessage:
        def __init__(self, content):
            self.content = content

    class _DummyChoice:
        def __init__(self, content):
            self.message = _DummyMessage(content)

    class _DummyChatResponse:
        def __init__(self, content):
            self.choices = [_DummyChoice(content)]

    class _DummyInferenceClient:
        def __init__(self, token=None):
            self.token = token

        def chat_completion(self, **_kwargs):
            return _DummyChatResponse(hf_module._response_text)

    hf_module.InferenceClient = _DummyInferenceClient
    monkeypatch.setitem(sys.modules, "huggingface_hub", hf_module)

    return {"gemini": gemini_module, "huggingface": hf_module}


@pytest.fixture
def mock_gemini_response(mock_external_ai_sdks):
    """Override Gemini mock response text for a test."""
    gemini_module = mock_external_ai_sdks["gemini"]

    def _set(payload):
        gemini_module._response_text = payload if isinstance(payload, str) else json.dumps(payload)

    return _set


@pytest.fixture
def mock_medgemma_response(mock_external_ai_sdks):
    """Override MedGemma mock response JSON for a test."""
    hf_module = mock_external_ai_sdks["huggingface"]

    def _set(payload):
        hf_module._response_text = payload if isinstance(payload, str) else json.dumps(payload)

    return _set
