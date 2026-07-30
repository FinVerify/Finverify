# FinVerify Implementation Report

## 1. Executive Summary

FinVerify has been evolved from a terminal-focused prototype into a more reusable verification platform while preserving the existing backend behavior and terminal UI.

The central architectural change is the introduction of a reusable `verify(claim)` engine. The engine is now the single production verification path for the terminal evaluator, `/verify`, `/v1/verify`, market-derived metrics, SEC ingestion, transcript claim verification, and model evaluation. The existing Deterministic Verification Layer (DVL) remains the tested mathematical implementation, but it is now invoked through the core math stage rather than independently by each consumer.

The backend now includes shared domain contracts, a staged verification pipeline, an evidence boundary, a provider interface, a provider registry, and an SEC provider adapter. Existing response models and endpoint behavior remain compatible at the API boundary.

The frontend retains its terminal layout, navigation, typography, colors, panel positions, and compact institutional styling. It was polished with a hero financial-network visualization, terminal event logging, pipeline-stage feedback, expanded engine diagnostics, ticker refinements, restrained ambient motion, and result animations.

The implementation deliberately excludes future platform work such as consensus, persistent caching infrastructure, SDKs, CLI packaging, authentication, additional providers, Kubernetes, and enterprise features.

## 2. Architecture Overview

### Core engine

The reusable engine is located under `finverify-terminal/backend/core/` and exposed through:

```python
from core import Claim, verify

result = verify(Claim(question="What was revenue growth?", raw_value=0.152))
```

`verify()` accepts a shared `Claim` model or a dictionary, runs the complete pipeline, and returns a `VerificationResult`. Consumers should use this entry point rather than calling DVL functions directly.

### Verification pipeline

The engine performs these stages in order:

1. Compile the input into a normalized `Claim`.
2. Resolve entity, metric, and period information.
3. Retrieve evidence through an `EvidenceRetriever` and `ProviderRegistry`.
4. Run deterministic mathematical verification through the existing DVL implementation.
5. Convert DVL trust labels into the shared `TrustScore` contract.
6. Format correction records, calculations, evidence, and trust into a `VerificationResult`.

The pipeline is intentionally synchronous and lightweight. It does not introduce workflow orchestration, background workers, distributed queues, or new storage systems.

### Domain models

`backend/core/models.py` defines the shared contracts:

- `Claim`: question, raw value/text, optional actual value, entity, metric, period, model source, and metadata.
- `Entity`: company or other financial entity identity, including ticker, CIK, and LEI fields.
- `Metric`: human-readable and canonical metric names plus an optional unit.
- `Evidence`: a claim-linked value with source, period, excerpt, and locator metadata.
- `Source`: source name, kind, authority score, URL, and retrieval timestamp.
- `Calculation`: calculation name, expression, inputs, output, and pass/fail status.
- `TrustScore`: label, normalized score, color, and explanatory reasons.
- `VerificationResult`: claim, verified value, corrections, evidence, calculations, trust, mode, and verification status.

The legacy API models in `backend/app/models.py` re-export these domain contracts while retaining the existing request and response schemas.

### Provider architecture

`backend/providers/base.py` defines the provider protocol:

- `name`
- `can_handle(claim)`
- `retrieve(claim)`

`ProviderRegistry` stores providers, allows registration, selects the first compatible provider, and logs provider failures without taking down verification. The default registry is created by `providers/registry.py` and currently registers exactly one provider: `SECProvider`.

`SECProvider` reads existing SEC fundamentals from the SQLite-backed ingestion store and converts them into shared `Evidence` objects. It is intentionally thin; SEC fetching, XBRL extraction, fallback filing data, and persistence remain in the existing ingestion implementation.

### Ingestion

SEC ingestion remains on-demand and uses the existing EDGAR Company Facts path with fallback filing data. Each extracted metric is passed through `core.verify()` before being persisted with raw value, verified value, filing metadata, source URL, trust, color, and correction rule.

Transcript ingestion extracts numeric claims from transcript text and sends each claim through the same core engine before classifying, flagging, and optionally storing it.

### Evaluator

`backend/app/evaluator.py` converts an already-parsed LLM output into a `Claim`, calls `verify()`, and maps the resulting shared result back into the existing `QueryResponse` shape. Missing extracted numbers remain a valid response state rather than causing a crash.

### API flow

The primary request lifecycle is:

```text
Client request
    -> API request model
    -> LLM inference or supplied raw value
    -> Claim construction
    -> core.verify()
    -> evidence registry
    -> deterministic DVL math
    -> trust and output construction
    -> backward-compatible API response
```

For a raw-number request, the request bypasses LLM inference and enters the same engine with `Claim.raw_value`. For a model query, the LLM output is cleaned and parsed before entering the engine. For SEC and transcript ingestion, extracted values enter the same path directly.

## 3. Repository Structure

### `finverify-terminal/backend/`

The Python FastAPI backend and its domain, ingestion, evaluation, storage, and test code.

- `app/`: API application, legacy-compatible API models, parser, query classifier, market service, evaluator, and DVL implementation.
- `core/`: reusable verification engine and shared contracts.
- `providers/`: provider protocol, registry, and SEC adapter.
- `ingestion/`: SEC EDGAR ingestion, transcript parsing, SQLite persistence, and verification-before-storage logic.
- `fcg/`: Financial Constraint Graph normalization and multi-number consistency checks.
- `rag/`: existing vector/keyword retrieval and seed utilities.
- `evals/`: cross-model evaluation workflow.
- `tests/`: unit and integration tests for DVL, APIs, ingestion, RAG, FCG, normalization, and transcript flows.
- `data/`: SQLite fundamentals database.

### `finverify-terminal/frontend/`

The Next.js terminal frontend.

- `app/`: route pages, layout, global CSS, loading/error states, and Open Graph image route.
- `components/`: terminal panels, market displays, query UI, verification visualization, dashboard elements, and report generation.
- `lib/`: typed API client, market client, connection health state, local history, and client-side DVL fallback.
- `public/`: browser widget asset.

### `finverify-terminal/backend/core/`

The shared verification package. It contains the compiler, resolvers, evidence boundary, math adapter, trust adapter, output builder, engine, and domain models.

### `finverify-terminal/backend/providers/`

The provider abstraction and current SEC provider registration. The registry is the extension point for future providers, but only SEC is currently implemented.

### `finverify-terminal/backend/ingestion/`

Source-specific retrieval and persistence. SEC ingestion uses Company Facts and fallback filing records; transcript ingestion parses claims and stores verification outcomes.

### `finverify-terminal/backend/evals/`

Cross-model evaluation code. The evaluator now calls `core.verify()` for DVL accuracy measurement.

### `finverify-terminal/backend/tests/`

Regression and behavior tests covering the existing DVL, API, FCG, RAG, SEC, transcript, parser, and normalization functionality. The SEC ingestion test now mocks the shared engine rather than the removed legacy call path.

### `finverify-terminal/smoke-tests/`

A CI regression smoke-check, distinct from the FinVerifyBench research dataset in `finverify-bench/`. `smoke.json` contains 2 representative cases run directly against the core engine to catch regressions; it is not a benchmark in the research/evaluation sense.

### Root documentation

`ARCHITECTURE.md` documents the current core/provider boundaries and pipeline order. This report provides the broader implementation and product audit.

## 4. Verification Pipeline

### Claim compilation

`core/compiler.py` converts a `Claim` or dictionary into a deep-copied, validated shared `Claim`. This prevents consumers from maintaining incompatible input shapes.

### Entity resolution

`core/resolvers.py` performs lightweight deterministic entity detection. It preserves explicitly supplied entity data and can detect uppercase ticker-like tokens from a question.

This is intentionally a small resolver, not a complete global entity-resolution graph.

### Metric resolution

The metric resolver detects common financial terms such as revenue, income, margin, ratio, growth, shares, EPS, assets, liabilities, cash flow, yield, return, and securities. It creates a canonical metric name when one is detected.

### Time resolution

The time resolver detects simple year and quarter patterns such as `2024` and `Q4 2022`. Explicit period values are preserved.

### Evidence retrieval

`core/evidence.py` is the only evidence boundary used by the engine. It delegates provider selection to the registry. If a provider returns no evidence, a raw model value is represented as `model_input` evidence with low authority. If no raw value exists and no provider returns evidence, the result contains an empty evidence list and remains safe to consume.

Provider and registry errors are logged and treated as missing evidence rather than crashing the entire verification flow.

### Math verification

`core/math_engine.py` is the sole production adapter around `app.dvl.full_verify()`. Existing DVL behavior is preserved:

- ratio scale correction
- sign correction when supported by ground truth
- magnitude correction when supported by ground truth
- ambiguous scale handling
- correction audit records

The DVL itself remains available for focused low-level unit tests, but application entry points no longer call it directly.

### Trust scoring

`core/trust.py` maps existing DVL labels to a normalized score contract:

- `HIGH`: `0.9`
- `MEDIUM`: `0.6`
- `LOW`: `0.25`

The result retains the existing label and color used by the frontend. Reasons indicate whether corrections were applied and whether evidence was authoritative or model-provided.

This is a deterministic adapter, not the Bayesian provenance model described in the long-term product vision.

### Output building

`core/output.py` formats correction records, creates the deterministic calculation record, attaches evidence, and returns `VerificationResult`. Formatting is centralized here so API consumers do not duplicate correction-log formatting.

## 5. Frontend Architecture

### Pages

- `/`: primary terminal workspace with hero, capabilities, query input, result stack, correction log, verified output, failure-case explanation, and session/errors/stats panel.
- `/dashboard`: local query history, trust filtering, statistics, expandable audit details, re-run action, and history clearing.
- `/market`: market-focused view with live/fallback quotes, indices, market context, watchlist, and verified derived metrics.
- `/metrics`: research and benchmark presentation page with headline results, ablations, error taxonomy, robustness tables, and DVL explanations.
- `/og`: server-generated Open Graph image route.
- `error.tsx` and `loading.tsx`: route-level error and loading states.

### Major components

- `HeroNetwork`: compact SVG financial-hub network occupying only the unused right side of the hero.
- `TickerBar`: fixed-height scrolling market ticker with live/static source status.
- `QueryInput`: terminal textarea, execute action, fixed-input demo selection, engine diagnostics, and demo controls.
- `TerminalPanel`: raw model output, extraction state, execution state, token/latency/model metadata, and raw-number count-up.
- `QueryInterpretation`: query type, detected keywords, and armed DVL rules.
- `VerificationLog`: correction records and animated pipeline stage status.
- `TrustScore`: verified output, trust badge, correction summary, trust tooltip, and calculation visualization.
- `DVLReport`: PDF audit report generation.
- `MarketContext`, `Watchlist`, `MetricPanel`, and `MetricsChart`: market and derived-financial displays.
- `EarningsVerification`: earnings-claim verification presentation.
- `ErrorTaxonomy` and `AblationSection`: research and failure-analysis presentation.
- `NavModeToggle` and `NavHealthIndicator`: navigation mode and backend status indicators.

### Dashboard, market, metrics, and history

The dashboard reads local history, filters by trust, expands correction details, and re-runs historical raw values through `/verify`. The market route uses the typed API client for quotes, indices, and derived metrics, with fallback data where configured. The metrics route is primarily a research and benchmark presentation surface. History is stored locally for anonymous use and has optional backend persistence methods for user-scoped history.

## 6. UI Improvements

### Financial hub network

The hero now includes a dark monochrome inline SVG map-like visualization with New York, London, Frankfurt, Dubai, Mumbai, Singapore, Hong Kong, Tokyo, and Sydney. Hubs pulse softly, routes use dashed animated paths, packets travel along routes, and each hub displays a compact OPEN/CLOSED state.

The visualization is absolutely positioned and does not enlarge or rearrange the hero panel.

### Ticker improvements

- Slower, smoother marquee motion.
- Edge fade masks to reduce hard clipping.
- Blinking divider separators.
- Existing LIVE/STATIC source indicator retained.
- Existing fixed ticker height and visual treatment retained.

### Session log

The existing Session tab now shows timestamped terminal events such as query receipt, entity resolution, SEC evidence routing, math verification, trust computation, and completion. New events animate into the current panel without changing the tab structure.

### Pipeline animation

The existing verification log now displays:

```text
COMPILE -> RESOLVE -> RETRIEVE -> MATH -> TRUST -> VERIFIED
```

Completed stages use the existing green palette, the active stage uses amber, and pending stages remain muted. The animation is driven by the actual frontend execution flow rather than a separate spinner component.

### Diagnostics

The existing engine-status panel now includes:

- engine online status
- rule count
- tolerance
- provider status
- engine version
- latency state
- session uptime

The panel remains in the query-input column.

### Ambient effects

Subtle terminal grid lines, a moving scanline, panel-safe route animation, LED pulses, edge fades, and restrained glow effects add activity without changing the terminal palette or density.

### Result polish

- Raw values count upward.
- Verified values count upward.
- Verified values briefly glow.
- Trust badges pulse subtly.
- Correction entries appear line by line.
- Pipeline stages remain visible after completion until the next execution.

### Accessibility and reduced motion

The hero network includes an accessible label while remaining decorative to screen readers. A global `prefers-reduced-motion` rule disables extended animations and reduces motion for users who request it. Existing buttons, links, and tabs remain keyboard-operable.

## 7. API Endpoints

The backend exposes 23 HTTP endpoints and one WebSocket route.

### Core verification

#### `POST /query`

Input: `{ "question": string, "context"?: string }`.

Purpose: optional LLM inference followed by parsing and shared verification. Advisory queries are returned as unverified; numerical outputs are parsed and sent through `core.verify()`.

Output: backward-compatible `QueryResponse` containing question, raw text/value, verified value, correction log, trust score/color, display value, mode, and verification status.

#### `POST /verify`

Input: `{ "question": string, "raw_number": number }`.

Purpose: verify an already extracted number without an LLM call.

Output: `QueryResponse`.

#### `POST /v1/verify`

Input: `{ "question": string, "raw_value": number, "model_source"?: string }`.

Purpose: standalone public verification response with delta percentage, correction summary, trust, DVL version, and timestamp.

Output: `V1VerifyResponse`.

#### `GET /health`

Output: backend status, DVL status, LLM status, and model information.

#### `GET /sample-queries`

Output: hardcoded paper/demo questions with optional actual values and categories.

### Market

- `GET /market/quotes?symbols=AAPL,TSLA`: quote data for comma-separated symbols.
- `GET /market/indices`: S&P 500, NASDAQ, and VIX-style index data.
- `GET /market/verified-metrics?symbol=AAPL&metric=profit_margin`: one derived metric through the shared engine.
- `GET /market/metrics`: backward-compatible alias for verified metrics.
- `GET /market/all-metrics?symbol=AAPL`: all supported derived metrics for a symbol.
- `WS /ws/market`: pushes market quotes approximately every five seconds.

### SEC and earnings

- `GET /v1/fundamentals/{ticker}`: returns cached or freshly ingested SEC fundamentals with raw/verified values and provenance metadata.
- `GET /v1/earnings/{ticker}`: returns transcript claim verification and flagged-claim analysis.
- `POST /v1/ingest/sec?tickers=AAPL,MSFT`: triggers selected or all SEC ingestion jobs.
- `POST /v1/ingest/transcripts?tickers=AAPL,MSFT`: triggers selected or all transcript verification jobs.

### RAG

- `GET /v1/rag/stats`: returns RAG index statistics or an unavailable response.
- `POST /v1/rag/query`: input `{ "question": string, "top_k"?: number }`; returns retrieved context results.
- `POST /v1/rag/seed`: seeds the RAG index from SQLite data.

### History

- `GET /v1/history/{user_id}?limit=20&trust=HIGH`: returns user-scoped persistent history.
- `POST /v1/history`: accepts user ID, question, raw/verified values, trust, display value, and correction log.
- `DELETE /v1/history/{user_id}`: clears a user’s persistent history.

### Financial Constraint Graph

- `POST /v1/fcg/verify`: input `{ "values": {...}, "normalize": true }`; normalizes names and checks financial constraints.
- `POST /v1/fcg/normalize`: input `{ "names": [...] }`; returns mapped and unmapped canonical metric names.
- `GET /v1/fcg/constraints`: lists hard and soft constraints with required fields, tolerances, and severity.

## 8. Current Capabilities

FinVerify can currently:

- Parse numerical claims from LLM outputs.
- Detect numerical, advisory, and general query modes.
- Correct supported ratio-scale, sign, and magnitude errors deterministically.
- Return correction logs and trust labels.
- Represent claims, entities, metrics, sources, evidence, calculations, and results consistently.
- Route evidence retrieval through a provider registry.
- Read and ingest SEC Company Facts data.
- Use real filing metadata with fallback filing data for supported tickers.
- Verify transcript numeric claims and flag suspicious claims.
- Verify market-derived metrics.
- Run Financial Constraint Graph checks for multi-number relationships.
- Search the existing RAG index.
- Persist local anonymous history and optionally use backend history persistence.
- Run a smoke benchmark directly against the core engine.
- Present verification results in a terminal-style frontend with audit-oriented UI feedback.
- Export verification history as a PDF audit report.
- Stream market quote updates over WebSocket.

## 9. Known Limitations

- SEC is the only registered provider. FRED, DBNomics, Yahoo, Stooq, and other sources are not implemented as provider adapters.
- The SEC provider currently reads the existing fundamentals store; it does not itself perform a new filing fetch. Fresh ingestion remains an explicit ingestion/API operation.
- Evidence matching is basic. Retrieved SEC evidence is selected by ticker/cache availability rather than a full claim-to-line-item semantic matcher.
- Trust scores are deterministic label mappings, not Bayesian provenance scores or cross-source consensus scores.
- No consensus engine is implemented.
- No persistent Redis, PostgreSQL, DuckDB, Qdrant, or object-store architecture is introduced by this implementation. Existing SQLite and RAG behavior remain in place.
- Entity, metric, and time resolution use lightweight deterministic heuristics.
- The LLM path depends on an OpenAI-compatible inference endpoint configured through environment variables.
- The frontend has a client-side DVL fallback for known demo cases and does not represent a complete offline general-purpose verification engine.
- Custom typed queries require a functioning backend/LLM path; known demo values can run through fixed-input verification.
- The hero network is a compact illustrative visualization, not live global market topology or real-time exchange status telemetry.
- Anonymous history is local browser storage. User-scoped persistence depends on the configured Supabase integration.
- The current benchmark is a smoke benchmark, not the complete FinVerify Bench described in the product vision.
- Existing frontend lint warnings remain in `DVLReport.tsx` and `EarningsVerification.tsx`.
- In some development environments, backend test execution may be blocked by missing optional Python dependencies even when the source compiles successfully.

## 10. Future Roadmap

The following items are intentionally not implemented in this overhaul:

1. Add FRED, DBNomics, Yahoo/Stooq, and other open providers through the existing registry.
2. Add source-aware consensus and discrepancy reporting.
3. Improve entity resolution across CIK, ticker, LEI, FIGI, and ISIN identifiers.
4. Add semantic claim-to-evidence matching and filing line-item locators.
5. Add persistent caching and point-in-time data versioning.
6. Expand the benchmark into FinVerify Bench with datasets, CI regression runs, and leaderboard output.
7. Publish a Python SDK and TypeScript SDK around the shared result contract.
8. Add an installable CLI that calls the same `verify()` engine.
9. Add the Chrome extension verifier.
10. Add research-workspace document highlighting and bounding-box evidence.
11. Add MCP integration under the API boundary.
12. Improve trust scoring with source authority, math determinism, consensus, and lineage weighting.
13. Add production-grade dependency locking and CI environment validation.

## 11. File Change Summary

### Core engine and domain

- `backend/core/__init__.py`: public `Claim`, `VerificationResult`, and `verify` exports.
- `backend/core/models.py`: shared domain models.
- `backend/core/compiler.py`: claim normalization.
- `backend/core/resolvers.py`: entity, metric, and period resolution.
- `backend/core/evidence.py`: provider-backed evidence boundary and graceful fallback.
- `backend/core/math_engine.py`: sole production adapter around the existing DVL.
- `backend/core/trust.py`: deterministic trust contract adapter.
- `backend/core/output.py`: centralized result and correction-log construction.
- `backend/core/engine.py`: single `verify()` orchestration entry point.

### Providers

- `backend/providers/base.py`: provider protocol and registry implementation.
- `backend/providers/registry.py`: default registry with SEC registration.
- `backend/providers/sec.py`: SEC evidence adapter.
- `backend/providers/__init__.py`: provider exports.

### Backend integration

- `backend/app/evaluator.py`: migrated response construction to `core.verify()`.
- `backend/app/main.py`: migrated `/v1/verify` and cleaned duplicate imports.
- `backend/app/market.py`: migrated derived metric verification.
- `backend/app/models.py`: re-exported shared domain contracts while retaining API models.
- `backend/ingestion/sec_edgar.py`: verification-before-storage now uses the core engine.
- `backend/ingestion/transcripts.py`: transcript claims now use the core engine.
- `backend/evals/cross_model_eval.py`: evaluation path now measures the shared engine.
- `backend/tests/test_sec_edgar.py`: test hook updated to mock the shared engine.

### Frontend overhaul

- `frontend/app/page.tsx`: selected-demo execution fix, hero network insertion, session event log, pipeline stage state, and execution logging.
- `frontend/app/layout.tsx`: terminal ambience class applied to the existing shell.
- `frontend/app/globals.css`: network, ticker, scanline, grid, pulse, result glow, and reduced-motion styles.
- `frontend/components/HeroNetwork.tsx`: compact SVG financial network.
- `frontend/components/QueryInput.tsx`: expanded engine diagnostics and uptime.
- `frontend/components/TickerBar.tsx`: viewport fade and animated separators.
- `frontend/components/TerminalPanel.tsx`: terminal execution status and zero-safe raw counter.
- `frontend/components/VerificationLog.tsx`: pipeline stage visualization and staggered event presentation.
- `frontend/components/TrustScore.tsx`: verified number glow and trust badge animation.

### Benchmark and documentation

- `ARCHITECTURE.md`: current architecture boundary documentation.
- `smoke-tests/smoke.json`: smoke benchmark cases.
- `smoke-tests/runner.py`: direct core-engine smoke-test runner.
- `IMPLEMENTATION_REPORT.md`: this implementation audit.

## 12. Statistics

Approximate implementation statistics:

- New core modules: 9 Python modules, including the package initializer.
- Provider modules: 4 Python modules, including the package initializer.
- Core pipeline stages: 8 named stages when counting compiler, entity resolver, metric resolver, time resolver, evidence retrieval, math, trust, and output building.
- Provider adapters: 1 implemented adapter, SEC EDGAR.
- Frontend component modules: approximately 17 major `.tsx` components.
- Frontend pages/routes: 6 primary route surfaces including the terminal, dashboard, market, metrics, error/loading states, and Open Graph route.
- HTTP endpoints: 23.
- WebSocket routes: 1.
- Benchmark cases currently included: 2 smoke cases.
- Existing DVL correction families: scale, sign, and magnitude.

These figures describe the current repository and are intended as orientation rather than a generated build manifest.

## 13. Developer Notes

- New consumers should construct a `Claim` and call `core.verify()` rather than importing `app.dvl.full_verify()`.
- If a new source is needed, implement the `Provider` protocol, return shared `Evidence` objects, and register the provider without adding provider logic to UI or API route handlers.
- Keep API response compatibility at the edge. Convert `VerificationResult` into legacy response models only in the evaluator or route boundary.
- Preserve the distinction between model input evidence and primary-source evidence. A raw model number is not equivalent to a filing-backed fact.
- Keep DVL changes isolated. The existing low-level DVL tests are the behavioral reference for correction rules.
- Add pipeline tests at the `core.verify()` level before adding route-specific tests.
- Keep evidence retrieval failure-tolerant. A provider outage should produce missing evidence and a lower-confidence result where possible, not an unrelated server crash.
- Do not add UI-specific provider calls. Frontend code should use typed API functions.
- The terminal UI is intentionally dense and restrained. Future visual changes should preserve panel placement, typography, colors, spacing, and compact information hierarchy.
- Run `npm run build` after frontend changes. Existing warnings in unrelated components should be reviewed separately from functional build failures.
- Run the benchmark runner when changing math, trust, provider selection, or output formatting.
- Keep future work aligned with the architecture boundary in `ARCHITECTURE.md`; do not introduce consensus, caching infrastructure, SDKs, CLI packaging, or enterprise systems as incidental refactors.
