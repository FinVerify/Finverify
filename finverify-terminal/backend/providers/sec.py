"""SEC EDGAR evidence adapter over the existing ingestion/cache implementation."""

from datetime import datetime, timezone

from core.models import Claim, Evidence, Source


class SECProvider:
    name = "sec_edgar"
    metadata = {"tier": "primary"}

    def can_handle(self, claim: Claim) -> bool:
        return bool(claim.entity and (claim.entity.ticker or claim.entity.cik))

    @staticmethod
    def _to_evidence(rows: list[dict], claim: Claim) -> list[Evidence]:
        ticker = claim.entity.ticker if claim.entity else None
        return [
            Evidence(
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
            )
            for row in rows
            if row.get("verified_value") is not None
        ]

    def retrieve(self, claim: Claim) -> list[Evidence]:
        ticker = claim.entity.ticker if claim.entity else None
        if not ticker:
            return []

        from ingestion.db import get_fundamentals

        cached_rows = get_fundamentals(ticker)

        # The fundamentals DB is a cache, not an authority.  If it does not
        # contain evidence for the requested metric/period, refresh from SEC
        # CompanyFacts instead of returning stale rows and pretending they are
        # candidates for the current claim.
        if claim.metric is None or claim.period_struct is None:
            return self._to_evidence(cached_rows, claim)

        target_metric = claim.metric.canonical_name or claim.metric.name
        target_period = claim.period_struct

        from core.financial.concepts import ConceptRegistry
        from core.financial.period import parse_period_string, periods_compatible
        from pathlib import Path

        registry = ConceptRegistry(Path(__file__).resolve().parents[1] / "config" / "concepts.yaml")
        canonical_target = registry.resolve_alias(target_metric) or target_metric
        statement = registry.get_concept(canonical_target).get("statement")
        statement_type = "instant" if statement == "BalanceSheet" else "duration" if statement in {"IncomeStatement", "CashFlowStatement"} else None

        matching_cached = []
        for row in cached_rows:
            row_metric = registry.resolve_alias(str(row.get("metric_name") or ""))
            if row_metric != canonical_target:
                continue
            evidence_period = parse_period_string(row.get("period"), statement_period_type=statement_type)
            if periods_compatible(target_period, evidence_period) == "MATCH":
                matching_cached.append(row)

        if matching_cached:
            return self._to_evidence(matching_cached, claim)

        # No compatible cache entry: fetch the authoritative SEC CompanyFacts
        # feed and extract only the requested metric/period.  This keeps stale
        # local data from blocking current-quarter verification.
        try:
            from ingestion.sec_edgar import extract_xbrl_metrics, fetch_company_facts

            facts = fetch_company_facts(ticker)
            fresh = extract_xbrl_metrics(
                facts,
                ticker,
                target_metric=canonical_target.lower(),
                target_period=target_period,
            )
            if fresh:
                return self._to_evidence(
                    [dict(row, verified_value=row.get("raw_value")) for row in fresh],
                    claim,
                )
        except Exception as exc:
            # Evidence retrieval is fail-closed.  Stale rows remain available
            # only when explicitly compatible; a refresh failure must never
            # become independent evidence by accident.
            import logging
            logging.getLogger(__name__).warning(
                "SEC live evidence refresh failed for %s: %s", ticker, exc
            )

        return []
