# API Reference

Everything documented here is importable directly from `finverify`
(e.g. `from finverify import FinVerify, ValidationError`).

---

## `FinVerify`

Synchronous client.

```python
FinVerify(
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
    max_retries: int | None = None,
)
```

| Param | Default | Source of default |
|---|---|---|
| `api_key` | `None` | `FINVERIFY_API_KEY` env var |
| `base_url` | `https://aadi2026-finverify-api.hf.space` | `FINVERIFY_BASE_URL` env var |
| `timeout` | `15.0` seconds | `FINVERIFY_TIMEOUT` env var |
| `max_retries` | `2` | `FINVERIFY_MAX_RETRIES` env var |

Supports `with FinVerify() as client: ...` and a manual `client.close()`.

### Methods

- **`verify(question: str, raw_value: float, model_source: str | None = None) -> VerifyResult`**
  Calls `POST /v1/verify`. Raises `ValidationError` locally if `question`
  is empty or `raw_value` isn't numeric, before any network call.

- **`verify_batch(items: list[dict], *, max_workers: int = 8) -> BatchVerifyResult`**
  Each item needs `question` and `raw_value`, and may include
  `model_source`. Client-side concurrent fan-out over a thread pool —
  **not** a native backend batch endpoint (none exists yet; see
  `docs/roadmap.md`). Never raises for individual item failures; check
  `BatchVerifyResult.errors`.

- **`health() -> HealthStatus`** — `GET /health`.

- **`sample_queries() -> list[SampleQuery]`** — `GET /sample-queries`.

- **`fundamentals.get(ticker: str) -> FundamentalsResult`** — `GET /v1/fundamentals/{ticker}`.
- **`fundamentals.earnings(ticker: str) -> EarningsReport`** — `GET /v1/earnings/{ticker}`.
- **`fundamentals.ingest(tickers: list[str] | None = None) -> dict`** — `POST /v1/ingest/sec`.
- **`fundamentals.ingest_transcripts(tickers: list[str] | None = None) -> dict`** — `POST /v1/ingest/transcripts`.

- **`fcg.verify(values: dict, normalize: bool = True) -> FCGVerifyResult`** — `POST /v1/fcg/verify`.
- **`fcg.normalize(names: list[str]) -> NormalizeResult`** — `POST /v1/fcg/normalize`.
- **`fcg.constraints() -> list[Constraint]`** — `GET /v1/fcg/constraints`.

- **`market.quotes(symbols: list[str] | None = None) -> dict`** — `GET /market/quotes`. Raw pass-through.
- **`market.indices() -> dict`** — `GET /market/indices`. Raw pass-through.
- **`market.metric(symbol: str, metric: str = "profit_margin") -> dict`** — `GET /market/verified-metrics`. Raw pass-through.
- **`market.all_metrics(symbol: str) -> dict`** — `GET /market/all-metrics`. Raw pass-through.

- **`rag.stats() -> dict`** — `GET /v1/rag/stats`. Raw pass-through.
- **`rag.query(question: str, top_k: int = 5) -> dict`** — `POST /v1/rag/query`. Raw pass-through.
- **`rag.seed() -> dict`** — `POST /v1/rag/seed`. Raw pass-through.

- **`history.get(user_id: str, limit: int = 20, trust: str | None = None) -> list[HistoryEntry]`** — `GET /v1/history/{user_id}`.
- **`history.save(user_id, question, raw_value=None, verified_value=None, trust="HIGH", display_value="", correction_log=None) -> dict`** — `POST /v1/history`.
- **`history.delete(user_id: str) -> dict`** — `DELETE /v1/history/{user_id}`.

---

## `AsyncFinVerify`

Identical surface to `FinVerify`, with every method `async def` and
`await`ed. Supports `async with AsyncFinVerify() as client: ...` and
`await client.aclose()`.

The one signature difference: `verify_batch(items, *, max_concurrency: int = 8)`
takes `max_concurrency` (an `asyncio.Semaphore` bound) rather than
`max_workers` (a thread pool size), since the two clients use different
concurrency primitives — see `docs/architecture.md`.

---

## Local verification (no network)

- **`verify_local(question: str, raw_value: float) -> DVLResult`**
  Runs the DVL's correction rules in-process. Zero dependencies, zero
  network calls, no API key needed.

- **`normalize_metric_name(name: str) -> str | None`**
  Maps a free-text metric name to a canonical one (e.g. `"net revenues"`
  → `"revenue"`), or `None` if nothing matches closely enough.

---

## Models

All in `finverify.models`, all plain `dataclasses` with `.from_dict()`
(and `.to_dict()` where meaningful — see `docs/architecture.md` for why
dataclasses rather than Pydantic).

- **`VerifyResult`** — `question`, `raw_value`, `verified_value`,
  `trust_score` (`"HIGH"|"MEDIUM"|"LOW"`), `trust_color`, `delta_pct`,
  `correction_applied`, `dvl_version`, `timestamp`, `request_id`.
  Properties: `was_corrected`, `is_high_trust`.

- **`BatchVerifyResult`** — `results: list[VerifyResult | None]`,
  `errors: list[BaseException | None]`, same length and order as the
  input. Properties: `succeeded` (list of non-`None` results),
  `failed_count`. Supports `len()` and iteration.

- **`DVLResult`** (from `finverify.dvl`) — the result of `verify_local()`;
  see its docstring for fields (`verified_value`, `trust_score`,
  `correction_rules`, `correction_summary`, `delta_pct`, etc.).

- **`HealthStatus`** — `status`, `dvl`, `llm`, `model`. Property: `is_healthy`.

- **`FundamentalsResult`** — `ticker`, `source`, `metrics_count`, `metrics: dict`.

- **`EarningsReport`** — `ticker`, `raw: dict` (full backend payload;
  intentionally not further typed — see `docs/architecture.md`).

- **`FCGVerifyResult`** — `input_count`, `normalized_count`,
  `constraint_result: dict`, `normalization_map: dict`.

- **`NormalizeResult`** — `mapped: dict`, `unmapped: list`, `supported_metrics: list`.

- **`Constraint`** — `id`, `name`, `description`, `requires: list`,
  `tolerance_pct`, `severity`.

- **`SampleQuery`** — `question`, `actual`, `category`.

- **`HistoryEntry`** — `id`, `user_id`, `question`, `raw_value`,
  `verified_value`, `trust`, `display_value`, `correction_log`, `timestamp`.

---

## Exceptions

All in `finverify.exceptions`, all subclasses of `FinVerifyError`.

| Exception | Raised when | `retryable` |
|---|---|---|
| `ValidationError` | Local pre-flight check fails, or API returns 400/422 | No |
| `AuthenticationError` | API returns 401 | No |
| `PermissionDeniedError` | API returns 403 | No |
| `NotFoundError` | API returns 404 | No |
| `RateLimitError` | API returns 429 (has `.retry_after`) | Yes |
| `ServerError` | API returns 5xx | Yes |
| `APIError` | Any other non-2xx status | No |
| `ConnectionError` | No response received at all (DNS/refused/TLS) | — |
| `TimeoutError` | Request exceeded `timeout` | — |
| `APIConnectionError` | Response received but malformed | Yes |

`retryable` reflects what the SDK's own retry loop does automatically;
it isn't something you need to check yourself unless you're building
custom retry logic on top of the SDK.
