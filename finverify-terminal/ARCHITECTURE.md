# FinVerify architecture

The backend is now organized around one reusable entry point:

```python
from core import Claim, verify

result = verify(Claim(question="AAPL revenue FY2024", raw_value=123.0))
```

`backend/core` owns the domain models and pipeline stages. `backend/providers` owns
provider adapters and the registry. Existing terminal API response models remain
compatible at the edge, while the evaluator, `/verify`, `/v1/verify`, market
metrics, SEC ingestion, and transcript ingestion consume the core engine.

Pipeline order:

1. Claim compiler
2. Entity, metric, and time resolvers
3. Provider-backed evidence retrieval
4. Deterministic math validation (existing DVL implementation)
5. Trust scoring
6. Verification result builder

The SEC adapter reads the existing fundamentals cache and is intentionally thin;
the existing EDGAR fetch and normalization code remains the source-specific
implementation. New providers should implement `Provider` and register with
`ProviderRegistry` without changing the engine.
