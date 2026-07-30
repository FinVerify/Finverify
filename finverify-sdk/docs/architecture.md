# Architecture

## Package layout

```
finverify/
    __init__.py        # public API surface — everything importable from `finverify`
    version.py          # single source of truth for __version__
    config.py            # resolves base_url / api_key / timeout / max_retries
    auth.py               # builds request headers
    exceptions.py          # exception hierarchy
    retries.py              # pure retry-policy functions (no I/O)
    validators.py             # fail-fast request validation
    transport.py               # SyncTransport / AsyncTransport — HTTP + retries + error mapping
    models.py                    # typed response dataclasses
    dvl.py                        # vendored, zero-dependency local DVL (verify_local)
    normalizer.py                  # vendored metric-name normalizer
    utils.py                        # small shared helpers (chunking, etc.)
    client.py                        # FinVerify — sync client
    async_client.py                   # AsyncFinVerify — async client
    resources/
        verify.py                      # /v1/verify request/response spec
        meta.py                         # /health, /sample-queries
        fundamentals.py                  # /v1/fundamentals, /v1/earnings, /v1/ingest/*
        fcg.py                             # /v1/fcg/*
        market.py                           # /market/*
        rag.py                               # /v1/rag/*
        history.py                            # /v1/history/*
tests/                                          # pytest suite, mocks via respx
examples/                                        # one runnable script per feature
docs/                                              # this file, api-reference.md, roadmap.md
```

## Why a `resources/` layer

Each module in `resources/` holds two kinds of pure function, with no
I/O and no `self`:

- `build_*_request(...)` — turns typed Python arguments into
  `(method, path, json_body, params)`, running local validation first.
- `parse_*_response(...)` — turns a raw JSON dict/list into a typed
  model from `models.py`.

`client.py` and `async_client.py` both import these functions and are
otherwise nearly line-for-line mirrors of each other: the *only*
difference between the sync and async version of a call is whether the
transport call is `self._transport.request(...)` or
`await self._transport.request(...)`. This was a deliberate design
choice to satisfy the "no duplicated logic" constraint — the business
logic of "what does a `verify()` call look like on the wire" is written
exactly once, in `resources/verify.py`.

## Sync vs. async

- `SyncTransport` wraps a single pooled `httpx.Client`.
- `AsyncTransport` wraps a single pooled `httpx.AsyncClient`.
- Both expose the same `request(method, path, json_body=..., params=...)`
  signature; the async version is simply `async def` and uses
  `asyncio.sleep` instead of `time.sleep` between retries.
- `FinVerify.verify_batch()` fans requests out over a
  `concurrent.futures.ThreadPoolExecutor`; `AsyncFinVerify.verify_batch()`
  uses `asyncio.gather` with an `asyncio.Semaphore` for concurrency
  control. These are the one place sync/async genuinely need different
  primitives, since Python doesn't have a single concurrency primitive
  that's idiomatic in both worlds.

## Transport layer

`SyncTransport.request()` / `AsyncTransport.request()` do, in order:

1. Build headers via `auth.build_headers()`.
2. Attempt the HTTP call.
3. On a network-level failure (`httpx.TimeoutException`,
   `httpx.ConnectError`, other `httpx.HTTPError`), wrap it into a
   FinVerify exception (`TimeoutError`, `ConnectionError`,
   `APIConnectionError`) and either retry or raise.
4. On an HTTP response with `status_code >= 400`, decide via
   `retries.is_retryable_status()` whether to retry (429 and 5xx are
   retryable; 4xx other than 429 is not) or immediately raise the
   mapped exception from `exceptions.py`.
5. On success (`status_code < 400`), parse and return the JSON body
   (or raw text if the body isn't JSON).

Retries use `retries.compute_backoff()`: exponential backoff with full
jitter, capped at `backoff_max` (default 8s), and short-circuited to
honor a server-sent `Retry-After` header on 429s.

## Validators

`validators.py` runs *before* any network call. Its job is to turn a
guaranteed-to-fail request (empty question, non-numeric value, empty
metrics dict) into an immediate local `ValidationError`, rather than
spending a round trip to get the same rejection back as an HTTP 422.
This mirrors — but does not replace — the backend's own Pydantic
validation; the backend remains the source of truth for what's
actually valid.

## Model layer

Response models are plain `dataclasses`, not Pydantic, even though the
FastAPI backend uses Pydantic internally. This was a deliberate choice
to match the convention already established in this repository's
embedded SDK (`finverify-terminal/sdk-legacy/finverify/client.py`, `dvl.py`),
and to keep this package's only hard dependency `httpx`. Every model
class exposes `.from_dict()` and (where relevant) `.to_dict()`, so
nothing that comes back from a typed method is a raw `dict` — the
exceptions are `client.market.*`, `client.rag.*`, and the raw
ingestion-trigger calls, which intentionally return the backend's raw
JSON because their shape is open-ended (see `resources/market.py` and
`resources/rag.py` docstrings for the reasoning).
