"""Deterministic reasoning over canonical financial documents."""

from core.models import Claim, Evidence, MathResult, Source, VerificationContext
from core.trust_engine import compute_trust
from core.engine import verify

from .concepts import ConceptRegistry
from .contract import EvidenceContract, EvidenceItem
from .document import FinancialDocument, FinancialStatementItem
from .formula import FormulaEngine
from .planner import ExecutionPlanner
from .tasks import FinancialTask, TaskRegistry


class ReasoningEngine:
    def __init__(self, registry: ConceptRegistry, task_registry: TaskRegistry | None = None):
        self.registry = registry
        self.task_registry = task_registry or TaskRegistry()
        self.planner = ExecutionPlanner(registry, self.task_registry)
        self.formula_engine = FormulaEngine()

    def answer(self, task: FinancialTask, doc: FinancialDocument) -> dict:
        plan = self.planner.plan(task, doc)
        if not plan or task.metric is None:
            return {
                "task": task,
                "computed_value": None,
                "evidence_contract": None,
                "trust": None,
                "citations": [],
                "formula": None,
                "explanation": "Task is unsupported for Milestone 1.",
                "status": "incomplete",
                "missing": [],
            }

        spec = self.registry.get_concept(task.metric)
        required = spec.get("requires", []) or [task.metric]
        values, contract = self._resolve_required_values(doc, required)
        citations = [self._build_citation(item, doc) for item in contract.provided]
        if contract.missing:
            return {
                "task": task,
                "computed_value": None,
                "evidence_contract": contract,
                "trust": None,
                "citations": citations,
                "formula": None,
                "explanation": self._build_incomplete_explanation(task.metric, contract.missing),
                "status": "incomplete",
                "missing": contract.missing,
            }

        formula = spec.get("formula")
        computed_value = self.formula_engine.evaluate(formula, values) if formula else values.get(task.metric)

        reported_item = self._find_concept_item(doc, task.metric)
        verification = None
        if reported_item is not None and computed_value is not None:
            verification = verify(
                Claim(
                    question=f"What is the reported {task.metric} for this filing?",
                    raw_value=reported_item.value,
                    actual_value=computed_value,
                    metadata={"source_url": doc.source_url or ""},
                )
            )

        trust = self._compute_primary_trust(task, doc, computed_value, contract.provided)
        return {
            "task": task,
            "computed_value": computed_value,
            "reported_value": reported_item.value if reported_item is not None else None,
            "verification": verification,
            "evidence_contract": contract,
            "trust": trust,
            "citations": citations,
            "formula": formula,
            "explanation": self._build_complete_explanation(task.metric, computed_value, contract.provided),
            "status": "complete",
            "missing": [],
        }

    def _resolve_required_values(self, doc: FinancialDocument, required_tokens: list[str]) -> tuple[dict[str, float], EvidenceContract]:
        values: dict[str, float] = {}
        provided: list[EvidenceItem] = []
        optional: list[EvidenceItem] = []
        missing: list[str] = []
        required_set = set(required_tokens)

        for token in required_tokens:
            resolved = self._resolve_required_item(doc, token)
            if resolved is None:
                missing.append(token)
                continue
            values[token] = resolved.value
            provided.append(
                EvidenceItem(
                    concept=token,
                    value=resolved.value,
                    unit=resolved.unit,
                    statement=self._statement_name_for_item(doc, resolved),
                    source_ref=resolved.source_ref,
                    xbrl_tag=resolved.xbrl_tag,
                )
            )

        for statement in doc.statements.values():
            for item in statement.items:
                if item.concept in required_set:
                    continue
                optional.append(
                    EvidenceItem(
                        concept=item.concept,
                        value=item.value,
                        unit=item.unit,
                        statement=statement.name,
                        source_ref=item.source_ref,
                        xbrl_tag=item.xbrl_tag,
                    )
                )

        return values, EvidenceContract(
            required=required_tokens,
            provided=provided,
            missing=missing,
            optional=optional,
        )

    def _resolve_required_item(self, doc: FinancialDocument, token: str) -> FinancialStatementItem | None:
        if token.endswith("_prior"):
            base_concept = token[: -len("_prior")]
            matches = self._find_concept_items(doc, base_concept)
            return matches[1] if len(matches) > 1 else None
        matches = self._find_concept_items(doc, token)
        return matches[0] if matches else None

    def _compute_primary_trust(
        self,
        task: FinancialTask,
        doc: FinancialDocument,
        computed_value: float | None,
        evidence_items: list[EvidenceItem],
    ):
        claim = Claim(
            question=f"What is {task.metric} for this filing?",
            raw_value=computed_value,
            metadata={"source_url": doc.source_url or ""},
        )
        context = VerificationContext(
            claim=claim,
            provider="sec_edgar",
            provider_metadata={"tier": "primary"},
            evidence_mode="retrieved",
            current_value=computed_value,
        )
        evidence = [
            Evidence(
                source=Source(
                    name="SEC EDGAR",
                    kind="primary_filing",
                    authority=1.0,
                    url=doc.source_url,
                ),
                claim=claim.question,
                value=item.value,
                period=str(doc.filing_date.year),
                locator=item.source_ref,
            )
            for item in evidence_items
        ]
        math_result = MathResult(verified_value=computed_value)
        return compute_trust(context, math_result, evidence)

    @staticmethod
    def _find_concept_item(doc: FinancialDocument, concept: str) -> FinancialStatementItem | None:
        matches = ReasoningEngine._find_concept_items(doc, concept)
        return matches[0] if matches else None

    @staticmethod
    def _find_concept_items(doc: FinancialDocument, concept: str) -> list[FinancialStatementItem]:
        matches: list[FinancialStatementItem] = []
        for statement in doc.statements.values():
            for item in statement.items:
                if item.concept == concept:
                    matches.append(item)
        return sorted(matches, key=lambda item: item.period.end_date, reverse=True)

    @staticmethod
    def _statement_name_for_item(doc: FinancialDocument, target: FinancialStatementItem) -> str:
        for statement in doc.statements.values():
            for item in statement.items:
                if item is target:
                    return statement.name
        return "UnknownStatement"

    @staticmethod
    def _build_citation(item: EvidenceItem, doc: FinancialDocument) -> dict:
        return {
            "concept": item.concept,
            "value": item.value,
            "unit": item.unit,
            "statement": item.statement,
            "source_ref": item.source_ref,
            "xbrl_tag": item.xbrl_tag,
            "company_name": doc.company_name,
            "filing_type": doc.filing_type,
            "filing_date": doc.filing_date.isoformat(),
            "source_url": doc.source_url,
        }

    @staticmethod
    def _build_incomplete_explanation(metric: str, missing: list[str]) -> str:
        missing_text = ", ".join(ReasoningEngine._label_for_token(token) for token in missing)
        return f"Unable to compute {metric} because required evidence is missing: {missing_text}."

    @staticmethod
    def _build_complete_explanation(metric: str, computed_value: float | None, evidence_items: list[EvidenceItem]) -> str:
        evidence_names = ", ".join(ReasoningEngine._label_for_token(item.concept) for item in evidence_items)
        if computed_value is None:
            return f"No computed value was produced for {metric}."
        return f"Computed {metric} deterministically from {evidence_names}; result={computed_value:.6f}."

    @staticmethod
    def _label_for_token(token: str) -> str:
        if token.endswith("_prior"):
            return f"{token[: -len('_prior')]} (prior period)"
        return token
