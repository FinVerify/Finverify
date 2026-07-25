"""Evidence retrieval boundary. Providers are never called directly by UIs."""

from datetime import datetime, timezone
import logging

from .models import Claim, Evidence, Source

logger = logging.getLogger(__name__)


class EvidenceRetriever:
    def __init__(self, registry=None):
        self.registry = registry

    def retrieve(self, claim: Claim) -> list[Evidence]:
        if self.registry is not None:
            try:
                evidence = self.registry.retrieve(claim)
            except Exception as exc:
                logger.warning("Evidence retrieval failed for %r: %s", claim.question, exc)
                evidence = []
            if evidence:
                return evidence

        # A raw model value is still useful evidence for DVL verification, but
        # it is explicitly labeled as model input rather than primary truth.
        if claim.raw_value is not None:
            return [Evidence(
                source=Source(
                    name=claim.model_source or "model_input",
                    kind="model_output",
                    authority=0.2,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                ),
                claim=claim.question,
                value=claim.raw_value,
                period=claim.period,
            )]
        return []
