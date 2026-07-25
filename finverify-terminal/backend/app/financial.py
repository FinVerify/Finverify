"""Financial reasoning query handling for the shared /query endpoint."""

from app.models import QueryResponse
from app.parser import format_number_display
from core.financial import FinancialDocumentService, ReasoningEngine, TaskParser, resolve_company


def build_financial_query_response(question: str, document_service: FinancialDocumentService) -> QueryResponse:
    company = resolve_company(question)
    if company is None:
        return QueryResponse(
            question=question,
            raw_text="Financial reasoning requires a supported company or ticker in the question.",
            raw_number=None,
            verified_number=None,
            correction_log=[],
            trust_score="LOW",
            trust_color="#f87171",
            display_value="Company not resolved",
            mode="financial_reasoning",
            verified=False,
        )

    task = TaskParser.parse(question)
    if task.metric is None:
        return QueryResponse(
            question=question,
            raw_text="The financial reasoning engine could not determine which supported metric to answer.",
            raw_number=None,
            verified_number=None,
            correction_log=[],
            trust_score="LOW",
            trust_color="#f87171",
            display_value="Unsupported financial task",
            mode="financial_reasoning",
            verified=False,
        )

    try:
        document = document_service.load_document(company.ticker)
    except Exception as exc:
        return QueryResponse(
            question=question,
            raw_text=f"Unable to load SEC filing data for {company.ticker}: {exc}",
            raw_number=None,
            verified_number=None,
            correction_log=[],
            trust_score="LOW",
            trust_color="#f87171",
            display_value="SEC data unavailable",
            mode="financial_reasoning",
            verified=False,
        )

    engine = ReasoningEngine(document_service.registry)
    result = engine.answer(task, document)
    if result["status"] != "complete" or result["computed_value"] is None or result["trust"] is None:
        missing = ", ".join(result.get("missing", []))
        missing_text = f" Missing evidence: {missing}." if missing else ""
        return QueryResponse(
            question=question,
            raw_text=result["explanation"] + missing_text,
            raw_number=None,
            verified_number=None,
            correction_log=[],
            trust_score="LOW",
            trust_color="#f87171",
            display_value="Incomplete filing evidence",
            mode="financial_reasoning",
            verified=False,
        )

    citations = result.get("citations", [])
    citation_text = "; ".join(
        f"{citation['concept']} [{citation['source_ref']}]"
        for citation in citations[:3]
    )
    raw_number = result.get("reported_value")
    computed_value = result["computed_value"]
    explanation = result["explanation"]
    if citation_text:
        explanation = f"{explanation} Sources: {citation_text}."

    return QueryResponse(
        question=question,
        raw_text=explanation,
        raw_number=raw_number if raw_number is not None else computed_value,
        verified_number=computed_value,
        correction_log=[],
        trust_score=result["trust"].label,
        trust_color=result["trust"].color,
        display_value=format_number_display(computed_value, question),
        mode="financial_reasoning",
        verified=True,
    )
