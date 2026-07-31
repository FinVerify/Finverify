"""Financial-document reasoning primitives for Milestone 1."""

from .company import ResolvedCompany, resolve_company
from .concepts import ConceptRegistry
from .constraints import (
    ConstraintConfigError,
    ConstraintResult,
    ConstraintVerifier,
    Dependency,
    Equation,
    EvaluationResult,
    Expression,
    FormulaParser,
    Variable,
    Violation,
    load_equations_from_concepts,
)
from .contract import EvidenceContract, EvidenceContractBuilder, EvidenceItem
from .document import FinancialDocument, FinancialPeriod, FinancialStatement, FinancialStatementItem
from .formula import FormulaEngine
from .mapper import StatementMapper
from .parser import TaskParser
from .planner import ExecutionPlanner
from .reasoning import ReasoningEngine
from .service import FinancialDocumentService
from .tasks import FinancialTask, TaskRegistry, TaskType

__all__ = [
    "ConstraintConfigError",
    "ConstraintResult",
    "ConstraintVerifier",
    "ConceptRegistry",
    "Dependency",
    "Equation",
    "EvaluationResult",
    "FinancialDocumentService",
    "EvidenceContract",
    "EvidenceContractBuilder",
    "EvidenceItem",
    "Expression",
    "ExecutionPlanner",
    "FinancialDocument",
    "FinancialPeriod",
    "FinancialStatement",
    "FinancialStatementItem",
    "FinancialTask",
    "FormulaEngine",
    "FormulaParser",
    "ReasoningEngine",
    "ResolvedCompany",
    "StatementMapper",
    "TaskParser",
    "TaskRegistry",
    "TaskType",
    "Variable",
    "Violation",
    "load_equations_from_concepts",
    "resolve_company",
]
