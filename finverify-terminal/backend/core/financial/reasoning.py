"""Deterministic reasoning over canonical financial documents."""

from core.models import Claim, Evidence, MathResult, Source, VerificationContext
from core.trust_engine import compute_trust
from core.engine import verify

from .concepts import ConceptRegistry
from .contract import EvidenceContractBuilder, EvidenceItem
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

        values: dict[str, float] = {}
        contract = None
        for step in plan:
            if step["action"] == "retrieve":
                required = step["params"]["concepts"]
                contract = EvidenceContractBuilder.build(doc, required)
                for item in contract.provided:
                    values[item.concept] = item.value

        assert contract is not None
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

        spec = self.registry.get_concept(task.metric)
        formula = spec.get("formula")
        computed_value = self.formula_engine.evaluate(formula, values) if formula else None

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
        for statement in doc.statements.values():
            for item in statement.items:
                if item.concept == concept:
                    return item
        return None

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
        missing_text = ", ".join(missing)
        return f"Unable to compute {metric} because required evidence is missing: {missing_text}."

    @staticmethod
    def _build_complete_explanation(metric: str, computed_value: float | None, evidence_items: list[EvidenceItem]) -> str:
        evidence_names = ", ".join(item.concept for item in evidence_items)
        if computed_value is None:
            return f"No computed value was produced for {metric}."
        return f"Computed {metric} deterministically from {evidence_names}; result={computed_value:.6f}."
