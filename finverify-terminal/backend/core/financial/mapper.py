"""Map SEC XBRL CompanyFacts payloads into canonical financial documents."""

from collections import defaultdict
from datetime import date

from .concepts import ConceptRegistry
from .document import FinancialDocument, FinancialPeriod, FinancialStatement, FinancialStatementItem


class StatementMapper:
    def __init__(self, registry: ConceptRegistry):
        self.registry = registry

    def map_xbrl_to_document(self, facts: dict, metadata: dict | None = None) -> FinancialDocument:
        metadata = metadata or {}
        candidates = self._collect_candidates(facts, metadata)
        selected_period = self._select_period_key(candidates, metadata.get("filing_type"))
        statement_items: dict[str, list[FinancialStatementItem]] = defaultdict(list)
        periods: dict[tuple[str, str, int, int | None], FinancialPeriod] = {}

        if selected_period is not None:
            for candidate in candidates:
                if self._period_key(candidate["period"]) != selected_period:
                    continue
                statement_items[candidate["statement"]].append(candidate["item"])
                periods[selected_period] = candidate["period"]

        filing_date = self._parse_date(
            metadata.get("filing_date"),
            default=(periods[selected_period].end_date if selected_period is not None else date.today()),
        )
        filing_type = str(metadata.get("filing_type") or (next(iter(statement_items.values()))[0].source_ref.split()[0] if statement_items else "10-K"))
        statements = {
            name: FinancialStatement(
                name=name,
                items=items,
                period=items[0].period,
                currency=self._currency_for(items),
            )
            for name, items in statement_items.items()
        }
        return FinancialDocument(
            company_name=str(metadata.get("company_name") or facts.get("entityName") or "Unknown Entity"),
            ticker=metadata.get("ticker"),
            cik=str(metadata.get("cik") or facts.get("cik") or "") or None,
            filing_type=filing_type,
            filing_date=filing_date,
            periods=list(periods.values()),
            statements=statements,
            metadata={str(key): str(value) for key, value in metadata.items() if value is not None},
            source_url=metadata.get("source_url"),
        )

    def _collect_candidates(self, facts: dict, metadata: dict) -> list[dict]:
        candidates: list[dict] = []
        us_gaap = facts.get("facts", {}).get("us-gaap", {})
        desired_form = metadata.get("filing_type")

        for raw_tag, concept_payload in us_gaap.items():
            concept_name = self.registry.resolve_xbrl_tag(f"us-gaap:{raw_tag}")
            if concept_name is None:
                continue
            concept_spec = self.registry.get_concept(concept_name)
            for unit_name, entries in concept_payload.get("units", {}).items():
                for entry in entries:
                    form = entry.get("form")
                    if desired_form and form and form != desired_form:
                        continue
                    if form not in {"10-K", "10-Q", None}:
                        continue
                    if entry.get("val") is None or entry.get("end") is None:
                        continue
                    period = self._build_period(entry)
                    source_ref = self._build_source_ref(entry)
                    candidates.append(
                        {
                            "concept": concept_name,
                            "statement": concept_spec.get("statement", "IncomeStatement"),
                            "form": form or desired_form or "10-K",
                            "filed": self._parse_date(entry.get("filed"), default=period.end_date),
                            "period": period,
                            "item": FinancialStatementItem(
                                concept=concept_name,
                                value=float(entry["val"]),
                                unit=concept_spec.get("unit", unit_name),
                                period=period,
                                source_ref=source_ref,
                                xbrl_tag=f"us-gaap:{raw_tag}",
                            ),
                        }
                    )
        return candidates

    def _select_period_key(self, candidates: list[dict], desired_form: str | None) -> tuple[str, str, int, int | None] | None:
        if not candidates:
            return None
        sorted_candidates = sorted(
            candidates,
            key=lambda candidate: (
                candidate["form"] == (desired_form or candidate["form"]),
                candidate["filed"],
                candidate["period"].end_date,
            ),
            reverse=True,
        )
        return self._period_key(sorted_candidates[0]["period"])

    @staticmethod
    def _build_period(entry: dict) -> FinancialPeriod:
        end_date = StatementMapper._parse_date(entry.get("end"), default=date.today())
        start_date = StatementMapper._parse_date(entry.get("start"), default=end_date)
        fiscal_year = int(entry.get("fy") or end_date.year)
        fp = str(entry.get("fp") or "")
        fiscal_quarter = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}.get(fp)
        return FinancialPeriod(
            start_date=start_date,
            end_date=end_date,
            fiscal_year=fiscal_year,
            fiscal_quarter=fiscal_quarter,
        )

    @staticmethod
    def _build_source_ref(entry: dict) -> str:
        form = entry.get("form") or "filing"
        filed = entry.get("filed") or entry.get("end") or "unknown"
        accn = entry.get("accn")
        if accn:
            return f"{form} filed {filed} accn {accn}"
        return f"{form} filed {filed}"

    @staticmethod
    def _currency_for(items: list[FinancialStatementItem]) -> str:
        for item in items:
            if item.unit == "USD":
                return "USD"
        return items[0].unit if items else "USD"

    @staticmethod
    def _period_key(period: FinancialPeriod) -> tuple[str, str, int, int | None]:
        return (
            period.start_date.isoformat(),
            period.end_date.isoformat(),
            period.fiscal_year,
            period.fiscal_quarter,
        )

    @staticmethod
    def _parse_date(value: str | None, default: date) -> date:
        if not value:
            return default
        return date.fromisoformat(str(value))
