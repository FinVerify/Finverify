# Roadmap

This list was built by grepping every `@app.get/post/delete` route in
`finverify-terminal/backend/app/main.py` directly, not from memory or
assumption. Anything under "Available Today" is wrapped by this SDK
right now. Anything under "Not Yet Wrapped" exists on the backend
already but the SDK doesn't cover it — that's an SDK gap, not a backend
gap. Anything under "Future Enhancements" needs backend work first.

## Available Today (SDK wraps these)

| Endpoint | SDK method |
|---|---|
| `POST /v1/verify` | `client.verify()` |
| `GET /health` | `client.health()` |
| `GET /sample-queries` | `client.sample_queries()` |
| `GET /v1/fundamentals/{ticker}` | `client.fundamentals.get()` |
| `GET /v1/earnings/{ticker}` | `client.fundamentals.earnings()` |
| `POST /v1/ingest/sec` | `client.fundamentals.ingest()` |
| `POST /v1/ingest/transcripts` | `client.fundamentals.ingest_transcripts()` |
| `POST /v1/fcg/verify` | `client.fcg.verify()` |
| `POST /v1/fcg/normalize` | `client.fcg.normalize()` |
| `GET /v1/fcg/constraints` | `client.fcg.constraints()` |
| `GET /market/quotes` | `client.market.quotes()` |
| `GET /market/indices` | `client.market.indices()` |
| `GET /market/verified-metrics` | `client.market.metric()` |
| `GET /market/all-metrics` | `client.market.all_metrics()` |
| `GET /v1/rag/stats` | `client.rag.stats()` |
| `POST /v1/rag/query` | `client.rag.query()` |
| `POST /v1/rag/seed` | `client.rag.seed()` |
| `GET /v1/history/{user_id}` | `client.history.get()` |
| `POST /v1/history` | `client.history.save()` |
| `DELETE /v1/history/{user_id}` | `client.history.delete()` |

Both `FinVerify` (sync) and `AsyncFinVerify` (async) cover the full
list above identically.

## Not Yet Wrapped (exists on the backend, SDK gap)

These are real, working backend endpoints. Not wrapping them yet was a
scope decision for this release, not a technical blocker — flagging
them here rather than silently omitting them.

- **`POST /query`** — the full pipeline (question in, LLM inference,
  DVL verification, answer out). This is a materially different
  capability from `client.verify()`, which requires you to already
  have a `raw_value` in hand. Wrapping this would need its own request/
  response models (`QueryResponse` has `raw_text`, `mode`, `verified`
  fields `client.verify()` doesn't have) and is the single largest gap
  in this release.
- **`POST /verify`** (legacy, unversioned) — DVL-only, same shape as
  `/v1/verify` but on the older `QueryResponse` schema. Skipped
  deliberately in favor of the versioned `/v1/verify`, which is the
  one new integrations should use.
- **`GET /market/metrics`** — an explicitly-labeled backward-compat
  alias for `/market/verified-metrics` (same handler function). Not
  wrapped separately since `client.market.metric()` already covers it
  and a new SDK shouldn't encourage using a deprecated alias.
- **`WS /ws/market`** — a WebSocket endpoint pushing live quotes every
  5 seconds. This is a genuine streaming capability that already
  exists server-side. The SDK's `verify()` interface was designed with
  a streaming-shaped extension point in mind, but no WebSocket client
  has been implemented in this release — `httpx-ws` or Python's
  `websockets` would be the natural dependency to add for this.

## Future Enhancements (need backend work first)

- **A real batch-verify endpoint** (e.g. `POST /v1/verify/batch`
  accepting a list of `{question, raw_value}` and returning a list of
  results in one round trip). Today, `verify_batch()` is client-side
  concurrent fan-out over `/v1/verify` — it works, but it's N HTTP
  requests, not one. A native endpoint would cut latency and load
  meaningfully for large batches.
- **Streaming verification** — a `POST /v1/verify/stream` or
  server-sent-events variant, for cases where `raw_value` is itself
  being generated token-by-token by an LLM and the caller wants
  verification as soon as a number completes, without waiting for the
  full response.
- **API-key enforcement** — `X-FinVerify-Key` is already sent by this
  SDK on every request, but the backend does not currently validate it
  (per `main.py`, no auth dependency is attached to any route). Once
  the backend enforces this, no SDK changes should be needed —
  `AuthenticationError` (401) and `PermissionDeniedError` (403) are
  already mapped and tested.
- **Structured error bodies with a stable `error_code` field** — right
  now the SDK's exception mapping relies on HTTP status code plus a
  best-effort `detail` string (including reading FastAPI/Pydantic's
  422 validation-error shape). A stable machine-readable error code in
  every error response would let callers branch on failure reason
  without string-matching `.message`.
