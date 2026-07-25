"""
Query Classifier
================
Classifies incoming queries into four modes:
  - financial_reasoning: deterministic SEC filing reasoning
  - numerical:          run through DVL pipeline
  - advisory:           skip DVL, return LLM text unverified
  - general:            LLM response only
"""

import re

# ---------------------------------------------------------------------------
# Keyword banks
# ---------------------------------------------------------------------------

NUMERICAL_KEYWORDS: list[str] = [
    "ratio", "margin", "growth", "change", "percent", "increase",
    "decrease", "yoy", "revenue", "income", "earnings", "eps",
    "yield", "return", "cet1", "roa", "roe", "ebitda",
]

ADVISORY_KEYWORDS: list[str] = [
    "invest", "buy", "sell", "should i", "recommend", "advice",
    "portfolio", "where", "which stock", "best", "worst",
]

FINANCIAL_REASONING_KEYWORDS: list[str] = [
    "gross margin",
    "gross profit margin",
    "operating margin",
    "operating income",
    "net income",
    "cash flow",
    "revenue",
    "earnings",
    "yoy",
    "year over year",
    "qoq",
    "quarter over quarter",
]

FINANCIAL_REASONING_VERBS: list[str] = [
    "what is",
    "what was",
    "compare",
    "show",
    "calculate",
]

_COMPANY_CONTEXT = re.compile(
    r"\b(apple|microsoft|tesla|nvidia|jpmorgan|goldman|aapl|msft|tsla|nvda|jpm|gs)\b"
)


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def classify_query(query: str) -> str:
    """
    Classify a query string into one of four modes.

    Returns
    -------
    "financial_reasoning" | "advisory" | "numerical" | "general"
    """
    q = query.lower()
    has_reasoning_metric = any(keyword in q for keyword in FINANCIAL_REASONING_KEYWORDS)
    has_reasoning_verb = any(verb in q for verb in FINANCIAL_REASONING_VERBS)
    has_reasoning_context = "filing" in q or "sec" in q or "compare" in q or bool(_COMPANY_CONTEXT.search(q))

    if any(k in q for k in ADVISORY_KEYWORDS):
        return "advisory"
    if has_reasoning_metric and has_reasoning_verb and has_reasoning_context:
        return "financial_reasoning"
    if any(k in q for k in NUMERICAL_KEYWORDS):
        return "numerical"
    return "general"
