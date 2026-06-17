"""
Visual Clinical Validator (S13-M3)
===================================
Multimodal silent validator using Gemini 2.5 Flash.
Evaluates whether the student's described finding matches what is observable
in the attached clinical image.

Runs ONLY when image_bytes is provided. Fail-closed: any exception returns
image_finding_match=None (absence of evidence, not evidence of absence).
"""

import json
import logging
import os
import re
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
except ImportError as exc:
    raise ImportError(
        "google-generativeai is not installed. Install with:\n"
        "pip install google-generativeai"
    ) from exc

_VISUAL_VALIDATOR_PROMPT = """
You are a clinical dental education expert evaluating a student's visual finding description.

Given:
1. A clinical oral photograph.
2. The student's described action/finding (student_text).
3. Findings already identified by the AI interpreter (visual_findings_observed).

Your task:
- Determine whether the student's described visual finding is consistent with what is actually visible in the image.
- Output STRICT JSON ONLY. No markdown, no code blocks, no prose.

Output schema:
{
  "safety_flags": ["string"],
  "missing_critical_steps": ["string"],
  "clinical_accuracy": "high" | "medium" | "low" | null,
  "faculty_notes": "string",
  "image_finding_match": true | false | null
}

Rules for image_finding_match:
- true: the student's described visual finding is visible and consistent with the image.
- false: the student claims to see something clearly NOT present in the image.
- null: the student's text does not make a specific visual claim, or you cannot determine.

Keep faculty_notes under 200 characters. Respond ONLY in the JSON format above.
"""

_TIMEOUT_SECONDS = 15
_MODEL = "models/gemini-2.5-flash"


class VisualClinicalValidator:
    """
    Multimodal silent validator using Gemini 2.5 Flash.
    Stateless — create one per request or cache per API key.
    """

    MODEL = _MODEL
    TIMEOUT_SECONDS = _TIMEOUT_SECONDS

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY not set — VisualClinicalValidator cannot initialise.")
        genai.configure(api_key=self._api_key)
        self._model = genai.GenerativeModel(
            model_name=self.MODEL,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.9,
                "max_output_tokens": 256,
                "response_mime_type": "application/json",
            },
        )

    def validate(
        self,
        student_text: str,
        visual_findings_observed: list[str],
        image_bytes: bytes,
        image_mime: str,
        rules: dict,
        context_summary: str,
    ) -> dict[str, Any]:
        """
        Validate whether the student's described visual finding matches the image.

        Returns a dict matching the MedGemmaService output schema plus
        an `image_finding_match` field (true/false/None).

        Fail-closed: any exception returns image_finding_match=None.
        """
        if not image_bytes:
            return self._null_result("no_image")

        try:
            user_prompt = (
                f"Context: {context_summary}\n"
                f"Student text: {student_text[:500]}\n"
                f"AI-observed findings: {json.dumps(visual_findings_observed, ensure_ascii=False)}\n\n"
                "Evaluate image_finding_match as described in the system prompt."
            )

            parts = [
                genai.protos.Part(text=user_prompt),
                genai.protos.Part(inline_data=genai.protos.Blob(mime_type=image_mime, data=image_bytes)),
            ]

            t0 = time.monotonic()
            response = self._model.generate_content(
                [_VISUAL_VALIDATOR_PROMPT] + parts,
                request_options={"timeout": self.TIMEOUT_SECONDS},
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)

            raw_text = getattr(response, "text", "") or ""
            result = self._parse_response(raw_text)
            result["_elapsed_ms"] = elapsed_ms
            return result

        except Exception as exc:
            logger.warning("VisualClinicalValidator.validate failed (fail-closed): %s", exc)
            return self._null_result(str(exc))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_response(self, raw_text: str) -> dict[str, Any]:
        text = raw_text.strip()

        # Try direct parse
        try:
            data = json.loads(text)
        except Exception:
            # Try to extract first JSON block
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(0))
                except Exception:
                    return self._null_result("json_parse_error")
            else:
                return self._null_result("no_json_in_response")

        if not isinstance(data, dict):
            return self._null_result("unexpected_schema")

        safety_flags = data.get("safety_flags", [])
        if not isinstance(safety_flags, list):
            safety_flags = []
        safety_flags = [str(f).strip() for f in safety_flags if isinstance(f, str) and str(f).strip()][:10]

        missing = data.get("missing_critical_steps", [])
        if not isinstance(missing, list):
            missing = []
        missing = [str(s).strip() for s in missing if isinstance(s, str) and str(s).strip()][:10]

        raw_accuracy = data.get("clinical_accuracy")
        clinical_accuracy = None
        if isinstance(raw_accuracy, str) and raw_accuracy.lower() in {"high", "medium", "low"}:
            clinical_accuracy = raw_accuracy.lower()

        faculty_notes = str(data.get("faculty_notes") or "").strip()[:200]

        raw_match = data.get("image_finding_match")
        if isinstance(raw_match, bool):
            image_finding_match = raw_match
        elif isinstance(raw_match, str):
            lower = raw_match.lower()
            image_finding_match = True if lower == "true" else (False if lower == "false" else None)
        else:
            image_finding_match = None

        return {
            "safety_flags": safety_flags,
            "missing_critical_steps": missing,
            "clinical_accuracy": clinical_accuracy,
            "faculty_notes": faculty_notes,
            "image_finding_match": image_finding_match,
        }

    @staticmethod
    def _null_result(reason: str) -> dict[str, Any]:
        return {
            "safety_flags": [],
            "missing_critical_steps": [],
            "clinical_accuracy": None,
            "faculty_notes": "",
            "image_finding_match": None,
            "_fail_reason": reason,
        }
