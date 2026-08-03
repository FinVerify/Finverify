"""Financial-document reasoning primitives for Milestone 1.

This package uses lazy exports so importing a narrow submodule like
`core.financial.document` does not also trigger heavier financial-service
imports that depend back on the core verification engine.
"""

from __future__ import annotations

from importlib import import_module

_EXPORTS = {
    "ConstraintConfigError": (".constraints", "ConstraintConfigError"),
    "ConstraintResult": (".constraints", "ConstraintResult"),
    "ConstraintVerifier": (".constraints", "ConstraintVerifier"),
    "ConceptRegistry": (".concepts", "ConceptRegistry"),
    "Dependency": (".constraints", "Dependency"),
    "Equation": (".constraints", "Equation"),
    "EvaluationResult": (".constraints", "EvaluationResult"),
    "FinancialDocumentService": (".service", "FinancialDocumentService"),
    "EvidenceContract": (".contract", "EvidenceContract"),
    "EvidenceContractBuilder": (".contract", "EvidenceContractBuilder"),
    "EvidenceItem": (".contract", "EvidenceItem"),
    "Expression": (".constraints", "Expression"),
    "ExecutionPlanner": (".planner", "ExecutionPlanner"),
    "FinancialDocument": (".document", "FinancialDocument"),
    "FinancialPeriod": (".document", "FinancialPeriod"),
    "FinancialStatement": (".document", "FinancialStatement"),
    "FinancialStatementItem": (".document", "FinancialStatementItem"),
    "FinancialTask": (".tasks", "FinancialTask"),
    "FormulaEngine": (".formula", "FormulaEngine"),
    "FormulaParser": (".constraints", "FormulaParser"),
    "ReasoningEngine": (".reasoning", "ReasoningEngine"),
    "ResolvedCompany": (".company", "ResolvedCompany"),
    "StatementMapper": (".mapper", "StatementMapper"),
    "TaskParser": (".parser", "TaskParser"),
    "TaskRegistry": (".tasks", "TaskRegistry"),
    "TaskType": (".tasks", "TaskType"),
    "Variable": (".constraints", "Variable"),
    "Violation": (".constraints", "Violation"),
    "load_equations_from_concepts": (".constraints", "load_equations_from_concepts"),
    "resolve_company": (".company", "resolve_company"),
}

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


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name, __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
