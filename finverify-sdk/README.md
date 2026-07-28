# FinVerify Python SDK

**Deterministic verification for financial LLM outputs.** FinVerify
catches the class of hallucination where a model gets the right *number*
but the wrong *scale or sign* — 0.2531 instead of 25.31%, or a growth
rate reported as negative when the underlying numbers say positive —
and corrects it deterministically, without another LLM call.

This SDK wraps the [FinVerify DVL API](https://github.com/aadityat23/finverify-llm)
with a typed, retrying client — sync and async, both with the same
public surface.

```python
from finverify import FinVerify

client = FinVerify()
result = client.verify(question="What was Apple's FY2024 revenue?", raw_value=391.0)

print(result.verified_value)   # 391.0
print(result.trust_score)      # 'HIGH'
```

> **Status: v0.9.0, release candidate.** All 45 tests pass against a
> mocked HTTP transport. This SDK has not yet been exercised against the
> live API from this environment — see [Known Limitations](#known-limitations)
> before depending on it in production. See [`CHANGELOG.md`](CHANGELOG.md).

---

## Installation

```bash
pip install finverify-sdk
```

Requires Python 3.9+. The only hard dependency is [`httpx`](https://www.python-httpx.org/).

For local development:

```bash
git clone https://github.com/aadityat23/finverify-llm.git
cd finverify-llm/finverify-sdk   # wherever you place this package
pip install -e ".[dev]"
pytest
```

---

## Features

- **Sync and async clients** with an identical public surface —
  `FinVerify` and `AsyncFinVerify`.
- **Typed everything** — dataclass response models, full type hints,
  a `py.typed` marker for downstream type checkers.
- **Automatic retries** — exponential backoff with jitter on 429/5xx
  and transient network errors, honoring `Retry-After`.
- **A real exception hierarchy** — catch `FinVerifyError` broadly, or
  `RateLimitError` / `ValidationError` / etc. specifically.
- **Connection pooling** — one shared `httpx.Client`/`AsyncClient` per
  SDK client instance.
- **Local verification with zero network calls** — `verify_local()`
  runs the same DVL correction rules in-process.
- **Covers every real endpoint** on the backend as of this release:
  verification, fundamentals, earnings, the Financial Constraint Graph,
  market data, RAG search, and query history. See
  [`docs/roadmap.md`](docs/roadmap.md) for exactly what's covered vs. not.

---

## Quick Start

```python
from finverify import FinVerify

with FinVerify() as client:
    result = client.verify(
        question="What was the profit margin?",
        raw_value=0.2531,
    )
    print(result.verified_value)       # 25.31
    print(result.trust_score)          # 'MEDIUM'
    print(result.was_corrected)        # True
    print(result.correction_applied)   # 'scale_mul100'
```

---

## Sync Client

```python
from finverify import FinVerify

# Configuration falls back to env vars if not passed explicitly:
#   FINVERIFY_API_KEY, FINVERIFY_BASE_URL, FINVERIFY_TIMEOUT, FINVERIFY_MAX_RETRIES
client = FinVerify(
    api_key=None,        # optional; sent as X-FinVerify-Key
    base_url=None,       # defaults to the public FinVerify API
    timeout=15.0,        # seconds
    max_retries=2,       # for 429/5xx and transient network errors
)

result = client.verify(question="What was the P/E ratio?", raw_value=28.5)
client.close()
```

Or use it as a context manager so the connection pool is always closed:

```python
with FinVerify() as client:
    result = client.verify(question="...", raw_value=1.0)
```

---

## Async Client

```python
import asyncio
from finverify import AsyncFinVerify

async def main():
    async with AsyncFinVerify() as client:
        result = await client.verify(question="What was the P/E ratio?", raw_value=28.5)
        print(result.trust_score)

asyncio.run(main())
```

`AsyncFinVerify` has the same methods as `FinVerify`, all `async def`.
Both share one retry/error-mapping implementation — see
[`docs/architecture.md`](docs/architecture.md).

---

## Batch Verification

There is no native batch endpoint on the backend yet (see
[`docs/roadmap.md`](docs/roadmap.md)), so `verify_batch()` fans requests
out concurrently rather than sending one HTTP call:

```python
with FinVerify() as client:
    batch = client.verify_batch([
        {"question": "What was the profit margin?", "raw_value": 0.2531},
        {"question": "What was the P/E ratio?", "raw_value": 28.5},
    ], max_workers=8)

print(f"{len(batch.succeeded)}/{len(batch)} succeeded")
for result, error in zip(batch.results, batch.errors):
    if result is not None:
        print(result.verified_value, result.trust_score)
    else:
        print("failed:", error)
```

Async version takes `max_concurrency` (an `asyncio.Semaphore` bound)
instead of `max_workers` (a thread-pool size):

```python
async with AsyncFinVerify() as client:
    batch = await client.verify_batch(items, max_concurrency=8)
```

`verify_batch()` never raises for an individual item's failure — check
`batch.errors`, which is `None`-padded to the same length and order as
your input.

---

## Local Verification

Run the DVL's correction rules with no network call, no API key, and
no rate limit — useful for tests, offline batch jobs, or a fallback
when the API is unreachable:

```python
from finverify import verify_local

result = verify_local("What was the profit margin?", 0.2531)
print(result.verified_value)  # 25.31
```

---

## Health Checks

```python
with FinVerify() as client:
    status = client.health()
    print(status.status, status.dvl, status.llm, status.is_healthy)
```

---

## Fundamentals

SEC EDGAR-sourced fundamentals and earnings-call verification:

```python
with FinVerify() as client:
    fundamentals = client.fundamentals.get("AAPL")
    print(fundamentals.metrics)

    earnings = client.fundamentals.earnings("AAPL")
    print(earnings.raw)

    # Trigger backend ingestion for specific tickers (or all, if omitted)
    client.fundamentals.ingest(["AAPL", "MSFT"])
    client.fundamentals.ingest_transcripts(["AAPL"])
```

---

## FCG (Financial Constraint Graph)

Checks a *set* of related numbers against each other — e.g. that
`gross_margin ≈ (revenue - cogs) / revenue` — rather than verifying one
number in isolation:

```python
with FinVerify() as client:
    constraints = client.fcg.constraints()
    for c in constraints:
        print(c.id, c.description, c.severity)

    normalized = client.fcg.normalize(["net revenues", "cost of goods sold"])
    print(normalized.mapped)

    result = client.fcg.verify({"revenue": 391.0, "cogs": 210.0, "gross_margin": 46.3})
    print(result.constraint_result)
```

---

## Market

Live quotes, indices, and DVL-verified metrics. These return the
backend's raw `dict` rather than a typed model — the response shape is
open-ended, see [`docs/architecture.md`](docs/architecture.md):

```python
with FinVerify() as client:
    quotes = client.market.quotes(["AAPL", "MSFT"])
    indices = client.market.indices()
    metric = client.market.metric("AAPL", "profit_margin")
    all_metrics = client.market.all_metrics("AAPL")
```

---

## RAG

Vector search over ingested filings/transcripts (also raw `dict`
pass-through):

```python
with FinVerify() as client:
    stats = client.rag.stats()
    results = client.rag.query("What did management say about margins?", top_k=3)
```

---

## History

Supabase-backed per-user query history:

```python
with FinVerify() as client:
    client.history.save(
        user_id="user_123",
        question="What was the profit margin?",
        raw_value=0.2531,
        verified_value=25.31,
        trust="MEDIUM",
        display_value="25.31%",
        correction_log=["scale_mul100"],
    )

    entries = client.history.get("user_123", limit=10)
    for e in entries:
        print(e.question, e.verified_value, e.trust)

    client.history.delete("user_123")
```

---

## Error Handling

Every error is a `FinVerifyError`; catch specific subclasses when you
need to branch:

```python
from finverify import (
    FinVerify, FinVerifyError, ValidationError,
    RateLimitError, ServerError, AuthenticationError,
)

with FinVerify() as client:
    try:
        result = client.verify(question="What was the margin?", raw_value=0.25)
    except ValidationError as e:
        print("Bad input:", e)          # empty question, non-numeric value, or API 400/422
    except RateLimitError as e:
        print("Rate limited, retry after:", e.retry_after)
    except AuthenticationError as e:
        print("Bad or missing API key:", e)
    except ServerError as e:
        print("FinVerify had a problem:", e)
    except FinVerifyError as e:
        print("Something else went wrong:", e)
```

See [`docs/api-reference.md`](docs/api-reference.md#exceptions) for the
full hierarchy and which exceptions the SDK retries automatically.

---

## Configuration

| Constructor arg | Env var | Default |
|---|---|---|
| `api_key` | `FINVERIFY_API_KEY` | `None` |
| `base_url` | `FINVERIFY_BASE_URL` | `https://aadi2026-finverify-api.hf.space` |
| `timeout` | `FINVERIFY_TIMEOUT` | `15.0` |
| `max_retries` | `FINVERIFY_MAX_RETRIES` | `2` |

Explicit constructor args always win over env vars, which always win
over defaults.

---

## Retry Behavior

429 and 5xx responses, plus transient connection/timeout errors, are
retried automatically with exponential backoff and full jitter
(capped at 8 seconds between attempts), honoring a server-sent
`Retry-After` header on 429s. 4xx errors other than 429 are never
retried — they mean the request itself needs to change. See
[`docs/architecture.md`](docs/architecture.md#transport-layer) for the
exact algorithm.

---

## Type Hints

The package ships a `py.typed` marker and full type hints throughout,
so `mypy`/`pyright` and editor autocomplete work out of the box:

```python
from finverify import FinVerify, VerifyResult

def check(client: FinVerify, q: str, v: float) -> VerifyResult:
    return client.verify(question=q, raw_value=v)
```

---

## Examples

Runnable end-to-end scripts for every feature live in [`examples/`](examples/):

| Script | Demonstrates |
|---|---|
| `verify.py` | Basic sync verification |
| `async_verify.py` | Basic async verification |
| `batch_verify.py` | Concurrent batch verification |
| `verify_local.py` | Zero-network local verification |
| `health.py` | Health check |
| `fundamentals.py` | SEC EDGAR fundamentals + earnings |
| `fcg.py` | Financial Constraint Graph |
| `market.py` | Live quotes, indices, verified metrics |
| `rag.py` | Vector search over filings |
| `history.py` | Save / list / delete query history |

```bash
python examples/verify.py
```

---

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — package layout, why
  it's structured this way, sync vs. async, transport/retry design.
- [`docs/api-reference.md`](docs/api-reference.md) — every public class
  and method.
- [`docs/roadmap.md`](docs/roadmap.md) — what's wrapped today vs. what
  needs backend work, checked directly against `main.py`.

---

## Known Limitations

- **Not yet tested against the live API.** This development
  environment's outbound network doesn't reach
  `aadi2026-finverify-api.hf.space`; all 45 tests run against a mocked
  transport (`respx`). Run the examples against the real API before
  depending on this in production.
- `POST /query` (question in, LLM-generated answer + verification out)
  is not wrapped — only the DVL-only `/v1/verify` path is. See
  `docs/roadmap.md`.
- No WebSocket client for the backend's `/ws/market` live-quote stream.
- `client.market.*` and `client.rag.*` return raw `dict`s, not typed
  models (open-ended response shapes — see `docs/architecture.md`).

---

## Contributing

This SDK lives alongside the main
[finverify-llm](https://github.com/aadityat23/finverify-llm) repository.
Before opening a PR:

```bash
pip install -e ".[dev]"
pytest                 # all tests should pass
pyflakes finverify/    # no unused imports / obvious errors
```

Please don't add a new hard dependency without discussing it first —
`httpx` was chosen deliberately to keep the install light.

---

## License

MIT — see [`LICENSE`](LICENSE).
