# FinVerify Terminal — Workspace Functionalization Spec

**Status:** Inspection/specification only. No code modified.
**Scope:** `/` (now the Workspace — see §1), specifically `app/workspace/WorkspacePage.tsx` and everything under `components/workspace/`.
**Goal of this document:** enable a second engineer (or Codex) to turn the Workspace from a visually-complete, largely static dashboard into a genuinely functional terminal, without re-deriving any of the findings below.

Save this file at `docs/WORKSPACE_FUNCTIONALIZATION_SPEC.md` in the repo.

---

## 1. Current Architecture

The visual-implementation phase is complete and both routing conflicts flagged in the prior inspection report have been resolved:

- `/` now renders `WorkspacePage` directly (`app/page.tsx` imports and re-exports `./workspace/WorkspacePage`).
- `/workspace` is now a redirect to `/` (`app/workspace/page.tsx`: `redirect("/")`).
- `/terminal` now exists and hosts the original DVL query demo (the page previously living at `/`).
- Root nav (`app/layout.tsx`) matches the target screenshot: wordmark + `v1.3` + mode toggle, right-aligned `MODEL: llama-3.1-8b-instant`, live dot, `SYSTEM HEALTH — ALL SYSTEMS OPERATIONAL`, health indicator, `FV` badge.

**Component tree, current state:**

```
WorkspacePage (app/workspace/WorkspacePage.tsx)
├── MarketAlertBanner       — static, 5 hardcoded alerts, no interaction
├── Left column
│   ├── MarketPulsePanel    — LIVE (getMarketIndices, 30s poll, fallback data)
│   ├── WatchlistPanel      — LIVE (quote polling, fallback), row click → onSelectSymbol (works)
│   └── IntegrityMonitorPanel — static DEMO_DATA, row click → onSelectSymbol (works)
├── Center column
│   └── FocusView
│       ├── default state (no selectedSymbol):
│       │   ├── GlobalTransactionMonitor  — static demo map (real continent SVG data now, worldMapData.ts)
│       │   ├── VerificationPulse         — static, NEW component, no props/state
│       │   ├── RecentVerificationActivity — static, NEW, no props/state
│       │   ├── NeedsAttention             — static, NEW, no props/state
│       │   ├── VerificationCoverage       — static, NEW, no props/state
│       │   ├── LiveVerificationTrace      — static, NEW, single hardcoded trace, no props/state
│       │   └── CommandBar                 — NEW, real backend calls (verifyNumber/queryLLM),
│       │                                      result is fetched and then DISCARDED (see §4)
│       └── company-selected state: unchanged from prior report — 6-tab strip reusing
│           EarningsVerification.tsx and MetricPanel.tsx (both real, DVL-backed)
└── Right column
    ├── NewsRadarPanel, FilingRadarPanel, EarningsRadarPanel, SectorMonitorPanel — all static
└── WorkspaceBottomBar — status footer, backendOnline-driven dot + hardcoded "23/23 Active" etc.
```

**Key structural fact:** `CommandBar`, `VerificationPulse`, `RecentVerificationActivity`, `NeedsAttention`, `VerificationCoverage`, and `LiveVerificationTrace` are composed inside `FocusView.tsx`'s default-state branch, **not** in `WorkspacePage.tsx` itself. `WorkspacePage.tsx` only owns `selectedSymbol` state and passes it down. This matters for §6 — any shared Workspace state needs to live at or above `FocusView`, since that's the only place all six of these new components currently meet.

The previously-flagged dead file (`app/workspace/WorkspaceTopBar.tsx`, unused) is still present and still unimported — not addressed in the visual phase, out of scope for this one too, listed again in §14.

---

## 2. Static vs. Functional Inventory

| Component | Current data source | Static? | Existing API? | Interaction | Functionality gap |
|---|---|---|---|---|---|
| `MarketPulsePanel` | `getMarketIndices()` (`lib/api.ts` → `GET /market/indices`), 30s poll | No (live, with fallback) | Yes | Timeframe tabs (1D/1W/1M/YTD/1Y) — **no `onClick` wired to refetch by range**, tabs only change local `activeTimeframe` state visually | Chart doesn't actually re-fetch/re-render for the selected timeframe — chart data (`generateChartData`) is client-generated random noise regardless of tab |
| `WatchlistPanel` | Live quote polling (symbol list), 30s poll | No (live, with fallback/DEMO badge) | Yes | Row click → `onSelectSymbol` (**works, real**) | `EDIT` and `+ ADD SYMBOL` are plain `<span>`s with hover CSS only — no `onClick`, no state, non-functional |
| `IntegrityMonitorPanel` | `DEMO_DATA` constant | Yes, fully static | No | Row click → `onSelectSymbol` (**works, real**) | `VIEW INTEGRITY DASHBOARD →` is a plain `<span>`, non-functional. No backend integrity-scoring endpoint exists (see §3) |
| `GlobalTransactionMonitor` | Hardcoded `CITIES`/`ARCS` arrays; SVG paths from `worldMapData.ts` (generated once, real geography, not live data) | Yes, fully static | No | Node/city clicks — **need re-verification**; sector filter tabs — visual only, no filtering logic confirmed | No transaction/flow backend exists at all; this is decorative and always will be unless a transaction-data source is scoped in |
| `VerificationPulse` | Hardcoded `PULSE_METRICS` array | Yes, fully static | No | None — pure display, "LIVE" badge is decorative (no data ever changes) | No props, no state. Numbers (1,248 claims checked, etc.) don't correspond to anything real |
| `RecentVerificationActivity` | Hardcoded `DEMO_ACTIVITY` array (5 items) | Yes, fully static | No | None | Same — no props/state, can't currently receive a real verification event even if one existed |
| `NeedsAttention` | Hardcoded `DEMO_ITEMS` array (4 items) | Yes, fully static | No | None | Same |
| `VerificationCoverage` | Hardcoded `DEMO_COVERAGE` array (7 companies) | Yes, fully static | No | None | Same |
| `LiveVerificationTrace` | Hardcoded single `DEMO_TRACE` object (6 steps, frozen timestamp `23:18:32`) | Yes, fully static | No | None | "LIVE" badge decorative; trace never advances or updates; single NVDA example is the only one that will ever render |
| `CommandBar` | User input; on submit calls real `verifyNumber()`/`queryLLM()` (`lib/api.ts`) when backend is online, or a client-side `quickDVL()` fallback for a small hardcoded `DEMO_NUMS` map | Input is live; **but the response is fetched and then thrown away** | Yes — genuinely wired to `/verify` and `/query` | Text submit (Enter or button), Ctrl+K focus, Escape clear, quick-action chips (populate input text only) | **This is the single biggest functionality gap in the whole Workspace.** See §4 |
| `NewsRadarPanel` / `FilingRadarPanel` | Hardcoded arrays | Yes | No | "VIEW ALL NEWS →" / "VIEW ALL FILINGS →" — plain `<span>`, non-functional | No news/filing backend endpoint exists |
| `EarningsRadarPanel` | Hardcoded array | Yes | No | None found | No earnings-calendar endpoint exists (note: `/v1/earnings/{ticker}` exists but is per-ticker transcript verification, not a calendar) |
| `SectorMonitorPanel` | Hardcoded `SECTORS` array | Yes | No | 1D/1W/1M buttons — no `onClick`, purely decorative | No sector-performance endpoint exists |
| `WorkspaceBottomBar` | `useConnection()` for the online/offline dot (real); everything else (`23/23 Active`, sparkline) hardcoded/generated | Mostly static | Partially (connection status only) | None | "Data Sources 23/23 Active" is a fixed string, not derived from any real count |
| `MarketAlertBanner` | Hardcoded `ALERTS` array | Yes | No | None | No news/alert backend exists |
| `FocusView` (company-selected state) | Reuses `EarningsVerification`/`MetricPanel` | No (real) | Yes (`getFundamentals`, `getEarningsVerification`) | Tab switching (works) | Already functional — carried over from prior phase, no gap here |

---

## 3. Existing API Inventory

Full backend surface (`finverify-terminal/backend/app/main.py`), grouped by relevance to Workspace functionalization.

### Verification / DVL

| Endpoint | Method | Request | Response | Notes |
|---|---|---|---|---|
| `/query` | POST | `{ question: string, context?: string }` | `QueryResponse` (below) | Free-text query → LLM answer + DVL verification. Used by `CommandBar` and `/terminal`'s `queryLLM()` |
| `/verify` | POST | `{ question: string, raw_number: number }` | `QueryResponse` | Verify a specific raw number against a question. Used by `CommandBar`'s `DEMO_NUMS` path and `/terminal`'s `verifyNumber()` |
| `/v1/verify` | POST | (typed request, `V1VerifyResponse`) | `V1VerifyResponse` | Newer/versioned verify endpoint — **not currently called by any frontend `lib/api.ts` function**. Worth checking before building new integrations, in case it's the intended successor to `/verify` |
| `/v1/verify/batch` | POST | — | `BatchVerifyResponse` | Batch verification — **not wired into the frontend at all currently**. Could be relevant for Coverage/Pulse aggregate numbers, see §7 |
| `/sample-queries` | GET | — | `SampleQuery[]` | Pre-canned example questions, used on `/terminal`, not currently used in Workspace |

`QueryResponse` shape (from `lib/api.ts`, matches backend `main.py` model):
```ts
{
  question: string;
  raw_text: string | null;
  raw_number: number | null;
  verified_number: number | null;
  correction_log: { rule: string; before: number; after: number; description: string }[];
  trust_score: string;       // "HIGH" | "MEDIUM" | "LOW"
  trust_color: string;
  display_value: string;
  mode?: string;
  verified?: boolean;
}
```

No auth headers required on any of these (no `Authorization` header sent by `lib/api.ts`). Backend CORS is origin-allowlisted via `CORS_ORIGINS` env var, not token-based.

No streaming: `/query` and `/verify` are plain request/response (`await res.json()`), not `StreamingResponse` or SSE. No verification-stage events are pushed incrementally — the entire `QueryResponse` arrives at once, after the full pipeline runs server-side.

**Internal DVL pipeline** (`backend/app/dvl.py`) is `scale_correction → sign_correction → magnitude_correction`. This is the ground truth for what "verification" actually consists of server-side. It does **not** correspond to the six-stage `CLAIM EXTRACTED / ENTITY RESOLVED / EVIDENCE RETRIEVED / CALCULATION RECONSTRUCTED / CONSTRAINTS CHECK / RESULT` narrative in `LiveVerificationTrace.tsx` — see §5 for the exact mapping.

### Market

| Endpoint | Method | Notes |
|---|---|---|
| `/market/quotes` | GET | `?symbols=A,B,C` — used by `getMarketQuotes()`, not currently called anywhere in Workspace (Watchlist has its own fetch path — confirm which client it actually uses before assuming duplication) |
| `/market/indices` | GET | Used by `MarketPulsePanel` |
| `/market/verified-metrics` | GET | `?symbol=&metric=` — single verified metric, DVL-backed |
| `/market/metrics` | GET | Not currently called by any inspected frontend file |
| `/market/all-metrics` | GET | `?symbol=` — used via `getAllMetrics()`, and by `MetricPanel.tsx` (reused inside `FocusView`'s Financials tab) |
| `/ws/market` | WebSocket | Real, working (`backend/app/main.py:510`, 5s-ish interval). `createMarketWebSocket()` exists in `lib/api.ts` but **is not called anywhere in the Workspace tree currently** — Watchlist/MarketPulse both poll via `setInterval`, not the socket |

### Fundamentals / Earnings (SEC-backed)

| Endpoint | Method | Notes |
|---|---|---|
| `/v1/fundamentals/{ticker}` | GET | Real SEC EDGAR data, DVL-verified. Used by `FocusView`'s Evidence tab (`getFundamentals`) |
| `/v1/earnings/{ticker}` | GET | Real transcript-based claim verification, used by `FocusView`'s Verification tab (`EarningsVerification.tsx` via `getEarningsVerification`) |
| `/v1/ingest/sec`, `/v1/ingest/transcripts` | POST | Ingestion endpoints, not relevant to Workspace read-side functionality |
| `/v1/rag/*` | GET/POST | RAG stats/query/seed — not currently wired into any Workspace component |

### History

| Endpoint | Method | Notes |
|---|---|---|
| `/v1/history/{user_id}` | GET/DELETE | Persistent per-user query history (Supabase-backed). `getHistory`/`clearHistoryRemote` exist in `lib/api.ts` but are **not called anywhere in Workspace** — used on `/dashboard` only, per the prior architecture report |
| `/v1/history` | POST | `saveToHistory()` — same, not currently invoked from Workspace/CommandBar |

### FCG (Financial Constraint Graph)

| Endpoint | Method | Notes |
|---|---|---|
| `/v1/fcg/verify`, `/v1/fcg/normalize`, `/v1/fcg/constraints` | POST/GET | Not wired into `lib/api.ts` at all (no exported function calls these). Out of scope unless a future phase explicitly needs constraint-graph verification in Workspace — flagged as available but unintegrated |

**Environment variables relevant to any of this:** `NEXT_PUBLIC_API_URL` (defaults to the hosted HF Space if unset), `NEXT_PUBLIC_WS_URL` (derived from API URL if unset). Backend: `INFERENCE_URL`/`INFERENCE_MODEL`/`INFERENCE_API_KEY` (LLM), `CORS_ORIGINS`, `MARKET_CACHE_TTL`, `SUPABASE_URL`/`SUPABASE_KEY` (history), `PINECONE_API_KEY` (RAG). None of these need to change for Workspace functionalization — the endpoints needed already exist and are reachable with current config.

**Error/timeout behavior:** `checkHealth()` uses a 5s `AbortController` timeout; `queryLLM`/`verifyNumber` have no client-side timeout at all (will hang as long as the browser allows). `CommandBar`'s `handleSubmit` wraps everything in `try/catch` and silently swallows errors (`catch { /* swallow */ }`) — no error is ever shown to the user. This needs to change for any real functionalization (see §4).

---

## 4. CommandBar Implementation Plan

**Current flow, exactly as it exists today:**

1. User types into the input (or clicks a quick-action chip, which only populates the input text — "Upload Document" has an empty `query: ""` and does nothing at all when clicked).
2. On submit: if the trimmed text matches a known ticker (`KNOWN_TICKERS`), it calls `onSelectSymbol()` and returns — this part is real and already correctly routes into `FocusView`'s company view.
3. Otherwise: if the text exactly matches one of four hardcoded strings in `DEMO_NUMS`, it calls `verifyNumber()` (or the local `quickDVL()` fallback if offline) — but never reads or uses the response.
4. Otherwise, if backend is online, it calls `queryLLM(q)` — again, response is never read or used.
5. `finally` block clears `isLoading` and empties the input. The `isLoading` amber dot is the only visible feedback the user ever gets, for roughly as long as the network call takes, and then everything disappears with no result shown anywhere.

**What's required to make this real**, in order:

1. **Result state.** `CommandBar` (or a parent that owns shared Workspace state, per §6) needs to hold the last `QueryResponse` (or an error), not discard it.
2. **Result surface.** The target screenshot doesn't show an explicit "answer panel" distinct from the trace/pulse/activity components — the implied design is that a real submission should populate `LiveVerificationTrace` (as the "current" trace) and prepend an entry to `RecentVerificationActivity`. This is a design decision, not just an engineering one — flagged, not resolved here. Minimum viable: at least show the raw result inline near the input (even a simple one-line "✓ VERIFIED — 12.4% (was 1240%)" style summary) so the network call has *any* visible effect before wiring it further.
3. **Error state.** Replace the silent `catch { /* swallow */ }` with a real error path — show something like "Verification failed — try again" near the input, styled with `t-red`, consistent with the rest of the design system.
4. **Loading state.** Already present (`isLoading`, amber dot, disabled input) — keep as-is, just extend its duration to cover "waiting to render the result," not just "waiting for the fetch."
5. **Reuse, don't duplicate:** `/terminal`'s `app/terminal/page.tsx` already has a fuller reference implementation of this exact flow (`queryLLM`/`verifyNumber` → `QueryResponse` → rendered via `TerminalPanel`, `VerificationLog`, `TrustScore`, `DVLReport`, `QueryInterpretation`). Do not reimplement result-rendering logic from scratch in Workspace — either import/adapt these existing components, or extract a shared result-rendering piece both `/terminal` and Workspace can use. `VerificationLog.tsx`'s `PipelineStage` type in particular is worth checking against §5's trace-mapping question, since it may already encode a similar step concept for `/terminal`.
6. **Quick actions need real targets.** "Verify a Claim" → `"Verify TSLA revenue claim"` is not parseable by `/query` as a structured request; it will just hit the generic LLM query path like any other free text. "Analyze Apple 10-Q Filing" and "Check Earnings" quick actions should more plausibly route to the *already-real* `getFundamentals("AAPL")` / `getEarningsVerification("NVDA")` calls (i.e., behave like selecting that symbol and jumping to the Evidence/Verification tab) rather than going through the generic `/query` LLM path — this reuses real, working functionality instead of routing everything through free-text LLM queries. "Upload Document" has no backend support anywhere in the inspected API surface — flag to the user as out of scope until a document-upload endpoint exists; do not fabricate one.

---

## 5. Live Verification Trace — Stage-by-Stage Reality Check

| Stage (as shown in UI) | Real backend-supported? | Derivable from existing `/query`/`/verify` response? | UI-only progress state? | Notes |
|---|---|---|---|---|
| CLAIM EXTRACTED | No | Partially — `raw_text`/`raw_number` on `QueryResponse` represent "what was extracted," but there's no distinct extraction *step* exposed, just the final parsed value | Yes, would have to be presented as such | Could legitimately show `raw_text`/`raw_number` once the response arrives, framed as "what was found," not as a live streaming stage |
| ENTITY RESOLVED | No | No — no entity/ticker-resolution field anywhere in `QueryResponse` | Yes | Could be approximated only when the query flow already knows the symbol (e.g., quick-action-routed fundamentals/earnings calls per §4 point 6), by showing the resolved ticker/company name that was already selected — not something the generic `/query` endpoint reports back |
| EVIDENCE RETRIEVED | **Yes, but only for fundamentals/earnings flows** | `getFundamentals()` returns `source_url`/`filing_date`; `getEarningsVerification()` returns `source` | For generic `/query`/`/verify` calls: no | This stage is real and derivable **only** when the request went through `/v1/fundamentals` or `/v1/earnings`, not through `/query`/`/verify` |
| CALCULATION RECONSTRUCTED | **Yes** | `correction_log` (array of `{rule, before, after, description}`) is exactly this — the DVL's scale/sign/magnitude correction steps | No — this one is genuinely real and already returned by both `/query` and `/verify` | This is the strongest, most legitimate stage to wire up first |
| CONSTRAINTS CHECK | Partially | `/v1/fcg/constraints` exists but is **not currently called anywhere in the frontend** (§3) — the current `/query`/`/verify` responses carry no constraints-check field | Yes, unless FCG is separately integrated | Do not claim "All N constraints PASSED" from `/query`/`/verify` responses — that field doesn't exist there. Only legitimate if `/v1/fcg/*` is separately wired in a later phase |
| RESULT | **Yes** | `trust_score`, `trust_color`, `display_value`, `verified` are all real, directly-returned fields | No | Fully real, straightforward to wire |

**Bottom line for the implementer:** two of six stages (Calculation Reconstructed, Result) can be wired to real data immediately from the existing `/query`/`/verify` response. One stage (Evidence Retrieved) is real but only for the fundamentals/earnings-routed flows, not generic queries. Three stages (Claim Extracted, Entity Resolved, Constraints Check) have no true backend counterpart today and must either be presented honestly as UI-only progress/staging indicators (e.g., a generic "processing" animation with no invented specifics), or left out of any real-data version of the trace until a backend change adds them. **Do not have the future implementation fabricate specific values for these three** (e.g., don't invent a plausible-sounding "Match: Revenue" or "All 4 constraints PASSED" from nothing) — this is exactly the kind of fabrication the project has explicitly avoided elsewhere (`IntegrityMonitorPanel`, `GlobalTransactionMonitor` are marked/treated as demo-only for the same reason).

---

## 6. Workspace State Architecture

**Current reality:** there is no central Workspace state model. `WorkspacePage.tsx` owns exactly one piece of state (`selectedSymbol`), threaded down through props to `WatchlistPanel`, `IntegrityMonitorPanel`, and `FocusView`. Every other component — `CommandBar`, `VerificationPulse`, `RecentVerificationActivity`, `NeedsAttention`, `VerificationCoverage`, `LiveVerificationTrace` — is entirely self-contained with hardcoded data and zero props. There is currently no duplicated data to reconcile (nothing is fetched twice with different results), because nothing beyond `selectedSymbol` is shared at all yet.

**Recommended minimal addition** — do not over-engineer, per the brief:

```
WorkspacePage
  selectedSymbol: string | null            (existing, unchanged)
      ↓ (new, one level up from CommandBar — likely lifted into FocusView or a
         thin WorkspaceVerificationProvider wrapping FocusView's default-state branch)
  lastVerification: QueryResponse | null    (new)
  verificationHistory: QueryResponse[]      (new — bounded, e.g. last 20, purely client-side/session,
                                              NOT the same thing as the real /v1/history backend —
                                              don't conflate the two)
      ↓
  CommandBar        — writes lastVerification + appends to verificationHistory on submit
  LiveVerificationTrace — reads lastVerification, renders real stages per §5's mapping,
                           falls back to the current static DEMO_TRACE example when
                           verificationHistory is empty (so the panel isn't blank on first load)
  RecentVerificationActivity — reads verificationHistory (most recent N), same fallback pattern
  VerificationPulse  — derives simple counts (checked/verified/corrected — NOT conflicts/unresolved,
                        which have no backend concept, see §7) from verificationHistory this session
  NeedsAttention     — NOT populated from verificationHistory unless/until a "flagged" or
                        low-trust threshold concept is explicitly defined; keep static or empty-state
                        until that's decided (see §7)
  VerificationCoverage — per-company data; NOT derivable from a single-session verificationHistory
                        with any real coverage numbers — keep static/demo, or wire to
                        /v1/fcg or /market/all-metrics per company if that's judged worth it later
```

The smallest correct shape is a single `useState<QueryResponse | null>` for "last result" plus a bounded array for "session history," lifted no higher than necessary (i.e., not necessarily all the way to `WorkspacePage` — only as high as `FocusView`, since that's where all consumers currently live). A `useReducer` or context provider is not warranted at this scale — plain lifted `useState` plus prop-drilling into six sibling components under `FocusView` is sufficient and matches the existing code style (no state library, no Context beyond the existing `ConnectionProvider`).

**Do not** attempt to reconcile this session-only state with the real Supabase-backed `/v1/history` — those are different concerns (per-user persistent history vs. this-session Workspace activity feed) and conflating them risks either double-writing history or displaying another user's session data.

---

## 7. Panel-by-Panel Plan

| Panel | A. Current behavior | B. Static data | C. Existing real source | D. Required functional behavior | E. Dependencies | F. Recommended mode |
|---|---|---|---|---|---|---|
| Market Pulse | Live index fetch + fake chart | Chart line (`generateChartData`) | `/market/indices` | Wire timeframe tabs to actually refetch/re-render for the selected range, or remove the tabs if range data isn't available | Backend would need historical index data by range — **check whether `/market/indices` supports a range param before promising this**; if not, flag and leave tabs decorative-but-labeled-as-1D-only | Polling (already is) |
| Watchlist | Live quotes, working symbol-select | none beyond quotes | `getMarketQuotes`/live poll | Wire `EDIT` (remove/reorder symbols) and `+ ADD SYMBOL` (add a ticker to the polled list) | Needs a small local "watchlist symbols" state (session or localStorage) — no backend persistence exists for this, don't invent one | Session-based (client state), API-backed for quotes |
| Integrity Monitor | Static list, working symbol-select | `DEMO_DATA` | none | No real integrity-scoring endpoint exists — keep static/demo, or derive a lightweight proxy from `correction_log` frequency in `verificationHistory` (§6) if that's judged good enough; don't claim it's a real integrity score if it's a proxy | §6 state | Static until a real source exists, OR locally-derived proxy (label clearly if so) |
| Global Transaction Monitor | Static map + demo transaction data | `CITIES`/`ARCS` | none | No transaction-data backend exists anywhere in this repo — recommend **keep fully static**, this is decorative hero content, not a functionality gap to close | none | Static (explicitly, not a gap) |
| Verification Pulse | Static 5-stat strip | `PULSE_METRICS` | none directly, but see §6 | Wire `CLAIMS CHECKED`/`VERIFIED`/`CORRECTED` counts to `verificationHistory` length/breakdown this session; `CONFLICTS`/`UNRESOLVED` have no backend concept — keep those two static or remove them rather than fabricate a definition | §6 state | Session-based for 3 of 5 fields; static for 2 |
| Recent Verification Activity | Static 5-item list | `DEMO_ACTIVITY` | none directly, but see §6 | Prepend real `verificationHistory` entries as they occur; fall back to demo content when history is empty | §6 state | Session-based |
| Needs Attention | Static 4-item list | `DEMO_ITEMS` | none | No backend "flagged item" concept exists outside of `EarningsVerification`'s per-ticker `flagged`/`flags` field (real, but scoped to one ticker's transcript, not a cross-company feed) — keep static until a cross-company "attention" concept is explicitly defined, or scope it down to "flags from tickers the user has actually looked at this session" | §6 state (optional, reduced scope) | Static, or narrowly session-derived — needs a product decision, don't guess |
| Verification Coverage | Static 7-row table | `DEMO_COVERAGE` | none | No per-company aggregate coverage endpoint exists. `/v1/fcg/verify`/`/market/all-metrics` could theoretically be called per-watchlist-symbol to build something real, but that's N extra API calls per render and a real scope increase — flag as a larger future phase, keep static for this pass | N/A for this phase | Static (explicitly deferred) |
| Live Verification Trace | Static single example | `DEMO_TRACE` | 3 of 6 stages real, per §5 | Wire to `lastVerification` per §5/§6, with the 3 non-real stages either omitted or shown as generic non-specific progress indicators, never fabricated specifics | §6 state | Session-based (real result) with honest UI-only stages where backend doesn't support them |
| Command Bar | Real fetch, discarded result | `DEMO_NUMS`, `KNOWN_TICKERS` | `/query`, `/verify` | Per §4 — surface result, add error state, route quick actions to real fundamentals/earnings calls where sensible | §6 state | API-backed (already is) — just needs its result actually used |

---

## 8. Real Live Data vs. No Real Source

**REAL LIVE DATA AVAILABLE (already fetched or fetchable with existing endpoints):**
- Market indices (`MarketPulsePanel`) — `/market/indices`
- Market quotes (`WatchlistPanel`, `TickerBar`) — `/market/quotes` or the polling pattern already in use
- `/ws/market` WebSocket exists and works but is **currently unused** in Workspace (both `MarketPulsePanel` and `WatchlistPanel` poll via `setInterval` instead) — worth considering as a lower-latency replacement for polling, but that's an optimization, not a functionality gap; don't conflate "not using the socket" with "not live"
- Fundamentals (`FocusView` Evidence tab) — `/v1/fundamentals/{ticker}`, real SEC data
- Earnings verification (`FocusView` Verification tab) — `/v1/earnings/{ticker}`, real transcript data
- Verification results generally — `/query`, `/verify`, real DVL pipeline, just not currently surfaced (§4)
- Backend online/offline status (`WorkspaceBottomBar`, all "DEMO MODE" badges) — `useConnection()`/`checkHealth()`, real

**NO REAL DATA SOURCE CURRENTLY AVAILABLE (do not fake "LIVE" for these):**
- Global transaction/flow data (city volumes, arcs) — no backend concept exists; keep static, and consider whether the "LIVE" implication of the map's live-pulse dots should be softened, since there's no live data behind it (flag to user, don't unilaterally change the visual design per the brief's constraint)
- News (`NewsRadarPanel`, `MarketAlertBanner`) — no news ingestion endpoint anywhere in the inspected backend
- Filing radar (`FilingRadarPanel`) — no filing-feed endpoint (SEC fundamentals exist per-ticker on demand, but not as a push feed)
- Earnings calendar (`EarningsRadarPanel`) — no calendar endpoint (earnings *verification* exists per-ticker, that's different from a forward-looking calendar)
- Sector performance (`SectorMonitorPanel`) — no sector-aggregate endpoint
- Cross-company integrity scores, coverage table, needs-attention feed — see §7, no aggregate backend source exists
- "Data Sources 23/23 Active" in `WorkspaceBottomBar` — this number has no real source and is a fixed string; either remove the specific count or derive an honest one (e.g., count of endpoints successfully health-checked) — don't leave a fabricated-looking precise number if it isn't real

For everything in the second list, the brief's own instruction applies directly: keep static, make locally interactive where that's honestly achievable (e.g., watchlist add/remove), or build an abstraction (a typed but currently-unimplemented fetch function, clearly commented as not-yet-backed) for future integration. Do not add a third-party news/market-data provider to make these look live — none was requested and it would silently expand scope.

---

## 9. Buttons and Interactions Inventory

| Action | Current behavior | Desired behavior | Existing implementation? | Required work |
|---|---|---|---|---|
| Verify a Claim (quick action) | Populates input with `"Verify TSLA revenue claim"` | Route to a real, structured verification (ideally reusing `/v1/earnings` flagged-claims flow for a real ticker) rather than free-text `/query` | Partial (`/query` exists but isn't a good fit) | Redesign this specific quick action's target per §4 point 6 |
| Analyze Filing (quick action) | Populates input with `"Analyze latest 10-K filing"` | Same issue — free text isn't a great fit; consider routing to `getFundamentals()` for a default/selected ticker | Partial | Same as above |
| Analyze Apple 10-Q Filing (quick action) | Populates input with `"Analyze Apple 10-Q filing"` | Should call `getFundamentals("AAPL")` directly and select AAPL, reusing the real, working Evidence tab | Yes, fully (just needs rewiring) | Small — change the chip's `onClick` to call `onSelectSymbol("AAPL")` instead of populating text |
| Check Earnings (quick action) | Populates input with `"Check NVDA earnings"` | Should call `getEarningsVerification("NVDA")` directly and select NVDA + Verification tab | Yes, fully (just needs rewiring) | Small — same pattern as above |
| Upload Document (quick action) | `query: ""`, clicking does nothing | No backend document-upload endpoint exists | No | Out of scope until a backend endpoint exists — flag to user, don't build a fake upload UI |
| Add Symbol (Watchlist) | Plain span, no handler | Add a ticker to a client-side watchlist list | No | New: small local state + input, per §7 |
| View All (Watchlist / News / Filings / Integrity Dashboard) | Plain spans, no handler | Unclear what "all" means without a dedicated sub-view/route — likely out of scope for this phase unless a target sub-page is specified | No | Flag to user — needs a destination defined before building |
| Map node interactions | Needs direct re-verification in `GlobalTransactionMonitor.tsx` — not confirmed clickable from this pass | If clickable, should plausibly call `onSelectSymbol` for a related ticker if the city has an associated company; if not clickable, no gap | Unclear | Confirm current behavior in a follow-up read before scoping work here |
| Recent Activity / Needs Attention row clicks | No `onClick` present in either component currently | Clicking a row should plausibly call `onSelectSymbol(item.symbol)` to jump to that company | No | Small — both already carry a `symbol` field in their static data shape, trivial to wire once real data exists (§6) |
| Command submission (Enter / button / send arrow) | Real fetch, discarded result | Show result, per §4 | Partial | See §4 in full |
| Ticker bar item clicks | Not confirmed clickable — needs direct check | If clickable, should call `onSelectSymbol` | Unclear | Confirm in follow-up read |

---

## 10. Data Flow Design

```
User
 │
 ├─ types free text / clicks a quick-action chip
 ▼
CommandBar
 │  submit → decide route:
 │    (a) known ticker text        → onSelectSymbol(ticker)                [already real]
 │    (b) "Analyze X Filing" chip  → onSelectSymbol(X) + jump to Evidence  [rewire, §9]
 │    (c) "Check X Earnings" chip  → onSelectSymbol(X) + jump to Verify   [rewire, §9]
 │    (d) known DEMO_NUMS text     → verifyNumber(q, n)                   [existing]
 │    (e) anything else            → queryLLM(q)                          [existing]
 ▼
Existing FinVerify API — POST /verify or POST /query  (finverify-terminal/backend/app/main.py)
 ▼
Typed QueryResponse  { question, raw_number, verified_number, correction_log,
                        trust_score, trust_color, display_value, verified }
 ▼
Workspace session state (lifted no higher than FocusView, per §6)
  lastVerification: QueryResponse | null
  verificationHistory: QueryResponse[]   (bounded, session-only, NOT /v1/history)
 │
 ├─→ LiveVerificationTrace     — renders CALCULATION RECONSTRUCTED + RESULT from
 │                                lastVerification directly; EVIDENCE RETRIEVED only
 │                                when the request came via route (b)/(c) above;
 │                                CLAIM EXTRACTED / ENTITY RESOLVED / CONSTRAINTS CHECK
 │                                shown as generic non-specific progress only, per §5
 ├─→ RecentVerificationActivity — prepends verificationHistory entries, newest first
 ├─→ VerificationPulse         — derives CLAIMS CHECKED / VERIFIED / CORRECTED counts
 │                                from verificationHistory.length and trust_score/
 │                                correction_log breakdown; CONFLICTS/UNRESOLVED
 │                                remain static (no backend concept, §7)
 ├─→ NeedsAttention            — unchanged/static this phase (§7)
 └─→ VerificationCoverage      — unchanged/static this phase (§7)
```

Route (b)/(c) above (quick actions routing to `getFundamentals`/`getEarningsVerification` instead of `/query`) is the one new "wiring" decision this data-flow design depends on — it's what lets `EVIDENCE RETRIEVED` become real for those flows. Free-text queries via `/query` will never have real evidence data, and that's fine — the trace for those should honestly show fewer "real" stages, not fabricate the missing ones.

---

## 11. Ordered Implementation Plan

1. **Shared Workspace state/data model** (§6). Nothing downstream can be built correctly without this existing first — every other numbered item reads from or writes to it.
2. **CommandBar real request handling** (§4, points 1–4: result state, result surface, error state, keep loading state). This makes the existing real API calls actually visible for the first time.
3. **Verification result handling / routing decision** (§4 point 6, §9 rows for the 3 filing/earnings quick actions). Depends on step 1 (state) and 2 (CommandBar producing a usable result/route).
4. **Live Verification Trace** wired to real `lastVerification`, honest about which of the 6 stages are real per §5. Depends on 1–3.
5. **Recent Activity** wired to `verificationHistory`. Depends on 1–3; independent of 4.
6. **Needs Attention** — decide scope first (full static-remains vs. narrow session-derived, §7); implement only after that decision, don't guess. Depends on 1 if scope is expanded, otherwise no dependency.
7. **Verification Pulse** — wire the 3 derivable fields (Claims Checked/Verified/Corrected) to `verificationHistory`; leave Conflicts/Unresolved static. Depends on 1, 5.
8. **Coverage** — remains static this phase per §7 (explicitly deferred, not a dependency chain item).
9. **Locally interactive Workspace controls** — Watchlist Add/Edit (§9), Recent Activity/Needs Attention row-click-to-select (§9, trivial once 5/6 exist). No backend dependency, but logically sits after the data model exists so row data has a `symbol` field to click through on.
10. **Legitimate live-data integrations only where existing sources support them** — e.g., considering `/ws/market` in place of polling for Market Pulse/Watchlist (optimization, not new functionality; genuinely optional and last-priority).

Each step should be validated (build, lint, manual click-through) before the next begins, consistent with the incremental-phase approach used in the prior visual-implementation pass.

---

## 12. Files Codex Should Modify

- `components/workspace/CommandBar.tsx` — result/error state, quick-action routing (§4, §9)
- `components/workspace/LiveVerificationTrace.tsx` — real-data wiring, honest partial-stage rendering (§5)
- `components/workspace/RecentVerificationActivity.tsx` — consume session state instead of `DEMO_ACTIVITY`
- `components/workspace/VerificationPulse.tsx` — consume session state for 3 of 5 fields
- `components/workspace/FocusView.tsx` — introduce/lift the shared session state (§6), pass down to the 6 components above
- `components/workspace/WatchlistPanel.tsx` — Add/Edit symbol interactivity (§9), only if scoped in
- `components/workspace/NeedsAttention.tsx` — only if scope is explicitly expanded per §7's flagged decision
- Possibly a new small file, e.g. `components/workspace/useWorkspaceVerification.ts` (a hook encapsulating the state in §6), if that keeps `FocusView.tsx` from getting too large — implementer's call, not prescribed here as mandatory

## 13. Files Codex Should NOT Modify

- Anything under `finverify-terminal/backend/` — no backend/DVL/algorithm changes in this phase, full stop
- `finverify-bench/**`, `research/**` — benchmark and research code, unrelated and off-limits
- `app/market/page.tsx`, `app/metrics/page.tsx`, `app/dashboard/page.tsx` — Market/Research/Dashboard, out of scope
- `app/terminal/page.tsx` and its dedicated components (`QueryInput.tsx`, `TerminalPanel.tsx`, `VerificationLog.tsx`, `TrustScore.tsx`, `QueryInterpretation.tsx`, `DVLReport.tsx`, `HeroNetwork.tsx`) — **reuse/reference** these for patterns per §4 point 5, but don't modify them; if a shared extraction is genuinely needed, propose it rather than editing `/terminal` in place
- `components/EarningsVerification.tsx`, `components/MetricPanel.tsx` — real, working, reused by `FocusView`'s company-selected state; do not touch
- `components/workspace/GlobalTransactionMonitor.tsx`, `components/workspace/worldMapData.ts` — explicitly static/decorative per §7/§8, no functionality work scoped here
- `components/workspace/IntegrityMonitorPanel.tsx`, `components/workspace/VerificationCoverage.tsx` — explicitly deferred to a future phase per §7
- `components/workspace/MarketAlertBanner.tsx`, `components/workspace/RightColumnPanels.tsx` (News/Filing/Earnings/Sector) — no real backend source exists (§8); leave static this phase unless the user explicitly scopes it in
- `app/layout.tsx`, routing files, `tailwind.config.ts`, `app/globals.css` — no visual/routing changes, this is a functionality-only phase
- `package.json` — no new dependencies; everything needed already exists in `lib/api.ts`

---

## 14. Validation Checklist

- `npm run build` / `npm run lint` clean.
- Manual click-through: submit a free-text query via CommandBar → confirm a result renders somewhere near the input (not just the loading dot disappearing).
- Manual click-through: trigger an error (e.g., stop the backend or use dev tools to force a failed fetch) → confirm an error state renders, not a silent no-op.
- Manual click-through: click "Analyze Apple 10-Q Filing" quick action → confirm it selects AAPL and opens the Evidence tab with real fundamentals data (§9), not a free-text query.
- Confirm `LiveVerificationTrace` after a real submission shows the 2–3 genuinely-real stages populated from the actual response, and does not display fabricated specifics for the other stages (§5) — this is a correctness check, not just a visual one.
- Confirm `RecentVerificationActivity` and `VerificationPulse` update after a real submission, and confirm they still show sensible fallback content on first load with an empty history (no blank/broken panel).
- Confirm `selectedSymbol` flow (watchlist/integrity-row click → FocusView company state → deselect) still works exactly as before — this phase must not regress the one piece of real interaction that already worked.
- Confirm nothing in this phase silently invents numbers for Conflicts/Unresolved (Verification Pulse), Needs Attention, Verification Coverage, or Global Transaction Monitor — these should still read as static/demo (or be explicitly, visibly labeled as such) unless a real source was deliberately wired in.
- Confirm `/terminal`, `/market`, `/metrics`, `/dashboard` all still build and function unchanged.

---

## 15. Risks / Unknowns

- **Map node click behavior** and **ticker bar click behavior** were not conclusively confirmed in this pass — needs a direct follow-up read of the relevant handlers in `GlobalTransactionMonitor.tsx` and `TickerBar.tsx` before scoping any work against them (§9).
- **`/market/indices` range support** is unconfirmed — the Market Pulse timeframe tabs (1D/1W/1M/YTD/1Y) may not be backend-supportable at all; don't promise this without checking the backend implementation of that endpoint first.
- **`/v1/verify` vs `/verify`** — two verify endpoints exist; the frontend only uses the older `/verify`. Worth a deliberate check on whether `/v1/verify`'s `V1VerifyResponse` shape is meant to supersede it, before building new CommandBar logic on top of the older one.
- **`Needs Attention` and `Verification Coverage` scope** is a genuine open product decision, not an engineering one — this document intentionally does not resolve it, per §7 and §11 step 6/8. Get a decision before building either beyond what's specified.
- **"View All" destinations** (Watchlist, News, Filings, Integrity Dashboard) have no defined target — flagged, not resolved (§9).
- **`/ws/market`** exists and works but nothing currently uses it — switching Market Pulse/Watchlist from polling to the socket is a legitimate, low-risk improvement but is optional and explicitly last-priority (§11 step 10) so it doesn't distract from the CommandBar/state-model work that actually closes functionality gaps.
- This spec was produced from a single point-in-time repo read (shallow clone, no full git history available) — a `git log`/`git diff` against the previous visual-implementation commit was not available to double-check "what changed" beyond direct file comparison against the prior inspection report. If precise diff provenance matters, re-run with full git history access.
