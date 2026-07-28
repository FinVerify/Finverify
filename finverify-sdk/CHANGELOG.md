# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.9.0] — 2026-07-28

Initial public release candidate.

### Added
- `FinVerify` (sync) and `AsyncFinVerify` (async) clients with a
  matching public surface.
- `client.verify()` / `await client.verify()` against `POST /v1/verify`.
- `client.verify_batch()` — client-side concurrent fan-out (thread pool
  for sync, `asyncio.gather` + semaphore for async). Not a native
  backend batch endpoint; see `docs/roadmap.md`.
- Namespaced resources: `client.fundamentals`, `client.fcg`,
  `client.market`, `client.rag`, `client.history`, plus `client.health()`
  and `client.sample_queries()`.
- `verify_local()` and `normalize_metric_name()` — zero-network,
  zero-dependency local verification, vendored from
  `finverify-terminal/sdk/finverify/{dvl,normalizer}.py`.
- Typed exception hierarchy (`FinVerifyError` and 9 subclasses) with a
  `retryable` flag per class.
- Automatic retries with exponential backoff + full jitter for 429/5xx
  and transient network errors, honoring server `Retry-After` headers.
- Connection pooling via a single shared `httpx.Client` /
  `httpx.AsyncClient` per client instance.
- Local, pre-flight request validation (`finverify.validators`) that
  raises `ValidationError` before spending a network round trip on a
  request the API would reject anyway.
- Typed dataclass response models for every wrapped endpoint
  (`finverify.models`).
- `py.typed` marker; full type hints throughout.
- 45 passing tests (`pytest` + `respx` HTTP mocking), covering both
  clients, all response models, validators, and retry-policy logic.
- Nine runnable examples under `examples/`, one per feature area.
- `docs/architecture.md`, `docs/api-reference.md`, `docs/roadmap.md`.

### Known limitations
- Never exercised against the live `https://aadi2026-finverify-api.hf.space`
  endpoint from this environment (outbound network here is restricted
  to package registries) — all 45 tests run against a mocked transport.
  Treat this release as untested against the real API until that's
  done.
- `POST /query` (the full LLM-inference-plus-verification pipeline) is
  not wrapped. Only the DVL-only `/v1/verify` endpoint is.
- No WebSocket client for `/ws/market`, though the backend supports it.
- `client.market.*` and `client.rag.*` return raw `dict`s rather than
  typed models — their backend response shapes are open-ended (see
  `docs/architecture.md`).
- `verify_batch()`'s sync/async signatures differ (`max_workers` vs.
  `max_concurrency`) because the two implementations use different
  concurrency primitives. Documented, not considered a bug, but worth
  knowing before you write code that calls both.
