import json
import sys
import tempfile
import types
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base


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
    "safety_flags": [],
    "missing_critical_steps": [],
    "clinical_accuracy": "high",
    "faculty_notes": "Mocked MedGemma response",
}


def pytest_configure(config):
    """Keep pytest temp files inside the writable workspace on this desktop setup."""
    if config.option.basetemp:
        return

    repo_root = Path(__file__).resolve().parents[1]
    base_temp_root = repo_root / ".pytest_runtime"
    base_temp_root.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = tempfile.mkdtemp(prefix="run_", dir=base_temp_root)


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

        def generate_content(self, _prompt, request_options=None):
            # Always read from the currently active stub in sys.modules so that
            # mock_gemini_response overrides work even when app.agent's genai
            # binding was captured in a previous test's fixture invocation.
            active = sys.modules.get("google.generativeai", gemini_module)
            return types.SimpleNamespace(text=getattr(active, "_response_text", gemini_module._response_text))

    class _DummyBlob:
        def __init__(self, mime_type=None, data=None):
            self.mime_type = mime_type
            self.data = data

    class _DummyPart:
        def __init__(self, text=None, inline_data=None):
            self.text = text
            self.inline_data = inline_data

    class _DummyProtos:
        Part = _DummyPart
        Blob = _DummyBlob

    gemini_module.configure = _configure
    gemini_module.GenerativeModel = _DummyGenerativeModel
    gemini_module.protos = _DummyProtos

    google_module = sys.modules.get("google")
    if google_module is None:
        google_module = types.ModuleType("google")
        monkeypatch.setitem(sys.modules, "google", google_module)

    setattr(google_module, "generativeai", gemini_module)
    monkeypatch.setitem(sys.modules, "google.generativeai", gemini_module)

    # Also patch the `genai` name inside app.agent and app.services.visual_validator
    # directly, in case those modules were imported at collection time (before
    # fixtures ran) with the real google-generativeai package.
    try:
        import app.agent as _agent_module
        monkeypatch.setattr(_agent_module, "genai", gemini_module)
    except Exception:
        pass
    try:
        import app.services.visual_validator as _vv_module
        monkeypatch.setattr(_vv_module, "genai", gemini_module)
    except Exception:
        pass

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
def db():
    """Shared in-memory SQLite session for unit tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


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
