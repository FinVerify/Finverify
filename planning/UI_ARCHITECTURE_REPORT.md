# FinVerify Frontend — UI Architecture Report

Repo: `github.com/FinVerify/Finverify`
Frontend root: `finverify-terminal/frontend` (Next.js 14, App Router, TypeScript, Tailwind, no server components used — everything is `"use client"`)
Backend root: `finverify-terminal/backend` (FastAPI)

This report documents the **current state** of the frontend so a future Claude Code session can build the **FinVerify Intelligence Workspace** (per the target spec) without re-discovering the repo.

---

## 1. Executive Summary

The current frontend is **not** a blank chatbot — it's two working surfaces:

1. **`/` (Terminal)** — a query-driven DVL demo. 3-column layout (Query Input | Results stack | Session/Errors/Stats tabs). This is the deepest, most polished part of the app but is 100% reactive: nothing renders until a query is submitted.
2. **`/market` (Market Mode)** — a 3-column, always-populated dashboard (Watchlist | Metrics-or-Earnings tabs | Market Context) that is **already very close to the target workspace's shape**. It has live/demo data toggling, symbol switching, and two proprietary-signal panels (DVL-verified metrics, earnings red-flag report).

There are also `/dashboard` (query history) and `/metrics` (research/paper results) routes, which are auxiliary and not part of the target workspace's information architecture, but contain reusable primitives (stat cards, trust badges, filter tabs).

**Critical finding: much of the target spec's Milestone 2 backend infrastructure already exists.** The FastAPI backend already exposes `/market/quotes`, `/market/indices`, `/market/all-metrics`, `/v1/fundamentals/{ticker}`, `/v1/earnings/{ticker}`, and a working `/ws/market` WebSocket (5s interval). The target spec's proposed `/ws/streams` is essentially a rename/extension of `/ws/market`. This means the workspace rebuild is primarily a **frontend layout and composition problem**, not a full-stack buildout — most data plumbing exists; it needs to be re-arranged into the 3-column-plus-bottom-bar workspace shape and extended with the new proprietary panels (Integrity Score, Opportunity Scanner, Trust Heatmap, Financial Health Timeline).

**Design system is in good shape and highly reusable.** A Bloomberg-style dark theme (`t-*` Tailwind color tokens, `.panel`/`.panel-header`/`.trust-badge`/`.label` CSS primitives in `globals.css`) is already consistent across every page. The new workspace should extend this design system, not replace it.

**Known data-integrity caveats to carry forward** (do not silently "fix" — flag to the user, these are pre-existing, intentional-for-demo shortcuts that the team is already aware of):
- Sparklines in `Watchlist.tsx` and `MetricPanel.tsx` are **synthetically generated** (`generateSparkline`/`generateTrend`), not real historical series.
- `MarketContext.tsx`'s "Sector Performance" bars are **hardcoded static data**, never fetched.
- `TerminalPanel.tsx`'s "latency" figure is a **random number** (`1.1 + Math.random()*1.2`), not a real measurement.
- Finnhub API key is read via `NEXT_PUBLIC_FINNHUB_KEY` and called **directly from the browser** in `lib/market.ts` — this exposes the key client-side. Fine for a free-tier demo key, but should not be treated as a secure pattern to extend.

---

## 2. Current Architecture

### 2.1 Stack
- Next.js 14.2 App Router, React 18, TypeScript, Tailwind 3.
- No state management library — plain `useState`/`useEffect`/React Context (`ConnectionProvider`).
- Charts: `recharts` (LineChart sparklines, BarChart, PieChart).
- PDF export: `@react-pdf/renderer` (dynamically imported, client-only).
- `@clerk/nextjs` and `@clerk/themes` are still listed in `package.json` dependencies but **auth has been fully stripped** (see `middleware.ts` comment: "Clerk auth has been stripped (Session 2.3)"). Dead dependency.
- No `contexts/`, `hooks/`, `providers/`, `styles/`, `store/` directories exist — `lib/` holds everything non-component (API client, DVL client fallback, market client, history persistence, connection context).

### 2.2 Directory Structure
```
finverify-terminal/frontend/
├── app/
│   ├── layout.tsx          — Root layout: navbar, TickerBar, ConnectionProvider wrapper
│   ├── page.tsx            — "/" Terminal (662 lines, the main DVL demo)
│   ├── error.tsx           — Global error boundary
│   ├── loading.tsx         — Global loading UI
│   ├── globals.css         — Design tokens + primitives (panel, trust-badge, glow, etc.)
│   ├── favicon.ico
│   ├── fonts/              — (static assets, not inspected — not relevant to layout work)
│   ├── dashboard/
│   │   └── page.tsx        — "/dashboard" Query history (localStorage-backed)
│   ├── market/
│   │   └── page.tsx        — "/market" Market Mode (closest existing analog to target workspace)
│   ├── metrics/
│   │   └── page.tsx        — "/metrics" Research/paper results page
│   └── og/
│       └── route.tsx       — OG image generation route (not a UI page)
├── components/              — 17 flat files, no subfolders (no atoms/molecules split)
├── lib/
│   ├── api.ts              — FastAPI client (query/verify/market/fundamentals/earnings/history/websocket)
│   ├── market.ts            — Direct-from-browser Finnhub client (quotes + basic financials)
│   ├── dvl.ts               — Client-side DVL fallback (for MetricPanel)
│   ├── history.ts            — localStorage query-history persistence
│   └── connection.tsx        — ConnectionProvider (React Context) — backend health polling
├── middleware.ts             — Pass-through (Clerk stripped)
├── next.config.mjs           — Empty/default
├── tailwind.config.ts        — Design tokens (t-bg, t-green, t-amber, etc.)
├── public/widget.js          — Embeddable widget script (separate concern, not part of workspace)
└── package.json
```

No `hooks/`, `contexts/`, `providers/`, `styles/`, `utils/`, `assets/` directories exist. Everything client-fetching lives inline in components via `useEffect`, or in `lib/`.

### 2.3 Route / Layout Tree

```
RootLayout (app/layout.tsx)
├── ConnectionProvider (lib/connection.tsx) — wraps everything, provides backendOnline/status/modelName
├── <header> — nav bar: logo, version, NavModeToggle (Terminal/Market pill switch), NavHealthIndicator, Dashboard link, Research link
├── <TickerBar /> — scrolling marquee, sits below header, above all page content
└── <main>{children}</main>
    ├── "/"          → app/page.tsx           (Terminal — DVL query demo)
    ├── "/market"     → app/market/page.tsx    (Market Mode)
    ├── "/dashboard"  → app/dashboard/page.tsx (Query history)
    ├── "/metrics"    → app/metrics/page.tsx   (Research/paper page)
    └── "/og"         → app/og/route.tsx       (image route, not a page)
```

There is **no nested layout system** — one flat root layout, no route groups, no parallel/intercepting routes. `error.tsx` and `loading.tsx` are global (root-level), not per-route. Navigation is plain `<a>` tags (not `next/link`), which means every nav click is a full page reload — worth fixing when the workspace is built (should use `next/link` for the new nav, especially if the workspace becomes a single persistent shell).

**Important for the new workspace:** since there's no shared layout with persistent panels below the root, and the target Workspace vision calls for a *persistent 3-column shell with a bottom bar that's always present*, the new workspace should likely become its **own top-level route** (e.g. `/workspace` or replace `/` entirely) with its own internal layout — not attempt to bolt onto the existing `page.tsx` structure.

---

## 3. Component Tree (per page)

### 3.1 `/` Terminal (`app/page.tsx`)
```
HomePage
├── HeroNetwork (animated SVG world-map hero background)
├── Capabilities strip (3 static info cards — DVL/SEC/Earnings, inline JSX, not componentized)
└── 3-column grid [32% / 42% / 26%]
    ├── QueryInput           (left)
    ├── Center stack (scrollable, top-to-bottom):
    │   ├── AdvisoryState        (conditional — shown when query is an advisory/investment question)
    │   ├── QueryInterpretation  (conditional — shown when a result exists)
    │   ├── DVLExplainer         (conditional — empty-state education panel)
    │   ├── TerminalPanel        (raw LLM output display)
    │   ├── VerificationLog      (DVL correction pipeline log + animated pipeline stages)
    │   ├── TrustScore           (verified output + trust badge + correction pipeline viz)
    │   ├── DVLReport            (PDF export button, conditional on history.length > 0)
    │   ├── error banner         (conditional, inline JSX)
    │   └── Failure-case toggle  (inline JSX, collapsible "reasoning error" example)
    └── Right: Tabbed panel (session / errors / stats) — inline JSX, not componentized
```

### 3.2 `/market` Market Mode (`app/market/page.tsx`)
```
MarketPage
├── Demo-mode banner (conditional, inline)
├── Symbol quick-select tabs + center-panel toggle (inline)
└── 3-column grid [25% / 50% / 25%]
    ├── Watchlist          (left — live/demo quotes + sparklines, click to select symbol)
    ├── Center (tab-toggled):
    │   ├── MetricPanel          (tab: "metrics" — 2×2 DVL-verified metric cards)
    │   └── EarningsVerification (tab: "earnings" — SEC fundamentals + red-flag claim list) [DEFAULT TAB]
    └── MarketContext       (right — indices + static sector bars + DVL engine status box)
```

### 3.3 `/dashboard` (`app/dashboard/page.tsx`)
```
DashboardPage
├── StatsRow       (inline component in same file — total/high/med/low/fixes counts)
├── Filter tabs (ALL/HIGH/MEDIUM/LOW, inline)
└── History list
    └── HistoryRow[]  (inline component — expandable, shows correction log, re-run button)
```

### 3.4 `/metrics` (`app/metrics/page.tsx`)
```
MetricsPage
├── Key-result banner (inline)
├── Header + links (HuggingFace, GitHub) (inline)
├── StatCard[] (inline component, animated counters via IntersectionObserver)
├── AblationSection   (ablation table × 2 + bar chart)
├── ErrorTaxonomy      (donut chart + breakdown list)
├── Robustness table (inline)
└── "How it works" 3-card grid (inline)
```

---

## 4. Terminal Architecture (Query Lifecycle — `/` page)

This is the most complex piece of client logic in the app and the part most worth preserving functionally even as the UI around it changes.

**Query lifecycle (`handleSubmit` in `app/page.tsx`):**
1. Advisory-query detection: `isAdvisoryQuery()` checks the question against a keyword list (`"should i"`, `"recommend"`, `"invest in"`, etc.). If matched, sets `advisoryDetected` and renders `AdvisoryState` instead of running verification.
2. Pipeline stage simulation: `advancePipeline()` sequentially sets `pipelineStage` through `compile → resolve → retrieve → math → trust → verified`, each with a ~130ms artificial delay and a `logEvent()` call (feeds the right-column "session" tab). This stage machine is purely cosmetic/simulated timing — it does not reflect real backend timing.
3. Routing logic for the actual data call:
   - If the question exactly matches one of 6 hardcoded `DEMO_NUMS` questions → call `/verify` (DVL-only, fast, no LLM cold start) if `backendOnline`, else fall back to the client-side `clientDVL()` (defined inline in `page.tsx`, **duplicated** with different feature-completeness in `lib/dvl.ts`).
   - Else if `backendOnline` → call `/query` (full LLM + DVL pipeline via `queryLLM()`), showing a "cold start" loading message. Handles a special backend response shape (`mode: "dvl_only", trust_score: "N/A"`) meaning the LLM inference token isn't configured server-side.
   - Else (backend offline, custom question) → clean error, no fake result.
4. On success: pushes to `history` (capped at 20), updates `result`, calls `addToHistory()` (persists to `localStorage`, shared with `/dashboard`).

**Demo mode (`handleRunDemo`):** a parallel code path for the 6 fixed `DEMO_CASES`, using the same pipeline-stage animation but a separate `demoStatus` state machine.

**State flow:** all local `useState` in `page.tsx` — no context, no external store. `result`, `history`, `pipelineStage`, `sessionEvents` (capped at 40), `rightTab` are the key pieces of state that downstream components consume as props.

**No streaming, no WebSocket** on this page — every result is a single fetch/await. WebSocket usage exists only in Market Mode indirectly (`lib/api.ts` exports `createMarketWebSocket()` for `/ws/market`, but **it is not actually used by any component today** — `TickerBar`, `Watchlist`, `MarketContext`, `MetricPanel` all poll via `setInterval` + fetch instead of using the WebSocket helper). This is a gap: the backend WebSocket exists and works, but the frontend doesn't consume it yet — Milestone 2 of the target spec (`useWorkspaceStream`) should wire the frontend up to this existing endpoint rather than building a new one.

**Keyboard shortcuts:** `QueryInput.tsx` handles `Enter` (submit), `Cmd/Ctrl+Enter` (submit), and a window-level `Escape` listener to clear the textarea. No other global shortcuts exist (the target spec's `Ctrl+F`/`Ctrl+K` are net-new).

**Client-side DVL fallback — duplication warning:** there are **three** separate implementations of the DVL scale/sign/magnitude correction logic in the frontend:
1. `clientDVL()` inline in `app/page.tsx` (most complete — includes a documented comment on its known drift vs. backend).
2. `lib/dvl.ts`'s `clientDVL()` (used only by `MetricPanel.tsx`; simpler, no sign/magnitude correction, only scale).
3. The real backend `finverify-terminal/backend/app/dvl.py` (out of scope for this frontend report, but is the source of truth).

Any new workspace code that needs client-side verification should **consolidate on one shared client DVL module** rather than adding a fourth copy — this was flagged previously as a known issue and is still present.

---

## 5. Design System Audit

### 5.1 Typography
- Font: JetBrains Mono everywhere (`@fontsource/jetbrains-mono`, weights 400/500/600/700), imported in `globals.css`.
- No serif/sans fallback UI — this is a monospace-only terminal aesthetic throughout, matching the Bloomberg-style target.
- Text sizes are all Tailwind arbitrary values (`text-[9px]`, `text-[10px]`, `text-[11px]`, `text-[12px]`) — very information-dense, small type. This already matches the target spec's "tight spacing, small typography" requirement.

### 5.2 Color Tokens (`tailwind.config.ts`)
```
t-bg: #0a0a0a           t-green:  #00ff88   (positive / HIGH trust / online)
t-surface: #111111      t-amber:  #fbbf24   (warning / MEDIUM trust / corrections)
t-border: #1e1e1e       t-red:    #f87171   (negative / LOW trust / errors)
t-border-accent: #2a2a2a  t-blue: #60a5fa   (info accent)
t-primary: #e0e0e0      t-cyan:   #22d3ee   (secondary accent, links)
t-secondary: #888888    t-purple: #a78bfa   (tertiary accent)
t-muted: #444444
```
This palette already maps directly onto the target spec's semantic needs (integrity/trust color coding, up/down market colors). No new palette is needed for the workspace — reuse these tokens.

### 5.3 Reusable CSS Primitives (`globals.css`)
- `.panel` / `.panel-header` — the base card + header pattern used by literally every box in the app. **This is the primitive the new workspace's panels should be built on.**
- `.label` — bold uppercase panel-header text.
- `.status-dot` (+ `.amber`/`.red` modifiers) — small colored dot, used for live/loading indicators.
- `.trust-badge` (+ `.trust-high`/`.trust-medium`/`.trust-low`) — the HIGH/MEDIUM/LOW pill, reused across Terminal, Market, Dashboard.
- `.glow-green`/`.glow-amber`/`.glow-red` — box-shadow glow modifiers keyed to trust/direction.
- `.scanline` — CRT-style repeating-gradient overlay (used on TerminalPanel, VerificationLog).
- `.count-animate`, `.verified-flash`, `.trust-badge-animate`, `.live-pulse` — small entrance/attention animations.
- `.ticker-scroll` / `.ticker-viewport` — marquee scroll mechanics for TickerBar.
- `.hero-*` — HeroNetwork-specific SVG styling (not reusable outside the hero).
- `prefers-reduced-motion` handling is already in place globally — must be preserved in any new animated panels.

### 5.4 Spacing / Borders / Density
- Panels use `border border-t-border rounded (4px)` — thin 1px borders, minimal border radius, consistent with Bloomberg/terminal aesthetics.
- Grid layouts use percentage-based Tailwind arbitrary column templates (e.g. `lg:grid-cols-[32%_42%_26%]`, `lg:grid-cols-[25%_50%_25%]`) rather than `fr` units — the target spec's 3-column layout should follow this same pattern for consistency, but note both existing pages use *different* ratios (32/42/26 vs 25/50/25) — the new workspace should pick one canonical ratio (spec implies roughly 25/50/25).

### 5.5 Icons
No icon library is used anywhere (`lucide-react` etc. is NOT a current dependency, despite being available in the sandboxed artifact environment). All "icons" today are Unicode glyphs/emoji used inline (▲▼●■🚩📡🔍⏎🔎📊⚠). The target spec's mockup uses similar Unicode glyphs, so this is consistent — no icon library needs to be introduced, but if one is desired for polish, none currently exists.

### 5.6 Charts
`recharts` is the only charting library in use: `LineChart` (sparklines), `BarChart` (ablation, error progression), `PieChart` (error taxonomy donut). All chart color values are hardcoded hex per-datapoint rather than pulling from Tailwind tokens — acceptable pattern to continue, but be consistent (use the same t-green/t-amber/t-red hex values: `#00ff88`, `#fbbf24`, `#f87171`).

### 5.7 Tables
Two ad hoc HTML `<table>` implementations exist (Dashboard has none; `metrics/page.tsx`'s Robustness table and `AblationSection`'s two tables) — same Tailwind styling pattern each time (`text-t-muted border-b border-t-border` headers, alternating row backgrounds). No shared `<Table>` component exists — worth extracting if the workspace needs more tables (e.g. Filing Radar, News Radar could be table-like).

---

## 6. State & Data Flow

### 6.1 Global State
- **`ConnectionProvider`** (`lib/connection.tsx`) is the only app-wide React Context. Polls `GET /health` every 30s, exposes `{ status, backendOnline, modelName, refresh }`. Consumed by `page.tsx` (routing logic) and `NavHealthIndicator`.
- No Redux/Zustand/Jotai — and given the app's size, none is currently necessary. **If the new workspace introduces WebSocket-driven live data shared across many panels (Market Pulse, Intelligence Feed, Verification Radar, etc. all updating from one stream), a new shared context (e.g. `WorkspaceStreamProvider`) analogous to `ConnectionProvider` is the natural pattern to extend, not a new state library.**

### 6.2 Local State
Every page/component manages its own `useState` for its own data (quotes, metrics, reports, UI toggles). This is consistent throughout — no prop-drilling problems currently exist because pages are shallow (2-3 levels deep max).

### 6.3 Persistence
- `lib/history.ts`: `localStorage` key `finverify_query_history`, capped at 100 entries, shared between `/` (write) and `/dashboard` (read/write/clear).
- `lib/api.ts` also defines a **Supabase-backed** history API (`saveToHistory`, `getHistory`, `clearHistoryRemote` hitting `/v1/history/*`) — but **no component in the frontend currently calls these** (confirmed: `saveToHistory`/`getHistory`/`clearHistoryRemote` are unused exports). LocalStorage is the only history mechanism actually wired up today. This is presumably a partially-built feature — worth flagging as dead/unused code below, but also as a potential shortcut: if the workspace needs persistent per-user state (saved workspaces, watchlists), the Supabase history endpoints already exist server-side and could be repurposed.

### 6.4 API Client Layer (`lib/api.ts`)
Fully typed fetch wrappers, no SDK/codegen. Base URL: `NEXT_PUBLIC_API_URL` env var, defaults to the HF Spaces-hosted backend. Endpoints currently used by some component in the frontend:
| Endpoint | Used by |
|---|---|
| `POST /query` | `page.tsx` (LLM+DVL) |
| `POST /verify` | `page.tsx`, `dashboard/page.tsx` (DVL-only) |
| `GET /health` | `lib/connection.tsx` |
| `GET /market/quotes` | *(exported, not called anywhere currently)* |
| `GET /market/indices` | `MarketContext.tsx` |
| `GET /market/all-metrics` | *(exported, not called — MetricPanel uses Finnhub client + client DVL instead)* |
| `GET /v1/fundamentals/{ticker}` | `EarningsVerification.tsx` |
| `GET /v1/earnings/{ticker}` | `EarningsVerification.tsx` |
| `createMarketWebSocket()` (`/ws/market`) | *(exported, not called anywhere)* |
| `saveToHistory`/`getHistory`/`clearHistoryRemote` (`/v1/history/*`) | *(exported, not called anywhere — localStorage used instead)* |

### 6.5 Direct-to-third-party client
`lib/market.ts` calls Finnhub directly from the browser (`NEXT_PUBLIC_FINNHUB_KEY`), bypassing the backend entirely for quotes/basic-financials. This is a **parallel, redundant path** to the backend's own `/market/quotes` and `/market/all-metrics` endpoints (which presumably also call Finnhub server-side, judging by naming — not confirmed since backend wasn't in scope of this frontend audit, but should be verified before the workspace rebuild, since running both a client-side and server-side Finnhub integration risks double the rate-limit consumption against the same 60/min free-tier key).

### 6.6 Authentication
None currently — fully public, Clerk stripped. `middleware.ts` is a no-op pass-through. Any per-user features in the new workspace (saved workspaces, personal watchlists) would need either (a) re-introducing auth, or (b) continuing the localStorage-only pattern.

### 6.7 Loading / Error Handling
- Global: `app/loading.tsx` (route-level Suspense fallback), `app/error.tsx` (route-level error boundary with retry button).
- Per-component: every data-fetching component has its own inline loading/error/fallback-data handling (e.g. `MarketContext` shows fallback data immediately and never has a stuck loading state — a good pattern to keep). No shared `<Skeleton>` component exists; loading states are ad hoc text/pulse animations per component.

---

## 7. Reusable Components (carry into the new workspace)

| Component | Reuse in new workspace as... |
|---|---|
| `.panel`/`.panel-header` CSS primitives | Base for every workspace panel (Market Pulse, Watchlist, Opportunity Scanner, Focus View, News, Filings, Earnings, Sector Monitor, Intelligence Feed) |
| `TrustScore.tsx` trust-badge + tooltip pattern | Directly informs the Integrity Score panel's badge/tooltip UX |
| `EarningsVerification.tsx` (whole component) | Closest existing analog to "Verification Radar" — red-flag report, trust breakdown bar, claim expand/collapse — **should be adapted, not rebuilt from scratch** |
| `MetricPanel.tsx` (whole component) | Closest existing analog to a company drill-down "Financials" panel |
| `Watchlist.tsx` | Directly reusable for the Left-column Watchlist panel; sparkline mechanism needs to move from synthetic-random to real historical data eventually |
| `MarketContext.tsx` (indices portion) | Directly reusable for the Left-column Market Pulse panel; sector bars need real data source |
| `TickerBar.tsx` | Could remain as the top strip, or be retired if Market Pulse panel subsumes it |
| `VerificationLog.tsx` pipeline-stage visualization | Reusable pattern for showing "why is this flagged" reasoning inside the Focus View's Verification Radar |
| `NavHealthIndicator.tsx` / `ConnectionProvider` | Reusable as-is for a workspace-wide "backend online" indicator (top bar green dot in the target mockup) |
| `DVLReport.tsx` (PDF export) | Reusable as-is, can be offered from the workspace's Focus View or history |
| `QueryInput.tsx`'s textarea + keyboard-shortcut handling | Base for the persistent bottom Query Input bar in the target layout (needs re-skinning from a tall left-column box into a slim bottom bar, and `Ctrl+F` global-focus shortcut added) |
| `StatCard`/`AnimatedCounter` (inline in `metrics/page.tsx`) | Worth extracting into a shared component — useful for "Quick Stats" in the default Focus View |
| `AblationSection.tsx`/`ErrorTaxonomy.tsx` chart patterns | Reusable chart-panel patterns (bar/donut with custom tooltip) for Sector Monitor / Financial Health Timeline |

---

## 8. Dead Code / Unused Exports (report only — do not delete without confirming)

- **`components/MetricsChart.tsx`** — entirely unused. Not imported anywhere. Duplicates (with different, inconsistent numbers) the charts in `AblationSection.tsx` and `ErrorTaxonomy.tsx`, which are the ones actually rendered on `/metrics`.
- **`lib/api.ts`: `getMarketQuotes()`, `getAllMetrics()`, `getVerifiedMetric()`, `createMarketWebSocket()`, `saveToHistory()`, `getHistory()`, `clearHistoryRemote()`** — all exported, none currently called by any component.
- **`@clerk/nextjs`, `@clerk/themes`** in `package.json` — auth fully removed from the app; these are dead dependencies.
- **Two duplicate `clientDVL()` implementations** (`app/page.tsx` inline vs `lib/dvl.ts`) — not "dead" (both are used) but duplicated logic that has already drifted (documented in a code comment in `page.tsx`) and should be consolidated during the rebuild.
- **`public/widget.js`** — an embeddable widget script, unrelated to the main app UI; out of scope for the workspace but noted for completeness.

---

## 9. Risks & Recommendations

**Risks**
1. **Layout collision**: the target workspace's fixed `h-screen`, no-page-scroll, independently-scrolling-panel layout is a different structural pattern than either existing page (`/` scrolls the whole page including a large hero section; `/market` is closer but still has a symbol-tab header above the grid rather than being fully edge-to-edge). Building the workspace as a modification of `page.tsx` risks fighting the existing hero/capabilities sections. **Recommendation: build the workspace as a new route with its own dedicated layout**, reusing the design tokens/CSS primitives but not the page-level JSX structure of either existing route.
2. **Rate-limit double-spend**: both the backend (presumably) and the frontend (`lib/market.ts`) call Finnhub directly with what may be the same key. Before building the WebSocket-driven Market Pulse panel (Milestone 2), confirm whether backend `/market/quotes` and frontend `lib/market.ts` are hitting Finnhub redundantly, and consolidate to one path (server-side, streamed over the existing `/ws/market`) to stay under 60 req/min.
3. **Synthetic-data panels look real**: sparklines and sector bars are fake data with no visual "this is illustrative" marking. The target spec's principle ("if you remove FinVerify's verification, is this just a generic widget?") implies these should either get real data sources or be visually marked as directional/illustrative — silently shipping more synthetic-looking panels (Trust Heatmap, Financial Health Timeline) risks compounding a known issue.
4. **`<a>` tags instead of `next/link`**: all navigation is full-page reload. If the workspace is meant to feel like "professional software you keep open all day" (per the target spec), client-side navigation between Focus View states must not reload the whole page — this should use React state (as `market/page.tsx`'s `selectedSymbol`/`centerTab` already does for its within-page switching) rather than route navigation, for the Dynamic Focus View in particular.

**Recommendations for implementation order**
1. Stand up the new workspace route + layout shell first (empty panels, `.panel` primitives, 3-column + bottom-bar grid) — matches target spec's Milestone 1.
2. Port `Watchlist`, `MarketContext` (indices half), and `TickerBar`'s data-fetching logic into the new Market Pulse / Left column panels, swapping polling for the existing (unused) `createMarketWebSocket()`/`/ws/market` connection — this both satisfies Milestone 2 and fixes the redundant-Finnhub-call risk in one move.
3. Adapt `EarningsVerification.tsx` into the Verification Radar and `MetricPanel.tsx` into the Financials portion of the Dynamic Focus View, rather than writing these from scratch — both already implement most of the required interaction pattern (expand/collapse claim rows, trust breakdown bar, correction log).
4. Build genuinely new proprietary panels (Integrity Score composite, Opportunity Scanner, Trust Heatmap, Financial Health Timeline) last, since they have no existing analog and need real backend support (the composite Integrity Score formula in the spec — Consistency 40% + SEC agreement 30% + DVL confidence 30% — does not exist anywhere in the current frontend or (as far as this audit could tell without a backend-focused pass) the backend; this is genuinely new work, not a port).
