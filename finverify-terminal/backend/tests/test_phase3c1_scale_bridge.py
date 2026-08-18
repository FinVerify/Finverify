"""Phase 3C.1 regression tests: API numeric scale bridge.

Covers the fix in core/compiler.py::_apply_context_scale_bridge (via
app/parser.py::resolve_context_scale) for the bug where raw_value=109.42
alongside context_text="...$109.42 billion..." was compared against SEC
evidence as if it meant 109.42 rather than 109.42e9.
"""

from __future__ import annotations

from decimal import Decimal

from app.parser import resolve_context_scale
from core.compiler import compile_claim
from core.engine import verify
from core.financial.document import FinancialPeriod
from core.models import Claim, Entity, Metric


def _sec_facts(value: float):
    return {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "start": "2026-04-01",
                                "end": "2026-06-30",
                                "val": value,
                                "accn": "0000320193-26-000013",
                                "fy": 2026,
                                "fp": "Q3",
                                "form": "10-Q",
                                "filed": "2026-07-30",
                            },
                        ]
                    }
                }
            }
        }
    }


def _apple_claim(raw_value: float, context_text: str) -> Claim:
    return Claim(
        question="What was Apple revenue in Q3 FY2026?",
        raw_value=raw_value,
        context_text=context_text,
        entity=Entity(name="apple", ticker="AAPL", cik="0000320193"),
        metric=Metric(name="revenue", canonical_name="revenue"),
        period="Q3 FY2026",
        period_struct=FinancialPeriod(kind="quarterly", fiscal_year=2026, fiscal_quarter=3),
    )


# ---------------------------------------------------------------------------
# Unit-level: resolve_context_scale
# ---------------------------------------------------------------------------

def test_resolve_context_scale_finds_billion_multiplier():
    match = resolve_context_scale(
        109.42, "Apple reported revenue of $109.42 billion in Q3 FY2026."
    )
    assert match is not None
    assert match.multiplier == Decimal("1e9")
    assert match.scale_word == "billion"
    assert match.currency == "USD"


def test_resolve_context_scale_does_not_select_fiscal_year_as_claim_value():
    # "Q3 FY2026" must never be mistaken for the numeric claim itself.
    match = resolve_context_scale(
        109.42, "Apple reported revenue of $109.42 billion in Q3 FY2026."
    )
    assert match is not None
    assert match.matched_token.strip().startswith("$109.42")
    assert "2026" not in match.matched_token


def test_resolve_context_scale_fails_closed_with_no_matching_candidate():
    assert resolve_context_scale(109.42, "Apple reported revenue of $94.04 billion.") is None


def test_resolve_context_scale_fails_closed_on_ambiguous_scale():
    match = resolve_context_scale(
        109.42,
        "Revenue was $109.42 billion; another estimate was $109.42 million.",
    )
    assert match is None


def test_resolve_context_scale_million_multiplier():
    match = resolve_context_scale(42.5, "Net income was $42.5 million for the quarter.")
    assert match is not None
    assert match.multiplier == Decimal("1e6")
    assert match.scale_word == "million"


def test_resolve_context_scale_no_context_returns_none():
    assert resolve_context_scale(109.42, None) is None
    assert resolve_context_scale(109.42, "") is None


def test_resolve_context_scale_no_raw_value_returns_none():
    assert resolve_context_scale(None, "Revenue was $109.42 billion.") is None


# ---------------------------------------------------------------------------
# Claim-compilation level: compile_claim applies the bridge
# ---------------------------------------------------------------------------

def test_compile_claim_scales_raw_value_from_context():
    compiled = compile_claim(_apple_claim(109.42, "Apple reported revenue of $109.42 billion in Q3 FY2026."))
    assert compiled.raw_value == 109_420_000_000.0
    assert compiled.metadata["scale_bridge"]["applied"] is True
    assert compiled.metadata["scale_bridge"]["scale_word"] == "billion"


def test_compile_claim_leaves_raw_value_untouched_without_context():
    compiled = compile_claim(_apple_claim(109.42, None))
    assert compiled.raw_value == 109.42
    assert "scale_bridge" not in compiled.metadata


def test_compile_claim_leaves_raw_value_untouched_on_ambiguous_context():
    compiled = compile_claim(
        _apple_claim(
            109.42,
            "Revenue was $109.42 billion; another estimate was $109.42 million.",
        )
    )
    assert compiled.raw_value == 109.42
    assert compiled.metadata["scale_bridge"]["applied"] is False


# ---------------------------------------------------------------------------
# End-to-end: full verify() pipeline against mocked SEC evidence
# ---------------------------------------------------------------------------

def test_scale_bridged_claim_verifies_against_matching_sec_evidence(monkeypatch):
    monkeypatch.setattr("ingestion.db.get_fundamentals", lambda ticker: [])
    monkeypatch.setattr(
        "ingestion.sec_edgar.fetch_company_facts",
        lambda ticker: _sec_facts(109_420_000_000),
    )

    claim = _apple_claim(109.42, "Apple reported revenue of $109.42 billion in Q3 FY2026.")
    result = verify(claim)

    assert result.verified_value == 109_420_000_000.0
    assert result.trust_score.status.value == "verified"


def test_scale_bridged_claim_contradicts_mismatched_sec_evidence(monkeypatch):
    monkeypatch.setattr("ingestion.db.get_fundamentals", lambda ticker: [])
    monkeypatch.setattr(
        "ingestion.sec_edgar.fetch_company_facts",
        lambda ticker: _sec_facts(109_420_000_000),
    )

    claim = _apple_claim(94.04, "Apple reported revenue of $94.04 billion in Q3 FY2026.")
    result = verify(claim)

    assert result.trust_score.status.value == "contradicted"


def test_unscaled_raw_value_without_context_still_contradicts_sec_evidence(monkeypatch):
    """Sanity check: with no context_text to bridge from, a bare small
    raw_value naturally fails to match large SEC evidence -- this is the
    pre-3C.1 behavior for claims that never supplied context, and must
    remain unaffected."""
    monkeypatch.setattr("ingestion.db.get_fundamentals", lambda ticker: [])
    monkeypatch.setattr(
        "ingestion.sec_edgar.fetch_company_facts",
        lambda ticker: _sec_facts(109_420_000_000),
    )

    claim = _apple_claim(109.42, None)
    result = verify(claim)

    assert result.trust_score.status.value == "contradicted"
