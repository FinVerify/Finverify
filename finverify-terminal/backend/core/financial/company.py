"""Deterministic company resolution for financial reasoning queries."""

from dataclasses import dataclass
import re



@dataclass(frozen=True)
class ResolvedCompany:
    ticker: str
    cik: str
    matched_text: str


_COMPANY_ALIASES: dict[str, str] = {
    "aapl": "AAPL",
    "apple": "AAPL",
    "apple inc": "AAPL",
    "apple inc.": "AAPL",
    "msft": "MSFT",
    "microsoft": "MSFT",
    "microsoft corporation": "MSFT",
    "nvda": "NVDA",
    "nvidia": "NVDA",
    "nvidia corporation": "NVDA",
    "tsla": "TSLA",
    "tesla": "TSLA",
    "tesla inc": "TSLA",
    "tesla inc.": "TSLA",
    "jpm": "JPM",
    "jpmorgan": "JPM",
    "jpmorgan chase": "JPM",
    "jpmorgan chase & co": "JPM",
    "jpmorgan chase & co.": "JPM",
    "goldman": "GS",
    "goldman sachs": "GS",
    "goldman sachs group": "GS",
    "goldman sachs group inc": "GS",
    "goldman sachs group inc.": "GS",
    "gs": "GS",
}

_ALIASES_BY_LENGTH = sorted(_COMPANY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
_TICKER_PATTERN = re.compile(r"\b[A-Z]{2,5}\b")


def resolve_company(query: str) -> ResolvedCompany | None:
    """Resolve one unambiguous company; never guess among multiple entities."""
    # Lazy import avoids the ingestion module's optional core.engine import
    # cycle when the reusable resolver is loaded by core.engine itself.
    from ingestion.sec_edgar import TICKER_TO_CIK
    matches: dict[str, str] = {}
    for match in _TICKER_PATTERN.finditer(query):
        ticker = match.group(0).upper()
        if ticker in TICKER_TO_CIK:
            matches[ticker] = match.group(0)

    lower_query = query.lower()
    for alias, ticker in _ALIASES_BY_LENGTH:
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lower_query):
            matches.setdefault(ticker, alias)

    # A possessive subject followed by a relationship noun is not a claim
    # about that company itself (e.g. "Apple's suppliers").
    if re.search(r"\b(?:suppliers?|customers?|vendors?|partners?|competitors?|subsidiaries)\b", lower_query):
        return None
    if len(matches) != 1:
        return None
    ticker, matched_text = next(iter(matches.items()))
    return ResolvedCompany(ticker=ticker, cik=TICKER_TO_CIK[ticker], matched_text=matched_text)
