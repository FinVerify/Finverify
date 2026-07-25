"""
Evaluator
=========
Orchestrates the full pipeline:
  LLM call → parse → DVL verify → format response.

Also provides a verify-only path for demo mode.
"""

from typing import Optional

from core.engine import verify
from core.models import Claim
from .parser import format_number_display
from .models import QueryResponse, CorrectionEntry


def build_query_response(
    question: str,
    raw_text: Optional[str],
    raw_number: Optional[float],
    actual: Optional[float] = None,
) -> QueryResponse:
    """
    Verify an already-parsed number and build the backward-compatible response.
    """
    result = verify(Claim(
        question=question,
        raw_text=raw_text,
        raw_value=raw_number,
        actual_value=actual,
    ))

    if raw_number is None:
        return QueryResponse(
            question=question,
            raw_text=raw_text,
            raw_number=None,
            verified_number=None,
            correction_log=[],
            trust_score="LOW",
            trust_color="#f87171",
            display_value="N/A — no number extracted",
        )

    display = format_number_display(result.verified_value, question)

    return QueryResponse(
        question=question,
        raw_text=raw_text,
        raw_number=raw_number,
        verified_number=result.verified_value,
        correction_log=[CorrectionEntry(**e) for e in result.correction_log],
        trust_score=result.trust_score.label,
        trust_color=result.trust_score.color,
        display_value=display,
    )
