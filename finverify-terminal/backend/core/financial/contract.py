"""Evidence contracts for financial reasoning tasks."""

from pydantic import BaseModel, Field

from .document import FinancialDocument


class EvidenceItem(BaseModel):
    concept: str
    value: float
    unit: str
    statement: str
    source_ref: str
    xbrl_tag: str | None = None


class EvidenceContract(BaseModel):
    required: list[str]
    provided: list[EvidenceItem]
    missing: list[str]
    optional: list[EvidenceItem] = Field(default_factory=list)


class EvidenceContractBuilder:
    @staticmethod
    def build(document: FinancialDocument, required_concepts: list[str]) -> EvidenceContract:
        items_by_concept: dict[str, EvidenceItem] = {}
        optional: list[EvidenceItem] = []

        for statement in document.statements.values():
            for item in statement.items:
                evidence_item = EvidenceItem(
                    concept=item.concept,
                    value=item.value,
                    unit=item.unit,
                    statement=statement.name,
                    source_ref=item.source_ref,
                    xbrl_tag=item.xbrl_tag,
                )
                if item.concept in required_concepts and item.concept not in items_by_concept:
                    items_by_concept[item.concept] = evidence_item
                elif item.concept not in required_concepts:
                    optional.append(evidence_item)

        provided = [items_by_concept[concept] for concept in required_concepts if concept in items_by_concept]
        missing = [concept for concept in required_concepts if concept not in items_by_concept]

        return EvidenceContract(
            required=required_concepts,
            provided=provided,
            missing=missing,
            optional=optional,
        )
