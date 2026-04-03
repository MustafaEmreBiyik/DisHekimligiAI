import json
import re
from typing import Any, Dict, List, Tuple

MAX_STUDENT_INPUT_CHARS = 2000
MAX_MODEL_FEEDBACK_CHARS = 500

_INJECTION_PATTERNS: List[Tuple[str, int, re.Pattern[str]]] = [
    (
        "instruction_override",
        3,
        re.compile(
            r"\bignore\b.{0,50}\b(previous|all|above|earlier)\b.{0,50}\b(instruction|instructions|prompt|rules?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "role_override",
        2,
        re.compile(r"\b(you are now|act as|pretend to be|from now on)\b", re.IGNORECASE),
    ),
    (
        "prompt_exfiltration",
        3,
        re.compile(
            r"\b(system prompt|developer message|hidden prompt|reveal .*instructions|show .*prompt)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "jailbreak_pattern",
        2,
        re.compile(r"\b(jailbreak|dan mode|do anything now|bypass safety|disable safety)\b", re.IGNORECASE),
    ),
    (
        "system_role_injection",
        2,
        re.compile(r"(<\s*system\s*>|role\s*:\s*system|begin system prompt)", re.IGNORECASE),
    ),
]

_RESPONSE_BLOCKED_TOKENS = [
    "system prompt",
    "developer message",
    "hidden prompt",
    "api key",
    "token",
    "password",
]


def sanitize_student_text(text: Any, *, max_chars: int = MAX_STUDENT_INPUT_CHARS) -> Dict[str, Any]:
    raw = "" if text is None else str(text)
    without_controls = "".join(ch if ch in {"\n", "\t"} or ord(ch) >= 32 else " " for ch in raw)
    normalized_newlines = without_controls.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized_newlines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()

    truncated = len(normalized) > max_chars
    safe_text = normalized[:max_chars].strip() if truncated else normalized
    if not safe_text:
        safe_text = "(empty_input)"

    return {
        "text": safe_text,
        "meta": {
            "raw_length": len(raw),
            "sanitized_length": len(safe_text),
            "truncated": truncated,
            "control_chars_removed": raw != without_controls,
            "whitespace_normalized": raw.strip() != safe_text,
        },
    }


def detect_prompt_injection(text: Any) -> Dict[str, Any]:
    scan_text = "" if text is None else str(text)
    normalized = " ".join(scan_text.split())

    signals: List[Dict[str, Any]] = []
    score = 0
    for category, weight, pattern in _INJECTION_PATTERNS:
        match = pattern.search(normalized)
        if not match:
            continue

        score += weight
        snippet = normalized[max(0, match.start() - 30): match.end() + 30]
        signals.append(
            {
                "category": category,
                "weight": weight,
                "snippet": snippet[:180],
            }
        )

    risk_level = "low"
    if score >= 4:
        risk_level = "high"
    elif score >= 2:
        risk_level = "medium"

    return {
        "detected": len(signals) > 0,
        "score": score,
        "risk_level": risk_level,
        "signals": signals,
    }


def build_untrusted_student_payload(*, student_text: str, context: Dict[str, Any]) -> str:
    payload = {
        "untrusted_student_input": student_text,
        "context": context,
    }
    return json.dumps(payload, ensure_ascii=False)


def sanitize_model_feedback(text: Any) -> str:
    cleaned = " ".join(str(text or "").split()).strip()
    if not cleaned:
        return "Lutfen semptomlarini biraz daha detaylandirir misin?"

    lowered = cleaned.lower()
    if any(token in lowered for token in _RESPONSE_BLOCKED_TOKENS):
        return "Bu bilgiyi paylasamam. Klinikte bir sonraki guvenli adimi birlikte planlayalim."

    if len(cleaned) > MAX_MODEL_FEEDBACK_CHARS:
        cleaned = cleaned[:MAX_MODEL_FEEDBACK_CHARS].rstrip() + "..."

    return cleaned
