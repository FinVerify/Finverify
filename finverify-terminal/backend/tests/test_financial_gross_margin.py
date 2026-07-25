"""Tests for Milestone 1 gross margin financial reasoning."""

from pathlib import Path

import pytest

from core.financial.concepts import ConceptRegistry
from core.financial.contract import EvidenceContractBuilder
from core.financial.formula import FormulaEngine
from core.financial.mapper import StatementMapper
from core.financial.parser import TaskParser
from core.financial.planner import ExecutionPlanner
from core.financial.reasoning import ReasoningEngine


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "concepts.yaml"


def make_company_facts(revenue: float = 1000.0, cogs: float | None = 617.0, gross_profit: float | None = 383.0) -> dict:
    us_gaap = {
        "Revenues": {
            "units": {
                "USD": [
                    {
                        "start": "2023-10-01",
                        "end": "2024-09-30",
                        "val": revenue,
                        "accn": "0000320193-24-000123",
                        "fy": 2024,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2024-11-01",
                    }
                ]
            }
        }
    }
    if cogs is not None:
        us_gaap["CostOfGoodsAndServicesSold"] = {
            "units": {
                "USD": [
                    {
                        "start": "2023-10-01",
                        "end": "2024-09-30",
                        "val": cogs,
                        "accn": "0000320193-24-000123",
                        "fy": 2024,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2024-11-01",
                    }
                ]
            }
        }
    if gross_profit is not None:
        us_gaap["GrossProfit"] = {
            "units": {
                "USD": [
                    {
                        "start": "2023-10-01",
                        "end": "2024-09-30",
                        "val": gross_profit,
                        "accn": "0000320193-24-000123",
                        "fy": 2024,
                        "fp": "FY",
                        "form": "10-K",
                        "filed": "2024-11-01",
                    }
                ]
            }
        }
    return {
        "cik": 320193,
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": us_gaap,
        },
    }


def make_registry() -> ConceptRegistry:
    return ConceptRegistry(CONFIG_PATH)


def make_document(revenue: float = 1000.0, cogs: float | None = 617.0, gross_profit: float | None = 383.0):
    registry = make_registry()
    mapper = StatementMapper(registry)
    document = mapper.map_xbrl_to_document(
        make_company_facts(revenue=revenue, cogs=cogs, gross_profit=gross_profit),
        {
            "company_name": "Apple Inc.",
            "ticker": "AAPL",
            "cik": "0000320193",
            "filing_type": "10-K",
            "filing_date": "2024-11-01",
            "source_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019324000123/",
        },
    )
    return registry, document


def test_concept_registry_loads_gross_margin():
    registry = make_registry()
    assert registry.get_concept("GrossMargin")["formula"] == "(Revenue - CostOfGoodsSold) / Revenue"
    assert registry.resolve_alias("gross profit margin") == "GrossMargin"
    assert registry.resolve_xbrl_tag("us-gaap:Revenues") == "Revenue"


def test_statement_mapper_maps_mock_xbrl_payload():
    registry, document = make_document()
    assert document.company_name == "Apple Inc."
    assert document.filing_type == "10-K"
    assert "IncomeStatement" in document.statements
    items = {item.concept: item for item in document.statements["IncomeStatement"].items}
    assert items["Revenue"].value == pytest.approx(1000.0)
    assert items["CostOfGoodsSold"].value == pytest.approx(617.0)
    assert items["GrossProfit"].xbrl_tag == "us-gaap:GrossProfit"


def test_formula_engine_computes_without_eval():
    engine = FormulaEngine()
    assert engine.evaluate("(Revenue - CostOfGoodsSold) / Revenue", {"Revenue": 1000.0, "CostOfGoodsSold": 617.0}) == pytest.approx(0.383)


def test_formula_engine_rejects_unsafe_ast():
    engine = FormulaEngine()
    with pytest.raises(ValueError):
        engine.evaluate("__import__('os').system('dir')", {})


def test_evidence_contract_builder_includes_metadata():
    _, document = make_document()
    contract = EvidenceContractBuilder.build(document, ["Revenue", "CostOfGoodsSold"])
    assert contract.missing == []
    assert [item.concept for item in contract.provided] == ["Revenue", "CostOfGoodsSold"]
    assert any(item.concept == "GrossProfit" for item in contract.optional)
    assert contract.provided[0].statement == "IncomeStatement"
    assert contract.provided[0].xbrl_tag == "us-gaap:Revenues"


def test_execution_planner_generates_expected_steps():
    registry, document = make_document()
    planner = ExecutionPlanner(registry)
    task = TaskParser.parse("What is the gross margin for this filing?")
    steps = planner.plan(task, document)
    assert [step["action"] for step in steps] == ["retrieve", "compute", "verify", "build_contract"]
    assert steps[0]["params"]["concepts"] == ["Revenue", "CostOfGoodsSold"]


def test_reasoning_engine_handles_missing_evidence_gracefully():
    registry, document = make_document(cogs=None)
    engine = ReasoningEngine(registry)
    task = TaskParser.parse("What is the gross margin for this filing?")
    result = engine.answer(task, document)
    assert result["status"] == "incomplete"
    assert result["computed_value"] is None
    assert result["missing"] == ["CostOfGoodsSold"]
    assert result["trust"] is None
    assert "required evidence is missing" in result["explanation"]


def test_reasoning_engine_returns_complete_answer_with_citations():
    registry, document = make_document()
    engine = ReasoningEngine(registry)
    task = TaskParser.parse("What is the gross margin for this filing?")
    result = engine.answer(task, document)
    assert result["status"] == "complete"
    assert result["computed_value"] == pytest.approx(0.383)
    assert result["formula"] == "(Revenue - CostOfGoodsSold) / Revenue"
    assert result["trust"].label == "HIGH"
    assert len(result["citations"]) == 2
    assert result["citations"][0]["statement"] == "IncomeStatement"
    assert result["citations"][0]["xbrl_tag"] is not None
    assert "Computed GrossMargin deterministically" in result["explanation"]
