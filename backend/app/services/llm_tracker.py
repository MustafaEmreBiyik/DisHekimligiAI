"""LLM Interaction Tracker (S9-C)

Records every Gemini and HuggingFace API call to llm_interaction_logs.
Supports budget monitoring, rate-limit detection, and EU AI Act audit requirements.

Usage:
    from app.services.llm_tracker import record_llm_interaction

    with record_llm_interaction(
        provider="gemini",
        model_id="models/gemini-2.5-flash-lite",
        call_type="interpretation",
        session_id=42,
    ) as ctx:
        response = model.generate_content(prompt)
        ctx.set_token_usage(
            prompt_tokens=response.usage_metadata.prompt_token_count,
            completion_tokens=response.usage_metadata.candidates_token_count,
        )
"""
from __future__ import annotations

import contextlib
import datetime
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Gemini pricing (USD per 1 000 tokens) — Gemini 2.5 Flash Lite public pricing.
# Update when pricing changes; cost tracking is best-effort.
_GEMINI_COST_PER_1K_INPUT = 0.000075
_GEMINI_COST_PER_1K_OUTPUT = 0.0003


def _estimate_gemini_cost(prompt_tokens: Optional[int], completion_tokens: Optional[int]) -> Optional[float]:
    if prompt_tokens is None and completion_tokens is None:
        return None
    p = prompt_tokens or 0
    c = completion_tokens or 0
    return round(
        (p / 1000) * _GEMINI_COST_PER_1K_INPUT + (c / 1000) * _GEMINI_COST_PER_1K_OUTPUT,
        8,
    )


class _InteractionContext:
    """Mutable context object passed into the `with` block."""

    def __init__(self) -> None:
        self.prompt_tokens: Optional[int] = None
        self.completion_tokens: Optional[int] = None

    def set_token_usage(self, *, prompt_tokens: Optional[int], completion_tokens: Optional[int]) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


@contextlib.contextmanager
def record_llm_interaction(
    *,
    provider: str,
    model_id: str,
    call_type: str,
    session_id: Optional[int] = None,
):
    """Context manager that measures latency and persists an LLMInteractionLog row.

    The block sets success=True unless an exception escapes; in that case
    success=False and the error message is captured. Exceptions are re-raised.
    """
    ctx = _InteractionContext()
    start = time.monotonic()
    success = True
    error_msg: Optional[str] = None

    try:
        yield ctx
    except Exception as exc:
        success = False
        error_msg = str(exc)[:500]
        raise
    finally:
        latency_ms = int((time.monotonic() - start) * 1000)
        total_tokens: Optional[int] = None
        if ctx.prompt_tokens is not None or ctx.completion_tokens is not None:
            total_tokens = (ctx.prompt_tokens or 0) + (ctx.completion_tokens or 0)

        estimated_cost: Optional[float] = None
        if provider == "gemini":
            estimated_cost = _estimate_gemini_cost(ctx.prompt_tokens, ctx.completion_tokens)

        _persist(
            session_id=session_id,
            provider=provider,
            model_id=model_id,
            call_type=call_type,
            prompt_tokens=ctx.prompt_tokens,
            completion_tokens=ctx.completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            estimated_cost_usd=estimated_cost,
            success=success,
            error_message=error_msg,
        )


def _persist(
    *,
    session_id: Optional[int],
    provider: str,
    model_id: str,
    call_type: str,
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    total_tokens: Optional[int],
    latency_ms: int,
    estimated_cost_usd: Optional[float],
    success: bool,
    error_message: Optional[str],
) -> None:
    """Write one LLMInteractionLog row; swallows all errors to never break the calling flow."""
    try:
        from db.database import LLMInteractionLog, SessionLocal

        db = SessionLocal()
        try:
            db.add(
                LLMInteractionLog(
                    session_id=session_id,
                    provider=provider,
                    model_id=model_id,
                    call_type=call_type,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    estimated_cost_usd=estimated_cost_usd,
                    success=success,
                    error_message=error_message,
                    created_at=datetime.datetime.utcnow(),
                )
            )
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.warning("LLM tracker failed to persist log: %s", exc)
