"""Opt-in end-to-end flow test against a running DentAI API."""

import os
import time
import uuid

import pytest
import requests


pytestmark = pytest.mark.e2e

BASE_URL = os.getenv("DENTAI_E2E_BASE_URL", "http://localhost:8001")
CASE_ID = os.getenv("DENTAI_E2E_CASE_ID", "olp_001")
REQUEST_TIMEOUT = 10


def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _register_or_login(student_id: str, password: str, name: str) -> str:
    register_payload = {
        "student_id": student_id,
        "name": name,
        "password": password,
    }
    register_response = requests.post(
        _url("/api/auth/register"),
        json=register_payload,
        timeout=REQUEST_TIMEOUT,
    )

    if register_response.status_code in (200, 201):
        return register_response.json()["access_token"]

    if register_response.status_code == 400:
        login_response = requests.post(
            _url("/api/auth/login"),
            json={"student_id": student_id, "password": password},
            timeout=REQUEST_TIMEOUT,
        )
        assert login_response.status_code == 200, login_response.text
        return login_response.json()["access_token"]

    pytest.fail(f"Registration failed: {register_response.status_code} {register_response.text}")


def test_student_journey_e2e():
    try:
        health = requests.get(_url("/health"), timeout=5)
    except requests.RequestException:
        pytest.skip(f"DentAI API is not reachable at {BASE_URL}")

    if health.status_code != 200:
        pytest.skip(f"DentAI API is not reachable at {BASE_URL}")

    student_id = f"e2e_{uuid.uuid4().hex[:8]}"
    password = "testpass123"
    token = _register_or_login(student_id=student_id, password=password, name="E2E Test Student")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    first_chat = requests.post(
        _url("/api/chat/send"),
        json={"message": "Hastanin sikayeti nedir?", "case_id": CASE_ID},
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    if first_chat.status_code == 503:
        pytest.skip("Chat service unavailable (GEMINI_API_KEY may be missing).")
    assert first_chat.status_code == 200, first_chat.text

    first_payload = first_chat.json()
    session_id = first_payload.get("session_id")
    assert session_id is not None

    time.sleep(0.3)

    second_chat = requests.post(
        _url("/api/chat/send"),
        json={"message": "Oral mukoza muayenesi yapiyorum.", "case_id": CASE_ID},
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    assert second_chat.status_code == 200, second_chat.text
    second_payload = second_chat.json()
    assert second_payload.get("session_id") == session_id

    feedback = requests.post(
        _url("/api/feedback/submit"),
        json={
            "session_id": session_id,
            "case_id": CASE_ID,
            "rating": 5,
            "comment": "E2E pytest flow validation",
        },
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    assert feedback.status_code in (200, 201), feedback.text

    for endpoint in (
        "/api/analytics/export/actions",
        "/api/analytics/export/feedback",
        "/api/analytics/export/sessions",
    ):
        export_response = requests.get(_url(endpoint), headers=headers, timeout=REQUEST_TIMEOUT)
        assert export_response.status_code == 403, export_response.text

    student_stats = requests.get(
        _url("/api/analytics/student-stats"),
        headers=headers,
        timeout=REQUEST_TIMEOUT,
    )
    assert student_stats.status_code == 200, student_stats.text
