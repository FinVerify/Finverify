"""SEC EDGAR evidence adapter over the existing ingestion/cache implementation."""

from datetime import datetime, timezone

from core.models import Claim, Evidence, Source


class SECProvider:
    name = "sec_edgar"
    metadata = {"tier": "primary"}

    def can_handle(self, claim: Claim) -> bool:
        return bool(claim.entity and (claim.entity.ticker or claim.entity.cik))

    def retrieve(self, claim: Claim) -> list[Evidence]:
        ticker = claim.entity.ticker if claim.entity else None
        if not ticker:
            return []
        from ingestion.db import get_fundamentals

        results = []
        for row in get_fundamentals(ticker):
            results.append(Evidence(
                source=Source(
                    name="SEC EDGAR",
                    kind="primary_filing",
                    authority=1.0,
                    url=row.get("source_url") or None,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                ),
                claim=claim.question,
                value=row.get("verified_value"),
                period=row.get("period"),
                locator=row.get("metric_name"),
                entity=ticker,
            ))
        return results
