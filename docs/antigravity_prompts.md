# FinVerify Terminal — Antigravity Implementation Prompts

Four standalone prompts. Each is meant to be pasted into a **fresh Antigravity session** together with that page's CURRENT screenshot and TARGET screenshot. Execute one at a time: Workspace → review → Verify → review → Market → review → Research.

---
---

# PROMPT 1 — WORKSPACE

## 1. ROLE

You are the implementation engineer for FinVerify Terminal. The UX architecture and repository audit for this page have already been completed by a separate review process — you do not need to perform another broad architecture investigation. Do not redesign the page's information architecture. Do not second-guess the component boundaries below. Inspect only the specific files listed in Section 3 before you modify them (open and read each one fully before editing). The TARGET screenshot you've been given is the visual source of truth for hierarchy, density, and aesthetic. The CURRENT screenshot shows today's shipped state. Your job is to transform CURRENT → TARGET while preserving every piece of currently-working functionality listed in Section 13. If the screenshot and this specification disagree about a data value or functional behavior, **this specification wins** — never hardcode a screenshot's displayed number if this document tells you that data doesn't exist yet.

## 2. PRODUCT PURPOSE OF THIS PAGE

Workspace is the default landing surface. Its job is to answer, at a glance: **"What's happening?"** — across markets, filings, and FinVerify's own verification activity — before the user decides whether to dig into a specific claim (Verify) or a specific company (Market). Every panel on this page exists to make the system feel monitored and alive, not to be decorative. The center map is explicitly instructed by the product owner to remain the visual hero — do not shrink its prominence or replace its rendering approach.

## 3. EXACT CURRENT REPOSITORY STRUCTURE

Stack: Next.js 14.2 App Router, React 18, TypeScript, Tailwind. No Redux/Zustand — plain `useState`/`useEffect`/React Context. Design tokens live in `tailwind.config.ts` (`t-bg`, `t-green`, `t-amber`, `t-red`, `t-cyan`, `t-purple`, `t-blue`, `t-muted`, `t-border`, `t-secondary`, `t-primary`) and `app/globals.css` (`.panel`, `.panel-header`, `.trust-badge`, `.label`, `.glow-green`, `.glow-red` primitives). Navigation currently uses plain `<a>` tags, not `next/link` (full page reloads today — this is a known issue, not something to silently "fix" as a side effect unless Section 17 tells you to).

**Route:** `/workspace` → `app/workspace/page.tsx`, wrapped by `app/workspace/layout.tsx` (currently a pass-through that inherits the root layout's header — do not add a second header here).

**Root shell (shared across all pages, touch only if Section 17 applies):**
- `app/layout.tsx` — root layout: header with logo, `v1.2` version tag, `NavModeToggle` (currently a 2-way TERMINAL/MARKET pill), `NavHealthIndicator`, and separate WORKSPACE/DASHBOARD/RESEARCH text links. `TickerBar` renders below the header. `ConnectionProvider` wraps everything (`lib/connection.tsx`).

**Workspace-specific components (all in `components/workspace/`):**
- `WorkspaceTopBar.tsx` (55 lines) — top strip inside the workspace page itself, distinct from the root header.
- `MarketAlertBanner.tsx` (49 lines) — the scrolling market-alert ticker line under the header (currently 100% hardcoded news-style strings).
- `MarketPulsePanel.tsx` (129 lines) — top-left mini index chart (SPX/NDX/VIX) with a synthetic sparkline background (`Math.random()`-seeded) and a `FALLBACK_INDICES` constant used when live fetch fails.
- `WatchlistPanel.tsx` (167 lines) — left column watchlist. Imports `getAllQuotes`/`isFinnhubConfigured` from `lib/market.ts` (client-side Finnhub, gated on `NEXT_PUBLIC_FINNHUB_KEY`). Contains its own `FALLBACK_QUOTES` array (hardcoded prices, e.g. AAPL $333.43) shown with a small "DEMO" badge when Finnhub isn't configured. Contains `generateSparkline()` — a `Math.random()` random-walk generator seeded from the real current price, used purely for the sparkline shape.
- `GlobalTransactionMonitor.tsx` (365 lines) — the center map. Contains hardcoded `CITIES` (10 city nodes with fixed x/y/volume/changePct), hardcoded `ARCS` (9 fixed connections with fixed flow-type colors), a hardcoded `SECTORS` filter-tab list, an SVG `WORLD_PATH` low-poly world outline, and — importantly — **also contains the workspace's bottom command-bar query logic**: `KNOWN_TICKERS`, `RATIO_KW`, `DEMO_NUMS`, and a `quickDVL()` function that is an independent, simplified, client-side reimplementation of the DVL scale-correction rule (separate from both the real backend engine and from `lib/dvl.ts`'s client-side fallback). This file is large and does double duty (map rendering + command input logic) — read it fully before touching either part.
- `IntegrityMonitorPanel.tsx` (110 lines) — right-of-map-ish panel, currently a fully hardcoded `DEMO_DATA` array of 5 companies with fixed flag counts (INTC 4, TSLA 3, COIN 2, NVDA 1, AAPL 0), rendered as horizontal severity bars.
- `RightColumnPanels.tsx` (176 lines) — contains four sub-panels in one file: News Radar (`const items = [...]`, fully static), Filing Radar (fully static), Earnings Calendar (fully static), Sector Monitor (`const SECTORS = [...]`, fully static, duplicated from a similarly-named constant elsewhere in the codebase).
- `WorkspaceBottomBar.tsx` (100 lines) — the bottom command input bar with quick-action chips ("Analyze AAPL 10-Q", "Verify TSLA revenue claim", etc.). Also contains its own `Math.random()`-based value generation for one of its display elements — read the file to find and understand this before modifying.
- `FocusView.tsx` (357 lines) — the detail panel shown when a watchlist symbol is clicked (referenced in `RightColumnPanels`/`WatchlistPanel` selection flow). Contains `DEMO_INTEGRITY` (hardcoded per-symbol integrity score fallback) and `demoFilings` (hardcoded filing list fallback), each with visible "DEMO" / "DEMO DATA" labels already present in the JSX.

**Shared library files relevant to this page:**
- `lib/api.ts` — typed client for the real FastAPI backend (`/market/quotes`, `/market/indices`, `/market/all-metrics`, `/v1/verify`, etc.). This is the **server-side, no-API-key-required** path (backend uses `yfinance` internally).
- `lib/market.ts` — a **separate, parallel** client that calls Finnhub directly from the browser, gated on `NEXT_PUBLIC_FINNHUB_KEY`. `WatchlistPanel.tsx`, `TickerBar.tsx`, and `MetricPanel.tsx` (Market page) currently use this one instead of `lib/api.ts`. **This split is the root cause of a live, currently-observable bug**: the same ticker (e.g. AAPL) shows a different price on the Workspace watchlist than on the Market page and homepage ticker, because one path is live-Finnhub-or-static-fallback and the other is live-yfinance-or-a-different-static-fallback. Do not perpetuate this split when building new Workspace panels — any new panel you build should pull through `lib/api.ts`, not `lib/market.ts`. (Fully unifying the two existing components onto one client is in-scope for this pass if it's low-risk; if it feels risky, leave the existing components as-is but do NOT introduce a third parallel data path.)
- `lib/history.ts` — `localStorage`-backed query history (`loadHistory()`, `saveHistoryLocal()`, `HistoryEntry` type with `question`, `raw_number`, `verified_number`, `trust_score`, `trust_color`, `correction_log`, `timestamp`). This is real, but scoped to the current browser only — there is no server-side aggregate across sessions or users.
- `lib/connection.tsx` — `ConnectionProvider`/`useConnection()`, real backend-health polling, exposes `status: "online" | "degraded" | "checking"` and `modelName`. This is the one place in the app that already implements an honest live/degraded pattern — use it as your model for Section 8/9's data-truth states, don't reinvent a different pattern.
- `lib/dvl.ts` — `clientDVL()`, a real (if simplified) TypeScript port of the scale-correction rule, used as a fallback when the backend is unreachable. Already correctly labeled "DEGRADED — using client-side DVL" via `NavHealthIndicator`.

**Backend (do not modify, but you need to know what exists — file: `finverify-terminal/backend/app/main.py`, ~620 lines):**
- `POST /v1/verify` — the real verification pipeline. Response includes `claim`, `evidence` (list), `calculations` (list), `correction_log`, `trust_score` as first-class fields — this is the shape any "verification event" panel should eventually consume.
- `GET /market/quotes`, `GET /market/indices` — real, `yfinance`-backed, 10-second in-memory cache per symbol.
- `GET /market/all-metrics?symbol=X` — real, runs derived ratios through the actual `verify()` engine, returns `trust_score`/`trust_color` per metric. Returns `raw_value: null` / `trust_score: "N/A"` silently when `yfinance` has no data for that field — there is currently no user-facing explanation for this null state anywhere in the frontend.
- **No endpoint exists for**: cross-session/cross-user aggregate verification counts, a "numerical anomalies" or "high severity flags" concept, real news, real earnings-calendar data, or real institutional transaction-flow-between-cities data. Do not invent client-side computations that produce numbers resembling these.
- SEC EDGAR evidence provider exists (`providers/sec.py`) and is real, but is currently only wired into the `/v1/verify` evidence-retrieval step — it is NOT wired into the Filing Radar widget's data source today.

**Files that should probably NOT need modification for this page:** `app/page.tsx` (Verify/Terminal — separate prompt), `app/market/page.tsx`, `app/metrics/page.tsx`, `app/dashboard/page.tsx`, backend `main.py`/`market.py`/`core/*` (any backend change must be flagged per Section 22, not silently made), `lib/dvl.ts` (reuse, don't modify).

## 4. CURRENT → TARGET COMPONENT MAPPING

| CURRENT COMPONENT | TARGET REGION | ACTION | NOTES |
|---|---|---|---|
| `MarketPulsePanel.tsx` | Top-left "MARKET PULSE" mini chart | KEEP + RESTYLE | Keep live-fetch-with-fallback logic; only restyle to match target's tab row (1D/1W/1M/YTD/1Y) if not already present — check current file first, this may already exist |
| `WatchlistPanel.tsx` | Left column "WATCHLIST" | EXTEND | Add a new "VERIF. STATUS" shield-icon column per row (green shield = verified/high trust, amber = medium, red = conflicting, grey = no data). Do not change the existing price-fetch logic. |
| `IntegrityMonitorPanel.tsx` | Left column "INTEGRITY MONITOR" | REFACTOR | Target reformats this from a per-company severity-bar list into a compact 4-stat summary card ("Claims Monitored", "Numerical Anomalies", "High Severity", "Data Sources Active"). Per Section 9, these 4 stats have no real backend source today — build the new visual shape but populate it with an explicit DEMO state, not invented numbers. |
| `GlobalTransactionMonitor.tsx` (map/SVG/cities/arcs portion only) | Center hero map | KEEP + RESTYLE | Do not replace the SVG rendering approach or remove the map. Only restyle chrome (legend, stat readout styling, filter tabs) to match target's visual treatment. The `CITIES`/`ARCS` hardcoded data itself stays as explicitly-labeled DEMO per Section 16 — this was a deliberate prior decision (see Section 9), not something to "fix" by inventing real institutional flow data. |
| `GlobalTransactionMonitor.tsx` (command-input / `quickDVL` portion) | Bottom command bar | SEPARATE — do not touch here | This logic actually belongs conceptually with `WorkspaceBottomBar.tsx`. Do not refactor/move it in this pass unless it's trivial; if you do touch it, keep `quickDVL`'s behavior identical, only note the duplication in your final report. |
| `RightColumnPanels.tsx` → News Radar sub-panel | Right column "NEWS RADAR" | KEEP AS DEMO, ADD LABEL | No real news source exists. Keep the static content but add a persistent, clearly-visible "DEMO" status pill in the panel header (not a tiny corner tag) per Section 8. |
| `RightColumnPanels.tsx` → Filing Radar sub-panel | Right column "FILING RADAR" | EXTEND (real data available) | This is the one right-column panel with a real backend path available: `providers/sec.py`. If a simple way exists to fetch recent filings for watchlist symbols via the existing `/v1/verify` evidence machinery or an existing endpoint, wire it; otherwise, build the component to accept real data via a typed prop and render an honest "BACKEND PENDING" state — do NOT invent a new backend endpoint yourself (flag to Section 22 if one is needed). |
| `RightColumnPanels.tsx` → Earnings Calendar sub-panel | Right column "EARNINGS CALENDAR" | KEEP AS DEMO, ADD LABEL | No backend source exists at all for this. Same treatment as News Radar. |
| `RightColumnPanels.tsx` → Sector Monitor sub-panel | Right column "SECTOR MONITOR" | KEEP AS DEMO for now | No live sector-performance endpoint exists yet. Add DEMO label. Do not compute a fake average client-side. |
| `WorkspaceBottomBar.tsx` | Bottom command bar | KEEP + RESTYLE | Preserve the quick-action chips and command-input behavior; only restyle to match target's visual weight/placement. Fix the one `Math.random()`-based display value you find in this file only if it's trivial and isolated — otherwise flag it, don't silently leave a fake number unlabeled if you notice it and don't fix it. |
| *(none exists today)* | "VERIFICATION PULSE" full-width stat row (Claims Checked / Verified / Corrected / Conflicts / Unresolved) | CREATE | New component: `VerificationPulsePanel.tsx`. See Section 14. No real cross-session aggregate exists — build as session-scoped or explicit DEMO, per Section 9. |
| *(none exists today)* | "RECENT VERIFICATION ACTIVITY" panel | CREATE | New component: `RecentActivityPanel.tsx`. Real, session-scoped, sourced from `lib/history.ts`. |
| *(none exists today)* | "NEEDS ATTENTION" panel | CREATE | New component: `NeedsAttentionPanel.tsx`. Real, session-scoped — filter `lib/history.ts` entries where `trust_score` is `MEDIUM` or `LOW`. |
| *(none exists today)* | "VERIFICATION COVERAGE" (per-company table: Verified/Corrected/Conflicted/Trust) | CREATE (DEMO only) | New component: `VerificationCoveragePanel.tsx`. No backend aggregation exists for this at all — no per-company historical rollup. Build the visual shape, populate with an explicit "no data available yet" / DEMO state. Do not fabricate a table of numbers. |
| *(none exists today)* | "LIVE VERIFICATION TRACE" full-width strip | CREATE | New component: `LiveVerificationTracePanel.tsx`. This is the highest-value new panel — the backend's `/v1/verify` response already contains everything needed (`claim`, `evidence`, `calculations`, `correction_log`, `trust_score`). Populate this from the most recent entry in `lib/history.ts`/session state if no query has been run yet in this exact page load, show an empty/idle state rather than a fabricated example. |

## 5. PAGE LAYOUT BLUEPRINT

```
[ shared root header: logo | v1.3 | nav pill | health | WORKSPACE/VERIFY/MARKET/RESEARCH ]
[ TickerBar — scrolling price marquee ]
[ MarketAlertBanner — scrolling alert strip ]
-------------------------------------------------------------------------------
LEFT (≈20% width)      |         CENTER (≈55% width)          | RIGHT (≈25% width)
                        |                                       |
MARKET PULSE            |                                       | NEWS RADAR
(mini index chart)      |                                       |
------------------------|          GLOBAL TRANSACTION           |------------------
WATCHLIST                |          MONITOR (map hero)          | FILING RADAR
(scrollable list,        |          — dominant visual element   |
+ verif status col)      |          — do not shrink             |------------------
------------------------|                                       | EARNINGS CALENDAR
INTEGRITY MONITOR        |                                       |
(4-stat summary card)    |                                       |------------------
                        |                                       | SECTOR MONITOR
-------------------------------------------------------------------------------
FULL WIDTH: VERIFICATION PULSE (stat row: 5 stats side by side)
-------------------------------------------------------------------------------
3-COLUMN: RECENT ACTIVITY | NEEDS ATTENTION | VERIFICATION COVERAGE
-------------------------------------------------------------------------------
FULL WIDTH: LIVE VERIFICATION TRACE (horizontal 6-stage strip)
-------------------------------------------------------------------------------
BOTTOM (fixed/sticky): command input + quick-action chips + system status line
```

Notes on geometry:
- Left/Center/Right ratio above the fold should stay close to today's existing 3-column split (`GlobalTransactionMonitor` currently dominates center width) — don't rebalance it toward equal thirds.
- The map's height should remain the single tallest element above the fold.
- Below-fold new sections (Verification Pulse → Activity/Attention/Coverage → Live Trace) are full-width bands, stacked vertically, each in its own bordered panel — do not nest them inside the existing left/center/right columns.
- The right column's News/Filing/Earnings/Sector stack is tall and will likely need independent internal scroll (`overflow-y-auto` within a fixed-height container) rather than pushing overall page height — check current implementation to see if this already exists before adding it.
- Bottom command bar stays visually pinned/prominent at the bottom of the viewport-relevant content, matching current `WorkspaceBottomBar` placement — do not make it float/sticky if it currently isn't, unless the target screenshot clearly shows sticky behavior (it does not appear to).
- Borders: every panel uses a thin (1px) `t-border` colored border, square or minimally-rounded corners (check `.panel` class in `globals.css` for the exact existing radius — reuse it, don't introduce a new radius value).
- Whitespace: dense, terminal-style — small gaps between panels (check existing `gap-2`/`gap-3` Tailwind spacing already used in sibling components), not generous SaaS-dashboard whitespace.

## 6. VISUAL DESIGN SYSTEM

Institutional financial terminal, not consumer SaaS. Reuse the existing design system in `app/globals.css` and `tailwind.config.ts` — do not introduce a new color palette, new corner-radius scale, or a new font. Specifically:
- Background: near-black (`t-bg`), no gradients, no glassmorphism, no blur-behind-panel effects.
- Panel surfaces: flat, slightly-lighter-than-background fill, thin 1px border in `t-border`, minimal/no shadow. Use the existing `.panel`/`.panel-header` classes — extend them with modifiers if needed rather than writing new panel styles from scratch.
- Typography: monospace (`font-mono`) for all numeric data, labels, and status text — this is already the pattern in every existing component; keep it. Reserve any non-mono font (if one exists) only for the largest hero headline text, matching current homepage hero treatment.
- Numeric alignment: right-align all price/number columns, tabular-nums (`tabular-nums` Tailwind class already in use in `Watchlist.tsx`/`WatchlistPanel.tsx` — copy this pattern into new components).
- Density: small text sizes (10-12px range, matching existing `text-[10px]`/`text-[11px]`/`text-[12px]` utility patterns already used throughout), tight line-height, minimal padding (`p-2`/`p-3` range as already used).
- Corner radius: minimal — check `.panel` class's existing `rounded` value (likely a very small radius or none) and match it exactly in all new components. Do not introduce larger rounded-corner "cards."
- Status indicators: small colored dot (●) or shield/triangle icon + short uppercase label, exactly matching `NavHealthIndicator.tsx`'s existing pattern (colored dot + colored text label, e.g. "● LIVE").
- Dividers: thin 1px `t-border` lines, not thick section separators.
- Tables: monospace, right-aligned numerics, uppercase column headers in `t-muted`, hover-row highlight using a subtle background shift (check existing hover treatment in `WatchlistPanel.tsx`).
- Labels: uppercase, letter-spaced (`tracking-wider`/`tracking-widest` already used), small and muted unless it's a value being emphasized.
- Timestamps: small, muted, relative format ("12s ago", "2m", "1h") matching the pattern already visible in the current `MarketAlertBanner`/News items.
- Buttons: rectangular or minimally-rounded, bordered, uppercase mono text, matching existing "VIEW DEMO" / "EXECUTE" button treatment already in the Terminal page (`app/page.tsx`) — reuse that button styling.
- Scrollbars: thin, dark, unobtrusive — if a custom scrollbar style already exists in `globals.css`, reuse it.

Do NOT introduce: rounded pill-shaped mega-cards, drop shadows, gradient fills, glassmorphic blur panels, large friendly icons, generic dashboard color schemes (purple/blue SaaS gradients), oversized headline marketing copy, or bouncy/spring animations.

## 7. SEMANTIC COLOR RULES

Use exactly this mapping, consistent with existing `t-green`/`t-amber`/`t-red`/`t-cyan`/`t-blue`/`t-purple`/`t-muted` tokens already defined in `tailwind.config.ts`:
- **GREEN** (`t-green`) — verified, healthy, operational, LIVE status, positive price change, HIGH trust.
- **AMBER** (`t-amber`) — warning, uncertain, corrected-with-caveat, DEGRADED status, MEDIUM trust, DEMO badges (existing convention — check `WatchlistPanel.tsx`'s current "DEMO MODE" amber text).
- **RED** (`t-red`) — conflict, failed, HIGH severity, LOW trust, negative price change.
- **CYAN/BLUE** (`t-cyan`/`t-blue`) — informational, source/evidence references, selected state, "processing" state. Existing convention: Dashboard link uses cyan, Research link uses amber — check current header for the established per-section color convention and don't contradict it.
- **MUTED GREY** (`t-muted`) — secondary metadata, timestamps, inactive/disabled elements, UNAVAILABLE status.
- **PURPLE** (`t-purple`) — used in existing components for one specific accent (check `MarketContext.tsx`'s "MARKET CONTEXT" label color) — reuse consistently if you add a similarly-scoped label, don't introduce purple as a new general-purpose color.

Do not use color decoratively. Every color must map to a real state above. If you're tempted to pick a color "because it looks good" for a panel header, check whether that panel already has a header-color convention elsewhere in the codebase (e.g. News Radar = blue, Filing Radar = cyan per current `RightColumnPanels.tsx` — verify and preserve these exact existing per-panel accent colors rather than reassigning new ones).

## 8. DATA TRUTH RULES

Every data-driven panel on this page must expose one of these five states, and the UI must visually communicate which one is active — never render a number that looks live when it isn't:
- **LIVE** — successfully fetched within the current TTL window.
- **CACHED** — served from the backend's existing in-memory cache (`CACHE_TTL = 10` seconds in `market.py`), not this exact request.
- **DELAYED** — successfully fetched but older than ideal freshness (define a reasonable threshold, e.g. >60s since last successful fetch).
- **DEMO** — no real data path exists for this panel at all today (e.g. News Radar, Earnings Calendar, Sector Monitor, Verification Coverage, Integrity Monitor's 4-stat summary, map city/arc volumes).
- **UNAVAILABLE** — a real data path exists but this specific fetch failed (e.g. `yfinance` rate-limited, backend unreachable).

Use `lib/connection.tsx`'s existing `useConnection()` LIVE/DEGRADED pattern as your model — extend it, don't replace it, and don't invent a differently-named status system. Every panel's status badge should look visually consistent (same badge shape/position) across the whole page — build one small shared `<DataStatusBadge status={...} />` component (see Section 14) used everywhere rather than each panel inventing its own badge markup.

## 9. EXACT DATA FEASIBILITY

| Panel | Status | Existing API/field | Notes |
|---|---|---|---|
| Market Pulse (SPX/NDX/VIX) | REAL NOW (with fallback) | `lib/api.ts` → `GET /market/indices` | Keep existing fetch-with-fallback; add visible LIVE/UNAVAILABLE badge instead of silent fallback swap |
| Watchlist prices | REAL NOW (currently via wrong client) | Should be `lib/api.ts` → `GET /market/quotes`; currently uses `lib/market.ts` (Finnhub) | See Section 3 note on the two-client split |
| Watchlist verif-status column (NEW) | REAL NOW | `compute_financial_metric`'s `trust_score`/`trust_color`, exposed via `GET /market/all-metrics` | Fetch per-symbol trust alongside price |
| Integrity Monitor 4-stat summary | DEMO CURRENTLY | none | No "numerical anomalies"/"high severity" concept exists server-side. Render explicit DEMO state. |
| Global Transaction Monitor map (cities/arcs/volumes) | DEMO CURRENTLY | none | No institutional transaction-flow data source exists or is planned in near term. This is a known, accepted, previously-flagged limitation — keep as clearly-labeled DEMO, do not attempt to "fix" by inventing a new meaning for the map in this pass (that's a larger product decision outside this prompt's scope). |
| News Radar | DEMO CURRENTLY | none | No news integration exists. |
| Filing Radar | BACKEND PENDING | `providers/sec.py` exists and is real, but is not currently exposed as a simple "recent filings list" endpoint — only used internally during `/v1/verify` evidence retrieval | Build the component against a typed prop interface; if no simple existing endpoint surfaces this list, render BACKEND PENDING rather than inventing one yourself — flag it per Section 22. |
| Earnings Calendar | UNSUPPORTED | none found anywhere in the backend | Render DEMO/UNAVAILABLE, do not fabricate. |
| Sector Monitor | DEMO CURRENTLY | none (two separate hardcoded `SECTORS` constants exist in the codebase, never fetched) | Render DEMO. |
| Verification Pulse (Claims Checked/Verified/Corrected/Conflicts/Unresolved) | SESSION-SCOPED possible, no global aggregate | `lib/history.ts` (session-only) | No cross-session/cross-user store exists. Compute these 5 numbers from the current session's `loadHistory()` array and label clearly as "this session," OR if you'd rather not imply false precision, render an explicit "no aggregate data available yet" state — your call, but it must not look like a system-wide live counter. |
| Recent Verification Activity | SESSION-SCOPED, REAL | `lib/history.ts` | Real data, scoped honestly. |
| Needs Attention | SESSION-SCOPED, REAL | `lib/history.ts`, filter where `trust_score` is `MEDIUM`/`LOW` | Real data, scoped honestly. |
| Verification Coverage (per-company table) | UNSUPPORTED | none | No per-company historical rollup exists anywhere. Render an explicit "not yet available" state — do not build a fake table. |
| Live Verification Trace | REAL NOW | `/v1/verify` response fields: `claim`, `evidence`, `calculations`, `correction_log`, `trust_score` | Source from the most recent session history entry (or an idle/empty state if none exists yet this session) — this is the single most valuable, most real panel on this page; prioritize getting it right. |

## 10. INTERACTION SPECIFICATION

- **Map/city nodes**: clicking a city node should NOT trigger any new behavior beyond whatever currently exists (check `GlobalTransactionMonitor.tsx` for existing click handlers before assuming there are none). Do not add new fake "drill-down" interactions to demo data nodes.
- **Watchlist row click**: preserve existing behavior — clicking a symbol currently opens/updates `FocusView.tsx`. Do not change this flow; only add the new verif-status shield icon as a static (non-interactive, unless it already has a tooltip pattern elsewhere) visual element per row.
- **Right-column panel "VIEW ALL →" links**: preserve as-is (likely currently non-functional placeholders or route stubs — check before assuming behavior, and do not silently make them "work" by inventing a destination page).
- **New below-fold panels**: no click-through/drill-down interactions are required for v1 of Verification Pulse, Activity, Needs Attention, Coverage, or Live Trace — these are read-only status displays for this pass. If you want to add a "click a Recent Activity row to re-view that verification" interaction, that's acceptable as a small enhancement, but is not required.
- **Command bar**: preserve exact current behavior (`WorkspaceBottomBar.tsx` + the `quickDVL` logic in `GlobalTransactionMonitor.tsx`) — quick-action chips should continue to do whatever they currently do; do not add new quick actions unless trivial and clearly scoped.
- **Loading states**: every new panel needs a distinct loading skeleton (simple pulsing placeholder bars matching the existing dark theme, not a generic spinner) shown before its first data resolution.
- **Error states**: on fetch failure, panels must show the UNAVAILABLE badge state, not silently fall back to a stale-looking number.
- **Scroll behavior**: page-level vertical scroll for the whole workspace (above-fold + all new below-fold sections). Right column's News/Filing/Earnings/Sector stack may need its own internal scroll if it's already implemented that way — check current behavior first.
- **Nav active state**: whichever nav item corresponds to `/workspace` should show an active/highlighted state — check `NavModeToggle.tsx`'s existing active-state pattern (background tint + colored text) and extend the same pattern to the new 4-way nav if Section 17 has you rebuild it here.

## 11. ANIMATION / LIVE FEEL

Allowed: a subtle pulse on the LIVE status dot (check if `.animate-glow-pulse`/`animate-pulse` utility classes already exist in the codebase — reuse them, don't write new keyframes), a smooth fade-in when a new Recent Activity row appears (if you implement any kind of "new entry" transition), a gentle transition when the Live Verification Trace's stage indicators update state. Avoid: any new randomly-incrementing counter, any particle/glow effects beyond what already exists on the map, any bouncing/spring-physics entrance animations for panels, any animated number counters that don't reflect a real underlying value change (the existing `metrics/page.tsx` has an `AnimatedCounter` component that counts up to a hardcoded target on scroll-into-view — do NOT copy this pattern here for any of the new session-scoped or DEMO panels, since counting up implies the number was "computed," which would be misleading for a DEMO value).

## 12. RESPONSIVE BEHAVIOR

Desktop-first; this page's primary value is the dense multi-column terminal experience and it's acceptable for it to be genuinely awkward below ~1024px. For narrower viewports: stack the three above-fold columns vertically (left, then center/map, then right) rather than compressing them into unreadable narrow columns; allow the below-fold full-width bands (Verification Pulse stats, Activity/Attention/Coverage 3-column row) to also stack to single-column on narrow viewports; do not attempt to convert the watchlist or coverage tables into mobile "cards" — instead allow horizontal scroll within the table container if needed. Do not spend significant implementation time perfecting a phone-sized breakpoint in this pass — a reasonable tablet/narrow-desktop degradation is sufficient.

## 13. FUNCTIONALITY THAT MUST SURVIVE

- Watchlist symbol click → `FocusView` update.
- Existing live-fetch-with-fallback behavior in `MarketPulsePanel.tsx` and `WatchlistPanel.tsx` (even as you extend/fix the data client).
- The bottom command bar's existing quick-action chip behavior and its `quickDVL`/demo-query interaction in `GlobalTransactionMonitor.tsx`.
- `NavHealthIndicator`'s LIVE/DEGRADED display and the "using client-side DVL" degraded-mode messaging.
- Existing `ConnectionProvider` health polling.
- Any existing map pan/zoom/hover interactions already present in `GlobalTransactionMonitor.tsx` (inspect before modifying — do not assume there are none).

## 14. COMPONENT CREATION PLAN

**`VerificationPulsePanel.tsx`**
- PURPOSE: full-width stat row showing Claims Checked / Verified / Corrected / Conflicts / Unresolved.
- INPUT PROPS: none required — reads from `lib/history.ts` internally, OR accepts an optional `entries: HistoryEntry[]` prop for testability.
- STATE: derives counts via `useMemo` from `loadHistory()`.
- OUTPUT: 5 stat cells in a row, each with a number and a label, matching existing stat-card visual pattern from `app/metrics/page.tsx`'s `StatCard` (reuse that visual pattern, don't invent a new one).
- DATA STATUS BEHAVIOR: if `loadHistory()` returns an empty array, show all zeros with a "no verifications run this session yet" empty state, not a DEMO badge (this is honestly zero, not fake).

**`RecentActivityPanel.tsx`**
- PURPOSE: list of the most recent verification queries from this session.
- INPUT PROPS: optional `limit?: number` (default 5-8).
- STATE: reads `lib/history.ts`, sorted by timestamp descending.
- OUTPUT: rows with a status icon (✓/⚠/↻ matching trust_score), claim text, relative timestamp.
- DATA STATUS BEHAVIOR: empty state if no history yet.

**`NeedsAttentionPanel.tsx`**
- PURPOSE: subset of Recent Activity filtered to `trust_score` MEDIUM/LOW.
- INPUT PROPS: none, or shared `entries` prop with the above for consistency.
- OUTPUT: rows with severity badge (HIGH/MEDIUM per trust_score mapping — define HIGH severity = LOW trust, MEDIUM severity = MEDIUM trust, to avoid inventing a third scale).
- DATA STATUS BEHAVIOR: empty state ("nothing needs attention this session") if none match.

**`VerificationCoveragePanel.tsx`**
- PURPOSE: placeholder for the target's per-company coverage table.
- INPUT PROPS: none.
- OUTPUT: the table shell/header row exactly as in the target visual, with a centered "Coverage data not yet available — requires backend aggregation" message in place of rows, styled as an UNAVAILABLE/pending state, not an error.
- DATA STATUS BEHAVIOR: always UNAVAILABLE for this pass — do not wire fake data.

**`LiveVerificationTracePanel.tsx`**
- PURPOSE: horizontal 6-stage trace strip (Claim Extracted → Entity Resolved → Evidence Retrieved → Calculation Reconstructed → Constraints Check → Result) for the most recent verification.
- INPUT PROPS: optional `entry?: HistoryEntry` (most recent), or reads from `lib/history.ts` internally.
- OUTPUT: 6 connected stage nodes with checkmarks/timestamps, matching the target's visual style; below/beside it, the claim text, company, and final trust result.
- DATA STATUS BEHAVIOR: idle/empty state ("run a verification to see the trace") if no history exists yet this session.

**`DataStatusBadge.tsx`** (small shared component, put in `components/` not `components/workspace/`)
- PURPOSE: consistent LIVE/CACHED/DELAYED/DEMO/UNAVAILABLE badge used across every panel on this page (and reusable by the other three pages later).
- INPUT PROPS: `status: "live" | "cached" | "delayed" | "demo" | "unavailable"`.
- OUTPUT: colored dot + uppercase label, matching `NavHealthIndicator`'s existing visual pattern exactly.

## 15. COMPONENT REUSE PLAN

Reuse without rewriting: `MarketPulsePanel.tsx`'s existing fetch logic (extend, don't replace), `WatchlistPanel.tsx`'s row/sparkline rendering (extend with the new column, keep sparkline generation as-is for this pass), `GlobalTransactionMonitor.tsx`'s SVG map rendering (touch only the surrounding chrome), `RightColumnPanels.tsx`'s four sub-panel shells (add status badges, don't rebuild), `WorkspaceBottomBar.tsx` (restyle only), `lib/history.ts` (use as-is, it's already the right shape for the new panels), `lib/connection.tsx` (extend its pattern, don't duplicate it), the `.panel`/`.panel-header`/`.trust-badge`/`.label` CSS primitives in `globals.css`, the `StatCard` visual pattern from `app/metrics/page.tsx`. Why: these are all working, real, or intentionally-scoped-demo pieces — rewriting them burns budget without improving the target outcome, and risks regressing the "functionality that must survive" list in Section 13.

## 16. DO NOT BUILD YET / PLACEHOLDER BEHAVIOR

| Feature | Render as |
|---|---|
| Global Transaction Monitor real institutional flow data | DEMO (keep existing hardcoded visual, add DEMO badge if not already present) |
| Integrity Monitor real anomaly detection | DEMO |
| News Radar real news feed | DEMO |
| Earnings Calendar real data | DEMO / UNAVAILABLE |
| Sector Monitor real sector performance | DEMO |
| Verification Coverage per-company table | UNAVAILABLE (explicit "not yet available" message, not a fake table) |
| Filing Radar real SEC filings | BACKEND PENDING — build the component's prop interface correctly, render "connecting to filing data..." or similar pending state if no simple endpoint is available; do not build a new backend endpoint yourself, flag it |
| Cross-session Verification Pulse aggregate | SESSION-SCOPED instead (labeled honestly as "this session"), not hidden entirely — this is more useful than hiding it, as long as it's clearly not implying system-wide scope |

## 17. SHARED NAVIGATION

This is the FIRST of the four page implementations, so **you are establishing the shared navigation shell** that Verify, Market, and Research will reuse afterward. Build a single persistent nav component (e.g. extend `NavModeToggle.tsx` into a 4-way `WORKSPACE / VERIFY / MARKET / RESEARCH` nav, or create a new `PrimaryNav.tsx` if that's cleaner given the current file's structure — your call on which, but pick one and document it clearly in your final report so the next three prompts can reference it exactly). Use `next/link` instead of `<a>` tags for this new nav (this fixes the current full-page-reload issue as a natural side effect — acceptable to fix here since you're touching this file anyway, but do not go touch other unrelated `<a>` tags elsewhere in the app in this same pass). **Critical: `/` (the current Terminal/Verify route) must keep working and must not be silently removed or redirected in this pass** — if your navigation plan calls for Verify to eventually live at a different path, that migration happens in the Verify prompt, not here; for now, the new nav's "VERIFY" link should simply point at whatever the current Terminal route is (`/`), and Workspace becomes the new default only if you're also updating what `/` serves — if you're unsure whether to make `/workspace` the new root or keep `/workspace` as its own route with `/` still serving Terminal, **default to leaving `/` serving Terminal/Verify unchanged in this pass** and simply make the nav bar consistent; do not silently swap the site's default landing route as a side effect of a navigation-styling task. Document exactly what you did with routing in your final report so this is unambiguous for the next session.

## 18. IMPLEMENTATION ORDER INSIDE THE PAGE

**STEP 1** — Inspect only: `app/workspace/page.tsx`, `app/workspace/layout.tsx`, every file listed in Section 3's "Workspace-specific components," `app/layout.tsx`, `lib/history.ts`, `lib/connection.tsx`, `lib/api.ts`, `lib/market.ts`, `globals.css`, `tailwind.config.ts`. Do not open unrelated backend files beyond confirming the endpoints named in Section 3/9 exist as described.

**STEP 2** — Extract/confirm existing functionality: click through (or read code for) watchlist selection → FocusView, command bar quick actions, existing map interactions, existing LIVE/DEGRADED indicator behavior. Note anything that doesn't match this document's description of "current state" so your final report can flag discrepancies.

**STEP 3** — Build/update the shared navigation shell per Section 17.

**STEP 4** — Extend `WatchlistPanel.tsx` with the verif-status column (Section 4/9).

**STEP 5** — Restyle `IntegrityMonitorPanel.tsx` into the 4-stat DEMO summary card.

**STEP 6** — Add `DataStatusBadge.tsx` and apply it to every existing panel (`MarketPulsePanel`, `WatchlistPanel`, `RightColumnPanels`'s four sub-panels, `GlobalTransactionMonitor`) that currently lacks a clear live/demo indicator.

**STEP 7** — Build `VerificationPulsePanel.tsx`, `RecentActivityPanel.tsx`, `NeedsAttentionPanel.tsx` (all session-scoped, real, lower risk).

**STEP 8** — Build `VerificationCoveragePanel.tsx` (UNAVAILABLE placeholder) and `LiveVerificationTracePanel.tsx` (real, higher value — take your time here).

**STEP 9** — Wire all new below-fold sections into `app/workspace/page.tsx` in the correct vertical order per Section 5.

**STEP 10** — Visual polish pass against the target screenshot (spacing, borders, color accuracy).

**STEP 11** — Responsive pass per Section 12 (reasonable degradation only, not pixel-perfect mobile).

**STEP 12** — Run the test plan in Section 19.

## 19. TEST PLAN

Run and report actual output for:
- `npm run lint` (or the project's configured lint script) in `finverify-terminal/frontend` — report pass/fail and any warnings introduced by your changes.
- `npx tsc --noEmit` (or the project's type-check script) — report any new type errors.
- `npm run build` — report success/failure and any build warnings.
- Manual navigation sanity: load `/`, `/workspace`, `/market`, `/dashboard`, `/metrics` and confirm none of them 404 or crash after your nav changes.
- Manual functional sanity: run at least one demo query on the existing Terminal page (`/`) before and after your changes to confirm you haven't broken the underlying verify flow purely by touching shared nav/layout files.
- Confirm `lib/history.ts` entries populate the new session-scoped panels by manually running 2-3 demo queries and checking Recent Activity/Needs Attention/Verification Pulse update accordingly.
- Confirm every new/modified panel shows a correct DEMO/LIVE/UNAVAILABLE badge by temporarily simulating a fetch failure (e.g. via browser devtools network throttling/blocking) if practical, or by code inspection if not.

Do not report "tests should pass" — run them and paste the actual terminal output/summary in your final report.

## 20. VISUAL ACCEPTANCE CHECKLIST

- [ ] Map remains the single largest, most visually dominant element above the fold
- [ ] Left/center/right column ratio matches target's relative proportions, not equal thirds
- [ ] Below-fold sections (Verification Pulse, Activity/Attention/Coverage, Live Trace) appear as full-width bands in the correct order
- [ ] All new panels use the existing `.panel`/`.panel-header` styling, not new card styles
- [ ] No rounded mega-cards, gradients, or glassmorphism introduced anywhere
- [ ] Typography is monospace and dense throughout new components, matching existing components' text sizes
- [ ] All numeric columns are right-aligned with tabular-nums
- [ ] Every panel has a visible, correctly-colored status badge (LIVE/DEMO/etc.) at consistent visual weight — no tiny hard-to-see corner tags
- [ ] Semantic colors (green/amber/red/cyan/muted) are used correctly per Section 7, not decoratively
- [ ] Page feels visually consistent with the existing Terminal (`/`) and Market (`/market`) pages' aesthetic

## 21. FUNCTIONAL ACCEPTANCE CHECKLIST

- [ ] All items in Section 13 ("Functionality that must survive") still work after your changes
- [ ] No fake/invented numbers appear anywhere without a visible DEMO or UNAVAILABLE badge
- [ ] No new client-side calls to Finnhub or any other third-party provider were introduced beyond what already existed
- [ ] No new backend endpoints were invented or assumed to exist without being flagged in your final report
- [ ] `lib/history.ts`-derived panels correctly update when new demo queries are run in the same session
- [ ] `/` (Terminal) still loads and functions correctly
- [ ] Nav bar shows correct active state on `/workspace`
- [ ] Build succeeds with no new TypeScript errors

## 22. SCOPE GUARD

You must NOT: modify `app/page.tsx`, `app/market/page.tsx`, or `app/metrics/page.tsx` in this pass (only the shared nav/layout files, which affect all pages, are in scope for structural changes — page *content* for those three pages is out of scope); modify any backend Python file; modify the verification math/engine; invent a new backend endpoint yourself (if you determine one is genuinely needed — e.g. for Filing Radar — STOP, do not build a stub/mock version of it, and report exactly what's needed in your final report instead); install any new npm dependency without flagging it first in your final report; fabricate any financial data, verification count, trust score, filing, news item, or timestamp; commit; push. If you hit a point where the target screenshot clearly implies a capability this document says doesn't exist yet, follow this document's placeholder guidance (Section 16), not the screenshot.

## 23. FINAL RESPONSE FORMAT

End your work with exactly this structure, with literal actual output (not summaries):

```
## Files modified
## Files added
## Functionality preserved
## New functionality
## Data sources used
## Demo/unavailable elements
## Tests run
## Build result
## Known limitations
## Screenshot comparison notes
## git status --short
## git diff --stat
## Safety confirmation
```

No commit. No push. Then STOP for review.

---
---

# PROMPT 2 — VERIFY / TERMINAL

## 1. ROLE

You are the implementation engineer for FinVerify Terminal. The UX architecture and repository audit for this page have already been completed separately. Do not redesign the page's information architecture. Do not perform another broad frontend audit — inspect only the files listed in Section 3 before editing them. The TARGET screenshot is the visual source of truth for hierarchy, density, and aesthetic. The CURRENT screenshot shows today's shipped state. Transform CURRENT → TARGET while preserving every item in Section 13. If the screenshot implies a data value or capability that this document says doesn't exist, this document wins — render the honest placeholder state described in Section 16, never a fabricated number or a fake-working control.

## 2. PRODUCT PURPOSE OF THIS PAGE

Verify (currently called "Terminal" in the codebase and nav) answers: **"Can I trust this financial claim?"** A user brings a specific number or claim — typed, pasted from an AI output, or eventually from a document — and this page shows, transparently, every step FinVerify took to check it: what was claimed, what entity/metric it resolved to, what evidence was retrieved, what calculation was reconstructed, what constraints were checked, and what the final trust-scored result is. This page's entire value proposition rests on showing its work, not just producing a verdict — the pipeline visualization is not decoration, it is the product.

## 3. EXACT CURRENT REPOSITORY STRUCTURE

**Route:** `/` → `app/page.tsx` (661 lines — this is the file you will most heavily restructure). No separate layout file for this route; it uses the root `app/layout.tsx` shell directly.

**Current page structure inside `app/page.tsx` (read the whole file before starting):** a hero/explanation section at the top (FINVERIFY — DETERMINISTIC VERIFICATION LAYER heading + 3 feature cards: DVL Numeric Correction / SEC EDGAR Fundamentals / Earnings Verification), then a 3-column working area: left = query input + demo buttons + DVL Engine Status box, center = 3 stacked panels (Raw LLM Output / DVL Correction Log / Verified Output), right = Session/Errors/Stats tabbed log.

**Components used by this page (all in `components/`, flat structure, no subfolders):**
- `QueryInput.tsx` — the textarea + demo-query suggestion buttons (`sample-${i}` ids). Handles the input side of the page. Preserve its suggested-examples pattern; the target shows the same kind of suggested-example chips.
- `TerminalPanel.tsx` — renders the Raw LLM Output number with an animated count-up (`requestAnimationFrame`-based easing, this part is fine to keep) and the current DVL Engine Status box. **Contains one confirmed fake value: `const latency = (1.1 + Math.random() * 1.2).toFixed(1);` — this is not a measurement, it's a random number displayed as if real, and the target screenshot shows this same "LATENCY: 1.2s" field as part of the Engine Status box. You must replace this with a real measured round-trip time** (wrap the actual fetch call to `/v1/verify` in `performance.now()` timing) as part of this implementation, not as an optional nice-to-have.
- `VerificationLog.tsx` — renders the correction log (rule/before/after entries). Real data, sourced from the backend's `correction_log` field. Reuse as the basis for the target's "CORRECTION LOG" sub-panel.
- `TrustScore.tsx` — renders the trust badge (HIGH/MEDIUM/LOW + color). Real data from `trust_score`/`trust_color`. Reuse as the basis for the target's "TRUST & PROVENANCE" sub-panel, but note the target shows **four named sub-scores** (Source Reliability, Calculation Integrity, Data Consistency, Coverage) that do not currently exist as separate fields anywhere you've been shown — see Section 9, do not invent numeric values for these four sub-scores.
- `DVLReport.tsx` — used elsewhere for a fuller report view; check whether any of its internals are reusable for the new expandable pipeline-stage panels before writing new ones from scratch.
- `ErrorTaxonomy.tsx` — used on the Research page currently; not directly relevant here except as a reference for donut/breakdown visual patterns if needed.

**Shared library files:**
- `lib/api.ts` — the real typed client. Key function: whatever wraps `POST /v1/verify` (read the file to get its exact name/signature before writing new calling code). The response type includes `claim`, `evidence` (list), `calculations` (list), `correction_log`, `trust_score` — confirm the exact TypeScript interface in this file rather than assuming field names.
- `lib/dvl.ts` — `clientDVL()`, the real client-side fallback used when the backend is unreachable (scale-correction only, returns `{verified, logs, trust, trustColor}`). This is triggered today via the DEGRADED path in `lib/connection.tsx`/`NavHealthIndicator.tsx`. **Preserve this fallback exactly as-is** — do not remove it, and make sure whatever new UI you build for the 6-stage pipeline gracefully collapses to a simpler display when running in this degraded client-side-only mode (you cannot show "Evidence Retrieved" or "Constraints Check" stages truthfully when running on the simplified client-side fallback, since that fallback only does scale correction — design the pipeline strip to visually skip/grey-out stages that the client-side fallback doesn't actually perform, rather than pretending it ran the full pipeline).
- `lib/history.ts` — real `localStorage` history, `HistoryEntry` type. Preserve exactly; the target's "PAST QUERIES (THIS SESSION)" panel in the Session Activity column should read from this.
- `lib/connection.tsx` — real LIVE/DEGRADED backend status.

**Backend (do not modify — file: `finverify-terminal/backend/app/main.py`):**
- `POST /v1/verify` — the real pipeline: `compile_claim` → `resolve_entity/resolve_metric/resolve_time` → `EvidenceRetriever.retrieve` (real SEC EDGAR provider in `providers/sec.py`) → `MathEngine.run` (corrections) → constraint verification (`_run_constraint_verification`) → `compute_trust` → `build_result`. This is a genuinely staged pipeline in the backend, not a single monolithic call — the 6 stages in the target screenshot map almost exactly onto these real backend stages.
- Confirmed present in the response model (`core/models.py` `VerificationResult`, built in `core/output.py`'s `build_result`): `claim`, `verified_value`, `correction_log`, `evidence` (list), `calculations` (list, each with `name`, `inputs`, `output`, `passed`), `trust_score`.
- **NOT confirmed**: whether `constraint_result` (from `_run_constraint_verification`) is threaded all the way into the public API response schema, or only used internally before being folded into `trust_score`. Do not assume this field is available on the frontend response — check `lib/api.ts`'s actual TypeScript response type first. If it's missing from the type but you believe the backend has it, do not add backend code to expose it — flag this exactly in your final report per Section 22 as a Codex-owned backend change.
- **NOT confirmed / likely missing**: the four named trust sub-scores shown in the target (Source Reliability 0.98, Calculation Integrity 0.95, Data Consistency 0.90, Coverage 0.85). Check `core/trust_engine.py`'s `compute_trust` output shape via the frontend's typed response — if these sub-scores are not present in the type, do not invent plausible-looking numbers for them; render the Trust panel's overall `trust_score` (which is real) prominently, and either omit the four-sub-score breakdown entirely or render it as a clearly-labeled "detailed trust breakdown not yet available" placeholder.
- **No PDF/document ingestion path exists anywhere in `providers/`** — there is no backend support for the target's "DOCUMENT (PDF)" input tab today.
- **No user-configurable `Domain`/`Tolerance`/`Rule Set` parameters exist as backend inputs today** — `tolerance` (5%) is currently a fixed engine constant, not something the current `/v1/verify` call accepts as a parameter. Confirm this by checking the request body type in `lib/api.ts` before building functional dropdowns for these.
- **No cross-session aggregate exists** for "Claims Verified Today: 1,248", "Acc. (7D): 94.6%", "Errors Caught (7D): 172" shown in the target's top strip — these numbers have no backend source.

**Files that should probably NOT need modification for this page:** `app/workspace/*`, `app/market/page.tsx`, `app/metrics/page.tsx`, `app/dashboard/page.tsx`, all backend Python files, `lib/dvl.ts` (reuse, don't modify its logic — only integrate it into the new UI's degraded-mode rendering).

## 4. CURRENT → TARGET COMPONENT MAPPING

| CURRENT COMPONENT | TARGET REGION | ACTION | NOTES |
|---|---|---|---|
| Hero/explanation section (top of `app/page.tsx`) | *(removed in target)* | REMOVE (or relocate) | Target's Verify page has no marketing hero — it opens directly into the dense 4-column workbench with a compact "DETERMINISTIC VERIFICATION ENGINE" strip + real-time stat row instead. If the hero's explanatory copy is valuable, consider whether it belongs on a different page (e.g. it may already exist in shorter form elsewhere) rather than keeping a large marketing block here — but do not delete the underlying explanatory text entirely without confirming it isn't referenced elsewhere; just don't render it in this page's new layout. |
| `QueryInput.tsx` | Column 1 "INPUT" (with Claim/Question, AI Output, Document tabs) | EXTEND | Add tab switching UI around the existing textarea. "Claim/Question" tab = current behavior unchanged. "AI Output" tab = same textarea, different placeholder/label, same submit path (pasting AI-generated text is just a longer string into the same claim field — check whether the backend already handles this or if it's purely a UI framing difference). "Document (PDF)" tab = build as a visibly disabled/greyed control per Section 16, do not implement real upload. |
| `TerminalPanel.tsx`'s DVL Engine Status box | Left column "ENGINE STATUS" | KEEP + FIX | Fix the fake latency value (see Section 3). Keep Engine/Model/Providers/Rules Loaded fields as-is if they're already real (check before assuming — `RULES: 3` and similar values may be real engine config, confirm in the response/config rather than assuming they're fake just because latency was). |
| *(none exists today in this exact form)* | Column 2 "VERIFICATION PIPELINE" — 6-stage numbered strip | CREATE | New component: `VerificationPipelineStrip.tsx`. See Section 14. This is the centerpiece of the page. |
| *(none exists today)* | Stage 1 detail: "CLAIM PARSED" | CREATE | `ClaimParsedPanel.tsx` — renders `claim` fields (metric, period, claimed value, type). |
| *(none exists today)* | Stage 2 detail: "ENTITY RESOLVED" | CREATE | `EntityResolvedPanel.tsx` — renders resolved entity/ticker/exchange/match-confidence if present in the response; if match-confidence isn't in the current response type, omit that specific field rather than inventing a number. |
| *(none exists today)* | Stage 3 detail: "EVIDENCE RETRIEVED" | CREATE | `EvidenceRetrievedPanel.tsx` — renders the real `evidence` list (source, document type, filing date, period covered) already returned by the backend. This is real data currently underused by the existing `app/page.tsx`. |
| *(none exists today)* | Stage 4 detail: "CALCULATION RECONSTRUCTED" | CREATE | `CalculationPanel.tsx` — renders the real `calculations` list (inputs, output, passed). |
| *(none exists today)* | Stage 5 detail: "CONSTRAINTS CHECK" | CREATE | `ConstraintsPanel.tsx` — render ONLY if `constraint_result`/equivalent is confirmed present in the actual frontend response type; otherwise render this stage as present-but-summarized (e.g. folded into the overall trust score) rather than fabricating individual named constraint checks ("Period Alignment PASS", "Unit Consistency PASS" etc. shown in the target) that don't correspond to real fields. |
| `VerificationLog.tsx` | Column 3 "CORRECTION LOG" (within Verification Summary) | KEEP + RESTYLE | Real data, just restyle placement/visual treatment to match target. |
| `TrustScore.tsx` | Column 3 "TRUST & PROVENANCE" | EXTEND (partially) | Keep and prominently display the real overall trust score. Add the 4-sub-score breakdown ONLY if confirmed real per Section 3's note; otherwise add a clearly labeled "detailed breakdown not yet available" state instead of the 4 numbers shown in the target screenshot. |
| Right-side Session/Errors/Stats tabs | Column 4 "SESSION ACTIVITY" | KEEP + RESTYLE | Real, `lib/history.ts`-backed. Restyle into target's "LIVE LOG / EVENTS / ERRORS" tab structure and add the "PAST QUERIES (THIS SESSION)" + "QUICK ACTIONS" sub-sections shown in target. Quick action buttons ("Analyze 10-K Filing", "Extract from PDF", "Compare Periods", "New Verification") — "Extract from PDF" must be disabled per Section 16; "Analyze 10-K Filing" and "Compare Periods" should be evaluated for whether they map to any existing real capability before being wired as functional — if not, render disabled/coming-soon, don't fake success. |
| *(none exists today)* | Top strip: "CLAIMS VERIFIED TODAY / ACC. (7D) / AVG LATENCY / ERRORS CAUGHT" stat row | CREATE (DEMO/session-scoped) | No cross-session aggregate exists. See Section 9 — render session-scoped counts (from `lib/history.ts`) or an explicit "aggregate not yet available" state, not the specific numbers shown in the target screenshot. |

## 5. PAGE LAYOUT BLUEPRINT

```
[ shared root header + TickerBar, per Workspace prompt's Section 17 shell ]
-------------------------------------------------------------------------------
DETERMINISTIC VERIFICATION ENGINE strip (description text + stat row: Claims
Verified Today / Acc. 7D / Avg Latency / Errors Caught + small evidence-network
world-map decoration on the right, matching target)
-------------------------------------------------------------------------------
COLUMN 1 (≈22%)    | COLUMN 2 (≈32%)              | COLUMN 3 (≈24%)   | COLUMN 4 (≈22%)
                    |                               |                    |
INPUT               | VERIFICATION PIPELINE         | VERIFICATION       | SESSION ACTIVITY
- tabs: Claim/AI     |   (1)→(2)→(3)→(4)→(5)→(6)     | SUMMARY             | - Live Log/Events/
  Output/Document    |   numbered stage strip        | - claim vs verified |   Errors tabs
- textarea           |   with live status icons      |   comparison        | - Past Queries
- suggested examples |                                | - Evidence detail   |   (this session)
- query settings      | expanded stage detail panels  | - Correction Log    | - Quick Actions
  (Domain/Tolerance/  | below the strip (Claim        | - Trust &           |
  Rule Set)           | Parsed, Entity Resolved,      |   Provenance        |
- ENGINE STATUS box   | Evidence Retrieved,            |   (+ sub-scores      |
  (fixed latency)     | Calculation, Constraints,      |   IF confirmed real) |
- VERIFY CLAIM button | each individually bordered)    |                    |
                    |                               |                    |
                    | VERIFICATION RESULT card       |                    |
                    | (final verdict, full-width      |                    |
                    | within column 2, bottom)        |                    |
-------------------------------------------------------------------------------
```

Notes:
- The 6-stage pipeline strip is horizontal and compact at the top of column 2; the expanded per-stage detail panels stack vertically below it, one at a time in sequence, matching the target's "numbered card per stage" pattern.
- The final "VERIFICATION RESULT" card is visually the most emphasized element in column 2 — larger text, a colored left border or background tint matching trust level (green border for HIGH, amber for MEDIUM, red for LOW).
- Column widths above are approximate — the target shows column 2 (pipeline) as clearly the widest of the four; columns 1, 3, 4 are narrower and roughly similar to each other.
- This page does not need the below-fold scrolling pattern from Workspace — it's designed to mostly fit one dense viewport, with column 4's session log scrolling independently if content overflows.

## 6. VISUAL DESIGN SYSTEM

Same institutional-terminal system as Workspace (Section 6 of Prompt 1 applies identically — reuse `.panel`/`.panel-header`, monospace, tight density, thin borders, no gradients/glassmorphism/rounded mega-cards). Additional page-specific notes: the numbered pipeline stages (① through ⑥) should use small circular or square numbered badges, not decorative icons unrelated to the number; stage status icons (checkmark for complete, lock/pending icon for not-yet-reached, matching target's stage 6 "🔒" treatment before completion) should reuse whatever icon/badge convention already exists in `VerificationLog.tsx`/`TrustScore.tsx` rather than introducing a new icon set.

## 7. SEMANTIC COLOR RULES

Same mapping as Workspace Section 7. Page-specific application: pipeline stage numbers/borders are green once that stage completes successfully, amber if that stage produced a correction/caveat, red if verification ultimately fails or a constraint fails, muted grey/locked if not yet reached. The final Verification Result card's accent color follows the overall `trust_color` field exactly — do not introduce a different color logic for this card than what `TrustScore.tsx` already uses elsewhere.

## 8. DATA TRUTH RULES

Same five-state model as Workspace (LIVE/CACHED/DELAYED/DEMO/UNAVAILABLE). Apply specifically: the top-strip aggregate stats are the clearest DEMO/session-scoped case on this page (see Section 9) — do not render "1,248" or "94.6%" literally as shown in the target unless you've built a real session-scoped equivalent and labeled it as such. The pipeline strip itself, when running against a real `/v1/verify` call, should show LIVE status implicitly (it's showing a real just-completed verification) — no extra badge needed on the pipeline stages themselves beyond their own checkmark/pending states, since the whole page context already communicates data provenance via the Engine Status box's LIVE/DEGRADED indicator.

## 9. EXACT DATA FEASIBILITY

| Element | Status | Existing field/source | Notes |
|---|---|---|---|
| Claim Parsed stage | REAL NOW | `claim` field on `/v1/verify` response | Confirm exact sub-field names in `lib/api.ts`'s type before building the display |
| Entity Resolved stage | REAL NOW (partial) | likely folded into `claim`/context, per backend's `resolve_entity` step | Match-confidence percentage shown in target screenshot (98.7%) — confirm whether this exists in the type; if not, omit rather than invent |
| Evidence Retrieved stage | REAL NOW | `evidence` list field | Includes source, document type, filing date — real, from `providers/sec.py` |
| Calculation Reconstructed stage | REAL NOW | `calculations` list field | Includes inputs, output, passed |
| Constraints Check stage | UNCONFIRMED | possibly `constraint_result`, not confirmed present in public response type | Check `lib/api.ts` type definition first; if absent, render this stage as a summary pass/fail folded from trust_score rather than fabricating named sub-checks |
| Trust score (overall) | REAL NOW | `trust_score`/`trust_color` | |
| Trust sub-scores (Source Reliability, Calculation Integrity, Data Consistency, Coverage) | UNSUPPORTED (likely) | none confirmed | Do not invent these four numbers |
| Correction Log | REAL NOW | `correction_log` | |
| Fixed engine latency (1.2s shown in target) | DEMO CURRENTLY, MUST FIX | `Math.random()` in `TerminalPanel.tsx` | Replace with real measured round-trip time as part of this implementation |
| Claims Verified Today / Acc 7D / Errors Caught 7D | UNSUPPORTED (no aggregate) | none | Session-scoped from `lib/history.ts` or explicit "not yet available" |
| Domain / Tolerance / Rule Set query settings | UNSUPPORTED as functional controls | `tolerance` is a fixed backend constant today | Render as disabled/fixed-value display, or functional only if you confirm the backend request body actually accepts these as parameters |
| Document (PDF) input tab | UNSUPPORTED | no ingestion path in `providers/` | Disabled/coming-soon per Section 16 |
| Session Activity / Past Queries | REAL, session-scoped | `lib/history.ts` | |

## 10. INTERACTION SPECIFICATION

- **Input tabs**: switching between Claim/Question, AI Output, Document should swap the input affordance without losing whatever's currently typed if the user switches back (reasonable UX expectation, not explicitly shown in target but implied by tab behavior).
- **Pipeline stage strip**: on submitting a query, stages should visually progress in sequence — since the backend actually executes these stages sequentially before returning one combined response today (not a streaming/incremental API), you have two honest options: (a) reveal all 6 stages' results simultaneously once the single response arrives, with a brief staggered reveal animation for polish (acceptable, since you're not claiming a live progressive process, just adding a UI reveal rhythm to already-real, already-complete data), or (b) if you want genuine incremental reveal, that would require backend streaming which does not exist today — do not fake incremental reveal by inserting artificial `setTimeout` delays between stages that make it look like the backend is working through them live when it already returned a complete result; if you choose staggered reveal for polish, keep delays very short (under ~150ms per stage) so it reads as a reveal animation, not a fake progress simulation.
- **Stage expansion**: each of the 6 stages should be individually expandable/collapsible if screen space is tight, or always-expanded in sequence per the target screenshot showing all of them open — match the target's fully-expanded default state.
- **VERIFY CLAIM button**: preserve existing submit behavior/keyboard shortcut (`Ctrl+Enter` shown in target — check if this already exists in `QueryInput.tsx`, extend if not).
- **Suggested example chips**: preserve existing click-to-fill behavior.
- **Query Settings dropdowns**: if rendered as disabled/fixed-value (per Section 9), they should still be visually present and legible, just non-interactive, with perhaps a tooltip or subtle note indicating they're fixed for now — don't hide them entirely unless Section 16 says to.
- **Session Activity tabs (Live Log/Events/Errors)**: preserve existing tab-switching behavior from the current right-column implementation.
- **Quick action buttons**: "Extract from PDF" disabled; verify the other three ("Analyze 10-K Filing", "Compare Periods", "New Verification") against real capability before wiring — "New Verification" likely just clears the input, which is trivially real; the other two need confirmation.

## 11. ANIMATION / LIVE FEEL

Allowed: the short staggered pipeline-stage reveal described in Section 10 (if chosen), a subtle pulse on the "ENGINE: ONLINE" status dot, a smooth transition when the Verification Result card's trust-color border appears. Avoid: fake incremental progress bars that don't correspond to real backend timing, animated counters on the unsupported top-strip aggregate stats, any spinner that runs longer than the actual real fetch takes (i.e., don't add a minimum artificial loading delay purely for "feel" — if the real call is fast, let it be fast).

## 12. RESPONSIVE BEHAVIOR

Desktop-first, 4-column layout is the primary target. For narrower viewports: stack columns in priority order — Input first, Pipeline second, Verification Summary third, Session Activity fourth (or collapse Session Activity into a toggleable drawer if that's simpler) — rather than compressing all four into unreadable slivers. Do not attempt a polished mobile redesign in this pass.

## 13. FUNCTIONALITY THAT MUST SURVIVE

- The actual `/v1/verify` API call and its full request/response handling.
- Demo query buttons and their exact current fixed inputs/behavior.
- `lib/dvl.ts`'s client-side DEGRADED fallback path — must still work and must be visually distinguishable in the new layout (the pipeline strip should gracefully indicate reduced-stage coverage in this mode, per Section 3).
- `lib/history.ts` recording of new queries.
- The `NavHealthIndicator` LIVE/DEGRADED display.
- Keyboard submit shortcut if it currently exists.

## 14. COMPONENT CREATION PLAN

**`VerificationPipelineStrip.tsx`** — PURPOSE: horizontal 6-stage numbered progress strip. INPUT PROPS: `result: VerificationResponse | null`, `isLoading: boolean`. STATE: derives per-stage complete/pending/error status from which response fields are populated. OUTPUT: 6 stage nodes with connecting lines, numbered, colored per Section 7. DATA STATUS BEHAVIOR: all stages show "locked/pending" grey state before a query is run; in DEGRADED client-side-fallback mode, stages 2/3/5 (Entity Resolved, Evidence Retrieved, Constraints) should show a "not performed in degraded mode" state rather than a fake checkmark.

**`ClaimParsedPanel.tsx` / `EntityResolvedPanel.tsx` / `EvidenceRetrievedPanel.tsx` / `CalculationPanel.tsx` / `ConstraintsPanel.tsx`** — each: PURPOSE renders one pipeline stage's detail. INPUT PROPS: the relevant slice of the `/v1/verify` response. OUTPUT: bordered card matching target's per-stage visual format (field label/value pairs). DATA STATUS BEHAVIOR: `ConstraintsPanel` specifically must render a summarized/folded state instead of fabricated named checks if the underlying field isn't confirmed present (see Section 9).

**`VerificationTopStats.tsx`** — PURPOSE: the top strip's 4 aggregate stats. INPUT PROPS: none (reads `lib/history.ts`) or accepts injected session data. DATA STATUS BEHAVIOR: session-scoped counts with a "this session" label, or an explicit unavailable state — never the literal target numbers.

## 15. COMPONENT REUSE PLAN

Reuse: `QueryInput.tsx` (extend with tabs), `VerificationLog.tsx` (restyle placement only), `TrustScore.tsx` (extend, don't replace, its core overall-score rendering), `TerminalPanel.tsx`'s Engine Status box structure (fix latency, keep the rest), `lib/api.ts`, `lib/dvl.ts`, `lib/history.ts`, `lib/connection.tsx` unchanged. Why: the underlying data plumbing here is the most real, most complete pipeline in the whole app — the work is almost entirely about exposing already-real fields in a new layout, not building new data logic.

## 16. DO NOT BUILD YET / PLACEHOLDER BEHAVIOR

| Feature | Render as |
|---|---|
| Document (PDF) input tab | DISABLED — tab visible, greyed out, tooltip/label "Document verification coming soon" |
| Constraints Check named sub-checks (if field unconfirmed) | Folded summary only, not fabricated named checks |
| Trust sub-scores (Source Reliability etc., if unconfirmed) | HIDE or explicit "detailed breakdown not yet available" — do not show 4 fake numbers |
| Top-strip aggregate stats (Claims Verified Today, Acc 7D, Errors Caught 7D) | SESSION-SCOPED real counts with "this session" label, or UNAVAILABLE |
| Domain/Tolerance/Rule Set settings (if unconfirmed as real params) | DISABLED, shown as fixed current value, not an interactive dropdown that silently does nothing |
| "Analyze 10-K Filing" / "Compare Periods" quick actions (if no real capability found) | COMING SOON / DISABLED |
| "Extract from PDF" quick action | DISABLED |

## 17. SHARED NAVIGATION

Reuse the shared nav shell established in the Workspace prompt (Prompt 1, Section 17) exactly — do not rebuild it. If the Workspace implementation is not yet merged/available when you run this prompt, fall back to: build the same 4-way `WORKSPACE / VERIFY / MARKET / RESEARCH` nav using `next/link`, matching `NavHealthIndicator`'s existing visual pattern, and note in your final report that you built it independently so it can be reconciled with the Workspace prompt's version. **`/` must continue to serve this Verify page — do not move it to a new route in this pass**, even if conceptually "Verify" feels like it should live at `/verify`; that kind of route migration is out of scope here per the "existing URLs must remain backward compatible" instruction — nav label can say "VERIFY" while the underlying route stays `/`.

## 18. IMPLEMENTATION ORDER INSIDE THE PAGE

**STEP 1** — Inspect only: `app/page.tsx`, `components/QueryInput.tsx`, `components/TerminalPanel.tsx`, `components/VerificationLog.tsx`, `components/TrustScore.tsx`, `components/DVLReport.tsx`, `lib/api.ts` (confirm exact response type fields), `lib/dvl.ts`, `lib/history.ts`, `lib/connection.tsx`.

**STEP 2** — Confirm exact `/v1/verify` response TypeScript shape from `lib/api.ts` — this determines what Sections 4/9 tell you is real vs. must-be-placeholder. Note any discrepancy from this document in your final report.

**STEP 3** — Fix the fake latency value in `TerminalPanel.tsx` first (isolated, low-risk, do this before the larger restructure so it's not lost in a big diff).

**STEP 4** — Remove/relocate the marketing hero section; build the new compact "DETERMINISTIC VERIFICATION ENGINE" strip + top stats row (session-scoped/placeholder per Section 16).

**STEP 5** — Build `VerificationPipelineStrip.tsx` and wire it to real response data.

**STEP 6** — Build the five stage-detail panels, in pipeline order, checking real-data availability against Section 9 for each before writing its display.

**STEP 7** — Restyle `VerificationLog.tsx`/`TrustScore.tsx` into the Verification Summary column; decide and implement the Trust sub-score handling per Section 16.

**STEP 8** — Restyle the Session Activity column (existing Session/Errors/Stats tabs + new Past Queries/Quick Actions sections).

**STEP 9** — Add input tabs to `QueryInput.tsx`, including the disabled Document tab.

**STEP 10** — Visual polish against target.

**STEP 11** — Responsive pass.

**STEP 12** — Run test plan (Section 19).

## 19. TEST PLAN

Same categories as Workspace Prompt Section 19, applied here: `npm run lint`, `npx tsc --noEmit`, `npm run build` — report actual output. Manual: run every existing demo query button and confirm the pipeline strip and all stage panels populate correctly with real data. Manually verify the latency figure changes plausibly across repeated runs (confirming it's no longer `Math.random()`). Manually trigger the DEGRADED fallback path (e.g. by simulating backend unavailability if there's an existing way to do so, or by reading `lib/connection.tsx`'s health-check logic to determine how to trigger it) and confirm the pipeline strip degrades honestly rather than showing fake full-pipeline success. Confirm `/` still loads and the page doesn't crash on first load with no query yet run (empty/idle state for the pipeline strip and result card).

## 20. VISUAL ACCEPTANCE CHECKLIST

- [ ] Page opens directly into the dense workbench, no large marketing hero
- [ ] 4-column layout matches target's relative proportions (pipeline column widest)
- [ ] 6-stage pipeline strip is visually the centerpiece of column 2
- [ ] Numbered stage badges, connecting lines, and status colors match target's style
- [ ] Verification Result card is the most visually emphasized element, colored per trust level
- [ ] No fabricated-looking precision anywhere placeholder states are used (Section 16 items look honestly incomplete, not almost-real)
- [ ] Typography/density/borders consistent with Workspace page's established system

## 21. FUNCTIONAL ACCEPTANCE CHECKLIST

- [ ] `/v1/verify` call still works exactly as before
- [ ] Demo query buttons still work
- [ ] Latency figure is real, not `Math.random()`
- [ ] DEGRADED/client-side fallback mode still works and is honestly represented in the new pipeline UI
- [ ] No fabricated Constraints/Trust-sub-score/aggregate-stat numbers were introduced
- [ ] Document (PDF) tab is disabled, not fake-functional
- [ ] `/` still loads correctly
- [ ] Build succeeds with no new TypeScript errors

## 22. SCOPE GUARD

Do not modify: `app/workspace/*`, `app/market/page.tsx`, `app/metrics/page.tsx`, `app/dashboard/page.tsx`, any backend Python file, the verification math/engine, benchmark/research numbers. Do not invent a backend endpoint or parameter (e.g. for Tolerance/Domain/Rule Set, or Constraints detail) — if you determine the backend genuinely needs a small schema extension to properly support something this page wants to show, STOP and report exactly what's needed rather than building a stub. Do not install new npm dependencies without flagging first. Do not fabricate any data. No commit, no push.

## 23. FINAL RESPONSE FORMAT

Same structure as Prompt 1, Section 23, verbatim. No commit. No push. Then STOP for review.

---
---

# PROMPT 3 — MARKET

## 1. ROLE

You are the implementation engineer for FinVerify Terminal. The UX architecture and audit for this page are already complete. Do not redesign the information architecture. Inspect only the files in Section 3 before editing. TARGET screenshot is the visual source of truth; CURRENT screenshot is today's state. Transform CURRENT → TARGET, preserving Section 13's functionality. Written specification wins over the screenshot on any data/functionality conflict.

## 2. PRODUCT PURPOSE OF THIS PAGE

Market answers: **"What financial information should I investigate?"** It's company- and market-centric rather than claim-centric — a user browses real price/fundamentals data and, where FinVerify has flagged something worth checking, can jump directly into Verify with that specific claim pre-loaded. Every panel should either show real market/company data or connect back to verification — this page should not become a generic Bloomberg clone with decorative-only widgets.

## 3. EXACT CURRENT REPOSITORY STRUCTURE

**Route:** `/market` → `app/market/page.tsx` (184 lines).

**Current structure:** 3-column layout — left: `Watchlist.tsx` (watchlist with sparklines); center: tab-switchable `EarningsVerification.tsx` or `MetricPanel.tsx` (Earnings/Metrics toggle, per the current page's tab control); right: `MarketContext.tsx` (indices + hardcoded sector performance).

**Components:**
- `Watchlist.tsx` (distinct file from Workspace's `WatchlistPanel.tsx` — these are two separate, currently-diverging implementations of a similar idea; do not assume they share code). Imports from `lib/market.ts` (client-side Finnhub). Contains `generateSparkline()` (`Math.random()`-based, same pattern as Workspace's version). Shows "LIVE" when Finnhub data is present, "DEMO" otherwise — this labeling logic already exists and is honest; preserve it.
- `MetricPanel.tsx` — the DVL-verified metrics tab. Imports `getBasicFinancials`/`isFinnhubConfigured` from `lib/market.ts`. Contains `generateTrend()` (`Math.random()`-based sparkline for the metric trend line). Shows "DEMO DATA"/"MARKET DATA — DEMO MODE (add FINNHUB_KEY for live data)" labels already — preserve this honesty pattern. The actual metric values themselves, when live, come through the real `verify()` engine via the backend (`GET /market/all-metrics`) — confirm in this file whether it's actually calling the backend endpoint or computing client-side; from the prior audit, this endpoint runs metrics through the real engine server-side, so this panel should ideally be pulling from `lib/api.ts`, not `lib/market.ts`, for the metric values themselves (Finnhub might currently be used just for price context) — read the file carefully to determine exactly which values come from which client before changing anything.
- `EarningsVerification.tsx` (large — contains claim-type color/label maps, a flags/all-claims view toggle). Calls the backend's `/v1/earnings/{ticker}` endpoint. **Confirmed from backend inspection: this endpoint currently defaults to `demo_transcript_verification()`, which runs the real claim-extraction/verification logic against a hardcoded `SAMPLE_TRANSCRIPTS` dictionary in `ingestion/transcripts.py` — not a live transcript feed.** The component already renders `report?.source === "sample_transcript" ? "sample transcript" : "live transcript"` — this existing distinction is honest but visually small; the target screenshot's Earnings Verification panel should make this distinction more visually prominent (not just a small caption at the bottom), since the numbers shown (28 verified, 3 corrected, etc.) are real computations but running on synthetic input text.
- `MarketContext.tsx` — indices (`FALLBACK_INDICES` constant + live fetch via `lib/api.ts`'s `getMarketIndices()`, which is honest — falls back silently on error though, no visible badge) and `SECTORS` (fully hardcoded, `const SECTORS = [...]`, never fetched at all — this is a second, separate hardcoded sectors array from the one in Workspace's `RightColumnPanels.tsx`).

**Shared library files:**
- `lib/api.ts` — real backend client. `getMarketIndices()` exists and works. Confirm exact function names for `/market/quotes` and `/market/all-metrics` before wiring new calls.
- `lib/market.ts` — client-side Finnhub client, used by `Watchlist.tsx`, `MetricPanel.tsx`, and `TickerBar.tsx`. **This is the source of the cross-page price-mismatch bug** described in the Workspace prompt (Prompt 1, Section 3) — `WatchlistPanel.tsx` (Workspace) and `Watchlist.tsx` (Market) both ultimately depend on this same client and its Finnhub-key-gated behavior, but each has its own separate hardcoded fallback array with different numbers.
- `lib/history.ts`, `lib/connection.tsx` — same as other pages.

**Backend (do not modify):**
- `GET /market/quotes`, `GET /market/indices` — real, `yfinance`, backend-side, no client API key required.
- `GET /market/all-metrics?symbol=X` — real, runs derived ratios through the actual `verify()` engine; returns `trust_score`/`trust_color` per metric and a `question_text` field per metric (e.g. "What is AAPL's profit margin?") — **this `question_text` field is exactly what you should use to pre-fill a "VERIFY →" deep link into the Verify page**, it already exists, no new backend work needed for that specific handoff.
- `GET /v1/earnings/{ticker}` — real claim-extraction pipeline, sample-transcript input by default (see above).
- No backend endpoint exists for: Rates, Commodities, FX data; a per-sector "verification health" score of any kind; analyst-rating changes or press-release events (only SEC filing events are realistically sourceable via the existing `providers/sec.py`, and even that isn't currently wired into a simple "recent events" list endpoint).

**Files that should probably NOT need modification:** `app/workspace/*`, `app/page.tsx`, `app/metrics/page.tsx`, `app/dashboard/page.tsx`, any backend Python file.

## 4. CURRENT → TARGET COMPONENT MAPPING

| CURRENT COMPONENT | TARGET REGION | ACTION | NOTES |
|---|---|---|---|
| `Watchlist.tsx` | Left column "WATCHLIST" | EXTEND | Add the same "VERIF. STATUS" shield column used in Workspace (reuse that exact visual pattern/component if the Workspace prompt has already been implemented — check for a shared component first before building a second, slightly-different version). Fix the underlying data-client split described in Section 3 as part of this pass if feasible — if it feels risky given time constraints, at minimum ensure this page's watchlist shows the SAME prices as the Workspace page's watchlist in the same session (this is the concrete regression test for this fix). |
| `EarningsVerification.tsx` | Center "EARNINGS VERIFICATION" summary strip + "CLAIMS REQUIRING ATTENTION" table | EXTEND + RESTYLE | Restyle the top of this panel into the target's compact 4-stat-plus-trust-score strip (Verified/Corrected/Conflicting/Unresolved counts + Verification Trust score) — check whether these counts are already computed somewhere in the existing flags/all-claims data and reuse that computation rather than re-deriving it differently. Add a "CLAIMS REQUIRING ATTENTION" table (claim / reported / verified / difference / severity / status / VERIFY action) as a new sub-section — this can likely be derived from the existing `report.flags` array already used by this component; check its exact shape first. Make the sample-transcript-vs-live distinction visually prominent (a persistent badge in the panel header, not a small caption). |
| `MetricPanel.tsx` | (folded into new Claims table / kept as a secondary tab) | RESTYLE | Target's Market page centers on the Claims Requiring Attention table rather than the old Metrics-tab format; you can keep `MetricPanel.tsx`'s content accessible (e.g. as a secondary view) but the primary center-column experience per target is the Earnings/Claims flow. Use your judgment on whether Metrics becomes a tab within the same panel or is de-emphasized — do not delete its underlying functionality. |
| *(none exists today)* | "MARKET EVENTS & VERIFICATION SIGNALS" feed | CREATE | New component: `MarketEventsFeed.tsx`. See Sections 9/14 — only the SEC-filing-sourced portion of this can be real; analyst-changes/press-release event types have no backend source. |
| `MarketContext.tsx` (indices portion) | Right column "MARKET CONTEXT" — Indices tab | KEEP + EXTEND (tabs) | Add Rates/Commodities/FX as additional tabs, rendered disabled/placeholder per Section 16 — Indices remains the only functional tab. |
| `MarketContext.tsx` (sectors portion) | Right column "SECTOR PERFORMANCE" | RESTYLE + ADD PLACEHOLDER COLUMN | Add the target's new "VERIFICATION HEALTH" column as an explicit DEMO/placeholder column (a per-sector 0-1 score with no defined real computation exists) — do not invent a formula for this number. |
| *(none exists today)* | Left column "VERIFICATION STATUS LEGEND" | CREATE | Small static legend panel explaining the shield icon meanings (Verified/Needs Review/Conflicting/Unverified) — this is purely explanatory UI, not data-driven, safe to build directly. |
| *(none exists today)* | Left column "MARKET INTEGRITY MONITOR" (DEMO) | CREATE (or reuse Workspace's if shared) | If the Workspace prompt already built an Integrity Monitor summary component, reuse it here rather than building a second copy — check for a shared component location (e.g. move it to `components/` root if it's used on two pages) before duplicating. |

## 5. PAGE LAYOUT BLUEPRINT

```
[ shared header + TickerBar + market alert banner strip ]
-------------------------------------------------------------------------------
LEFT (≈20%)              | CENTER (≈55%)                        | RIGHT (≈25%)
                          |                                       |
WATCHLIST                 | EARNINGS VERIFICATION summary strip  | MARKET CONTEXT
(+ verif status col)      | (4 stats + Verification Trust score) | (Indices/Rates/
                          |                                       |  Commodities/FX tabs)
--------------------------| CLAIMS REQUIRING ATTENTION table     |------------------------
VERIFICATION STATUS       | (rows with per-row VERIFY action)    | SECTOR PERFORMANCE
LEGEND                    |                                       | (+ Verification Health
                          |---------------------------------------|  placeholder column)
--------------------------| MARKET EVENTS & VERIFICATION SIGNALS |
MARKET INTEGRITY MONITOR  | feed (tabbed: All/Earnings/Filings/  |
(DEMO)                     | Press Releases/Analyst/Macro)        |
-------------------------------------------------------------------------------
BOTTOM: data sources / last updated / connection status strip
```

Column ratio matches the current page's existing 3-column split closely — don't rebalance dramatically. Center column becomes noticeably busier/taller than today (summary strip + table + feed stacked) — this is the main structural growth area on this page.

## 6. VISUAL DESIGN SYSTEM

Same system as Prompts 1/2 (Section 6 applies identically — reuse existing tokens/panels, no new design language). Page-specific: the Claims Requiring Attention table's per-row "VERIFY →" button should visually match whatever button styling is established on the Verify page (Prompt 2) for consistency across the product — if Prompt 2 has already been implemented, copy its button component; if not, use the existing "EXECUTE"-style button treatment from the current Terminal page as the reference.

## 7. SEMANTIC COLOR RULES

Same mapping as Prompts 1/2. Page-specific: claim severity badges (HIGH/MEDIUM/LOW shown in the Claims Requiring Attention table) map directly to red/amber/green per the same trust-score convention used everywhere else — do not introduce a different severity color scale just for this table.

## 8. DATA TRUTH RULES

Same five-state model. Page-specific emphasis: the Earnings Verification numbers (28 verified, 3 corrected, etc.) are **real computations running on synthetic input** — this is a nuanced case that doesn't map cleanly onto simple LIVE/DEMO. Render it as: the computation badge shows something like "COMPUTED" or reuse "LIVE" only for the calculation itself, paired with a clearly separate, persistent "SAMPLE TRANSCRIPT" or "LIVE TRANSCRIPT" source badge (per the component's existing `report?.source` field) — do not let the presence of real-looking verified/corrected counts imply the underlying transcript was a real earnings call unless `source === "live_transcript"` (or whatever the real value is per the actual field).

## 9. EXACT DATA FEASIBILITY

| Panel | Status | Existing API/field |
|---|---|---|
| Watchlist prices | REAL NOW (via Finnhub client currently; consider consolidating per Section 4) | `lib/market.ts` currently; `lib/api.ts`'s `/market/quotes` is the more consistent long-term source |
| Watchlist verif-status column | REAL NOW | `compute_financial_metric`'s `trust_score` via `/market/all-metrics` |
| Earnings Verification stats (Verified/Corrected/Conflicting/Unresolved counts, Verification Trust score) | REAL computation, SYNTHETIC input | `/v1/earnings/{ticker}` → `demo_transcript_verification()` over `SAMPLE_TRANSCRIPTS` | Must carry a prominent "sample transcript" badge per Section 8 |
| Claims Requiring Attention table | REAL, derived from existing `report.flags` | same endpoint | Confirm exact shape of `report.flags` in `EarningsVerification.tsx` before building the table |
| Market → Verify deep link | REAL NOW | `question_text` field already on `/market/all-metrics` response | No new backend work needed |
| Market Events feed — SEC filing events | BACKEND PENDING | `providers/sec.py` exists but isn't exposed as a simple "recent events" list endpoint | Build against a typed prop; render BACKEND PENDING if no simple endpoint is available; do not invent one, flag it |
| Market Events feed — analyst changes / press releases | UNSUPPORTED | none | DEMO/omit |
| Indices (Market Context) | REAL NOW | `lib/api.ts`'s `getMarketIndices()` | Existing silent-fallback behavior should get a visible badge instead |
| Rates / Commodities / FX tabs | UNSUPPORTED | none | Disabled placeholder tabs |
| Sector Performance percentages | DEMO CURRENTLY | fully hardcoded `SECTORS` constant, never fetched | Keep DEMO-labeled |
| Sector "Verification Health" score | UNSUPPORTED, no defined formula | none | Explicit placeholder column, no invented numbers |
| Market Integrity Monitor | DEMO CURRENTLY | same as Workspace's Integrity Monitor — no real anomaly-detection backend | DEMO |

## 10. INTERACTION SPECIFICATION

- **Watchlist symbol click**: preserve existing selection behavior (drives the center column's ticker context, per current `app/market/page.tsx`'s `ANALYZE:` symbol selector row).
- **Claims table "VERIFY →" button**: clicking navigates to the Verify page (`/`) with the claim's `question_text` (or equivalent reported claim text) pre-filled into the input — this is the single most important new interaction on this page; implement it as a real navigation with query param or shared state (check how the app currently passes state between pages, if at all, before inventing a new mechanism — a simple URL query param like `/?prefill=...` read by `QueryInput.tsx` on mount is a reasonable, low-risk approach if nothing else exists).
- **Market Events feed tabs** (All/Earnings/Filings/Press Releases/Analyst/Macro): only "Earnings" and "Filings" sub-tabs can show any real-sourced content per Section 9; the others should be visibly present (matching target) but show an empty/DEMO state, not be hidden.
- **Sector Performance row hover**: no special interaction required beyond existing hover-highlight convention.
- **Indices/Rates/Commodities/FX tab switching**: Indices tab is functional; the other three tabs, when clicked, show a "coming soon" state rather than an empty broken-looking panel.

## 11. ANIMATION / LIVE FEEL

Same restrained approach as prior pages — subtle live-status pulses only, no fake incrementing counters, no decorative motion on placeholder/DEMO panels (a DEMO panel should look calm/static, not falsely "alive," since implying activity on fake data is itself a data-truth violation).

## 12. RESPONSIVE BEHAVIOR

Desktop-first. Narrower viewports: stack left/center/right vertically in that priority order; allow the Claims Requiring Attention table and Watchlist to scroll horizontally rather than being redesigned as mobile cards. Do not over-invest in a phone breakpoint this pass.

## 13. FUNCTIONALITY THAT MUST SURVIVE

- Existing symbol selection/analysis flow (`ANALYZE:` row).
- `EarningsVerification.tsx`'s flags/all-claims toggle.
- `MetricPanel.tsx`'s existing DVL-verified metric display (even if de-emphasized in the new layout, don't delete the underlying capability).
- Existing live-fetch-with-fallback behavior in `MarketContext.tsx` and `Watchlist.tsx`.
- Any existing keyboard/hover interactions in `Watchlist.tsx`.

## 14. COMPONENT CREATION PLAN

**`MarketEventsFeed.tsx`** — PURPOSE: tabbed event list (All/Earnings/Filings/Press Releases/Analyst/Macro) with per-event risk/verification signal and a VIEW/VERIFY action. INPUT PROPS: `events: MarketEvent[]` (typed interface you define, matching target's shape: company, event type, headline, detail, verification-signal risk level, timestamp). STATE: active tab filter. DATA STATUS BEHAVIOR: Earnings/Filings sub-tabs attempt real data (per Section 9); Press Releases/Analyst/Macro show an explicit empty/DEMO state, not fabricated entries.

**`ClaimsAttentionTable.tsx`** — PURPOSE: renders the Claims Requiring Attention table. INPUT PROPS: `claims: FlaggedClaim[]` derived from `EarningsVerification.tsx`'s existing `report.flags`. OUTPUT: rows with a "VERIFY →" button wired per Section 10. DATA STATUS BEHAVIOR: shows the sample-transcript badge inherited from the parent panel's source field.

**`VerificationStatusLegend.tsx`** — PURPOSE: static explanatory panel (Verified/Needs Review/Conflicting/Unverified shield meanings). INPUT PROPS: none. Purely presentational, no data-truth concerns.

**`SectorVerificationHealthColumn`** (likely a small addition inside the existing sector table component rather than a whole new file) — renders a placeholder column with a "—" or "N/A" value and a DEMO badge, not a computed score.

## 15. COMPONENT REUSE PLAN

Reuse: `Watchlist.tsx` (extend), `EarningsVerification.tsx` (extend/restyle, this is the richest existing component on this page and should not be rewritten from scratch), `MetricPanel.tsx` (keep functional, de-emphasize placement only), `MarketContext.tsx` (extend with new tabs), `lib/api.ts`, `lib/market.ts` (consolidate carefully, don't duplicate further), whatever `DataStatusBadge`/Integrity Monitor components were built in the Workspace prompt (check for and reuse rather than duplicate).

## 16. DO NOT BUILD YET / PLACEHOLDER BEHAVIOR

| Feature | Render as |
|---|---|
| Rates/Commodities/FX tabs | DISABLED / "coming soon" |
| Sector Verification Health score | placeholder "—", no invented formula |
| Market Events — analyst changes, press releases | DEMO/empty state |
| Market Integrity Monitor real anomaly detection | DEMO (reuse Workspace's treatment if that component is shared) |
| Live earnings transcript ingestion (vs. current sample-based) | Keep current sample-based behavior, but make the "sample transcript" badge much more prominent than today's small caption |

## 17. SHARED NAVIGATION

Reuse the nav shell established in the Workspace prompt exactly — do not rebuild. If unavailable, fall back per Prompt 2's Section 17 guidance and note it in your report. `/market` must continue to work at its current path — no route changes.

## 18. IMPLEMENTATION ORDER INSIDE THE PAGE

**STEP 1** — Inspect only: `app/market/page.tsx`, `components/Watchlist.tsx`, `components/MetricPanel.tsx`, `components/EarningsVerification.tsx`, `components/MarketContext.tsx`, `lib/api.ts`, `lib/market.ts`.

**STEP 2** — Confirm exact shape of `EarningsVerification.tsx`'s `report.flags`/`report.all_claims` data before building the new table.

**STEP 3** — Address the watchlist data-client consistency issue (Section 4) — at minimum verify/document current behavior; fix if feasible within reasonable risk.

**STEP 4** — Add verif-status column to `Watchlist.tsx`.

**STEP 5** — Restyle `EarningsVerification.tsx`'s top section into the summary-stats strip; make the sample/live badge prominent.

**STEP 6** — Build `ClaimsAttentionTable.tsx` and wire the VERIFY → deep link.

**STEP 7** — Build `MarketEventsFeed.tsx` with real SEC-filing-sourced content where feasible, DEMO elsewhere.

**STEP 8** — Extend `MarketContext.tsx` with Rates/Commodities/FX disabled tabs and the Sector Verification Health placeholder column.

**STEP 9** — Build `VerificationStatusLegend.tsx` and Market Integrity Monitor panel (reuse Workspace's if available).

**STEP 10** — Visual polish, responsive pass, test plan (Section 19).

## 19. TEST PLAN

`npm run lint`, `npx tsc --noEmit`, `npm run build` — actual output. Manual: confirm watchlist prices match Workspace page's watchlist for the same symbols in the same session (the concrete regression test for the cross-page bug). Confirm Market → Verify deep link actually navigates and pre-fills correctly. Confirm Earnings Verification numbers still compute correctly and the sample-transcript badge is visible. Confirm Rates/Commodities/FX tabs show disabled state, not a crash or empty broken panel.

## 20. VISUAL ACCEPTANCE CHECKLIST

- [ ] 3-column ratio matches target
- [ ] Center column's new stacked sections (summary strip → claims table → events feed) match target's vertical order
- [ ] Claims table numeric columns right-aligned, severity badges color-correct
- [ ] Sample/live transcript badge is prominent, not a tiny caption
- [ ] Placeholder tabs (Rates/Commodities/FX) look intentionally disabled, not broken
- [ ] Consistent panel/typography system with Workspace and Verify pages

## 21. FUNCTIONAL ACCEPTANCE CHECKLIST

- [ ] Existing symbol analysis flow still works
- [ ] Watchlist prices consistent with Workspace page
- [ ] Market → Verify deep link works end-to-end
- [ ] No fabricated Sector Verification Health scores, Rates/Commodities/FX data, or analyst/press-release events
- [ ] Sample-transcript status accurately reflected
- [ ] Build succeeds, no new TypeScript errors

## 22. SCOPE GUARD

Do not modify `app/workspace/*`, `app/page.tsx`, `app/metrics/page.tsx`, backend Python files, verification math. Do not build a new backend endpoint for Filing events or Verification Health — flag if needed. No new npm dependencies without flagging. No fabricated data. No commit, no push.

## 23. FINAL RESPONSE FORMAT

Same structure as Prompt 1 Section 23, verbatim. No commit. No push. Then STOP for review.

---
---

# PROMPT 4 — RESEARCH

## 1. ROLE

You are the implementation engineer for FinVerify Terminal. UX architecture and audit already complete. Do not redesign the information architecture. Inspect only the files in Section 3 before editing. TARGET screenshot is the visual source of truth for layout/hierarchy/density; CURRENT screenshot is today's state. Transform CURRENT → TARGET while preserving Section 13. **This page carries an unusually strict constraint beyond the other three: there is an ongoing, unresolved evaluation-leakage/provenance audit on FinVerify's research numbers. You must not treat any currently-displayed number (42.61%, 42×, 873, 73.10%, or any ablation/negative-result figure) as confirmed ground truth. Where the written specification and the screenshot conflict about whether a number is authoritative, the written specification wins, always.**

## 2. PRODUCT PURPOSE OF THIS PAGE

Research answers: **"Why should I trust FinVerify's methodology?"** This page exists to make FinVerify's claims falsifiable and reproducible — a skeptical quant or researcher should be able to see the exact dataset, sample size, model, methodology, limitations, and a path to reproduce the result themselves. Given the live product's entire premise is "don't trust unverified numbers," this page failing to hold itself to that same standard would be a direct credibility problem — treat this page's own numbers with the same skepticism the product applies to everyone else's.

## 3. EXACT CURRENT REPOSITORY STRUCTURE

**Route:** `/metrics` → `app/metrics/page.tsx` (248 lines).

**Current structure:** single scrolling page — `AnimatedCounter` component (counts up to a hardcoded target number once scrolled into view, via `IntersectionObserver`), a `STATS` constant array (5 stat cards: 42.61% Final Accuracy n=873, 42x Improvement, 54 DVL Corrections, 0% Extraction Failures, 73.1% Reasoning Errors — **all literal numbers typed directly into this React file**), a `ROBUST` constant array (robustness/ablation-under-noise table, also literal), plus `AblationSection.tsx` and `ErrorTaxonomy.tsx` components (both likely following the same hardcoded-constant pattern — confirm by reading them).

**Confirmed from repository inspection (not just the deployed page):** a real evaluation predictions file exists at `finverify-bench/examples/arithmetic_test_predictions.json` containing an `n=873`-sized dataset reference, and a large (~840KB) Jupyter notebook exists at `research/notebooks/notebookdc2907e290.ipynb` that most likely produced the numbers currently hardcoded in `app/metrics/page.tsx` — **but there is no versioned artifact file connecting the notebook's actual output to these React constants**, and the exact numbers were not verified line-by-line against the notebook's computed output during the prior audit. Treat the current numbers as **plausibly real but unverified**, not as confirmed and not as definitely wrong — your job in this pass is architectural (build the page to read from a versioned artifact interface), not to re-run or validate the evaluation yourself.

**Components:**
- `AblationSection.tsx` — renders the ablation table (Baseline/+Doc Context/+DVL v1/+QLoRA FT/+DVL v2 rows with accuracy/CI/delta columns) and the negative-results table (CoT zero-shot/CoT FT/Cross-doc RAG rows). Confirm whether this file itself contains the hardcoded numbers or receives them as props from `app/metrics/page.tsx`.
- `ErrorTaxonomy.tsx` — renders the error-category breakdown (Reasoning close/far, Magnitude, Order-of-magnitude, Sign, Scale, Unknown — currently as a horizontal bar-list per the live deployed page; target shows this as a donut chart instead).
- `MetricsChart.tsx` — a small chart component, check its current usage (likely the "Accuracy Progression" bar chart shown on the current page).

**Backend/data (relevant but read-only for this pass):**
- `research/finverify_paper.pdf`, `research/finverify_numerical_hallucination_llm.pdf` — real PDF files already exist in the repo. **The deployed page's "Paper PDF" and "GitHub" links currently point to `#` (dead links)** — this is a simple, safe, isolated fix: point these links at the real files/URLs instead of `#`. This fix is safe to make regardless of the broader numbers-under-audit concern, since it doesn't touch any displayed statistic.
- No `research_results.json` or equivalent versioned artifact currently exists anywhere in the repo.

**Files that should probably NOT need modification:** `app/workspace/*`, `app/page.tsx`, `app/market/page.tsx`, `app/dashboard/page.tsx`, any backend Python file, any evaluation script/notebook in `research/notebooks/` or `finverify-bench/` (do not re-run or modify any evaluation code — this page's job is presentation architecture, not re-validating the science).

## 4. CURRENT → TARGET COMPONENT MAPPING

| CURRENT COMPONENT | TARGET REGION | ACTION | NOTES |
|---|---|---|---|
| Single-scroll page structure | Left-rail section navigation (Executive Summary/Core Result/Benchmark Setup/Results/Ablation Studies/Negative Results/Methodology/System Architecture/Limitations/Reproducibility) | CREATE (new shell) | New `ResearchLeftNav.tsx` — a sticky left-side section-jump nav with scroll-spy active-state highlighting (highlight whichever section is currently in viewport). |
| `STATS` constant array + stat cards | "CORE RESULT" stat cards | REFACTOR (data source, not visual) | **Critical**: do not simply restyle these 5 cards in place. Refactor them to read from a typed `ResearchArtifact` interface (see Section 9/14) passed as a prop, populated from a stub/fixture for this pass — not from new hardcoded literals in a differently-named file. The visual card design can otherwise stay close to current. |
| `AblationSection.tsx` | "ABLATION STUDIES" + "NEGATIVE RESULTS" tables | EXTEND (data source) + RESTYLE (add significance column) | Same artifact-interface refactor as above. Target adds a "Stat. Significance" column (p-values) — only populate this if the artifact/stub actually provides it; do not invent p-values if they're not in your fixture. |
| `ErrorTaxonomy.tsx` | "ERROR BREAKDOWN" donut chart | RESTYLE (visual only) + REFACTOR (data source) | Change visual treatment from bar-list to donut per target; same artifact-interface data refactor. |
| *(none exists today)* | "EXECUTIVE SUMMARY" panel | CREATE | Short paragraph + a few small labeled badges (Single-model study / Parameter-free / Deterministic verification / Transparent & reproducible) — this is presentational text, safe to write directly, but keep the language appropriately hedged given the ongoing audit (e.g. avoid absolute claims the current numbers can't yet fully back). |
| *(none exists today)* | "BENCHMARK SETUP" panel | CREATE | Dataset/Examples/Question Type/Source/Answer Type/Evaluation/Model/FinVerify Engine fields — populate from the artifact interface's metadata fields. |
| *(none exists today)* | "KEY FINDINGS" checklist | CREATE | Short bullet list, derived from/consistent with whatever the artifact interface reports — do not phrase these more strongly than the underlying (currently-unverified) numbers support. |
| *(none exists today)* | "SYSTEM ARCHITECTURE" diagram strip (LLM Output → Claim Extraction → Evidence Retrieval → Deterministic Checks → Verification Result) | CREATE | Static explanatory diagram of the real pipeline stages (these stage names match the real backend pipeline confirmed during the Verify page's audit — this diagram is safe to build as accurate and static, it doesn't depend on the numbers-under-audit at all). |
| *(none exists today)* | "LIMITATIONS" panel | CREATE | Bullet list (single model, single dataset, short-answer numeric QA only, doesn't account for non-GAAP adjustments, etc.) — this section should be treated as at least as important visually as the Core Result stat cards, not a footnote, given the audit context. |
| *(none exists today)* | "REPRODUCIBILITY" panel (Code/Dataset/Paper/Environment badges + "Reproduce Results" action) | CREATE | Link badges should point at real repo paths/files where they exist (the two PDFs confirmed present in `research/`) — do not fabricate a working "Reproduce Results" button that doesn't actually do anything; if there's no real reproduction script/command to surface, render this as a disabled/coming-soon action or link directly to the relevant README/scripts folder instead of implying one-click reproduction exists. |
| *(none exists today)* | Citation/BibTeX box | CREATE | Static text box with copy-to-clipboard — safe to build directly, purely presentational, but double check the citation details (author, year, arXiv ID if any) against what's actually confirmed rather than inventing a placeholder arXiv number that looks real. |
| Dead "GitHub"/"Paper PDF" links (`#`) | same links, target shows them alongside "ARXIV"/"CODE"/"DATASET"/"REPRODUCE" | FIX | Point at the real files (`research/finverify_paper.pdf`, `research/finverify_numerical_hallucination_llm.pdf`) or real GitHub repo URL instead of `#`. Low-risk, do this early. |
| *(none exists today)* | "RESEARCH ALERT" banner ("research artifacts updated... Ablation study: +DVL v2 results added") | CREATE (metadata-driven, not live) | Render as a static line reading the artifact interface's `last_updated`/`git_commit`/changelog-note metadata fields — do NOT build this as a live notification/changelog feed; it's a single static line sourced from whatever your stub artifact's metadata says. |

## 5. PAGE LAYOUT BLUEPRINT

```
[ shared header + TickerBar ]
-------------------------------------------------------------------------------
RESEARCH ALERT banner (static, metadata-driven, full width)
-------------------------------------------------------------------------------
LEFT RAIL (≈15%, sticky)     |  MAIN CONTENT (≈65%)                | RIGHT RAIL (≈20%)
                              |                                       |
Executive Summary             |  EXECUTIVE SUMMARY panel             | BENCHMARK SETUP
Core Result                   |  ---------------------------------   |------------------
Benchmark Setup                |  CORE RESULT (5 stat cards)          | KEY FINDINGS
Results                        |  ---------------------------------   |
Ablation Studies               |  ACCURACY COMPARISON chart +          |------------------
Negative Results               |  ERROR BREAKDOWN donut (side by side)| SYSTEM
Methodology                    |  ---------------------------------   | ARCHITECTURE
System Architecture            |  ABLATION STUDIES table              | (pipeline strip)
Limitations                    |  ---------------------------------   |------------------
Reproducibility                |  NEGATIVE RESULTS + LIMITATIONS       | NEGATIVE RESULTS
(scroll-spy active highlight)  |  (side by side)                      | (short summary)
                              |                                       |------------------
                              |  RESEARCH INFO / CITATION (bottom      | LIMITATIONS
                              |  of left rail per target, or footer)  |------------------
                              |                                       | REPRODUCIBILITY
```

(Target screenshot shows a 3-column layout with the left rail as pure navigation, a wide center content area, and a right rail holding Benchmark Setup/Key Findings/System Architecture/Negative Results/Limitations/Reproducibility as compact summary cards — the center holds the fuller Executive Summary, Core Result stats, charts, and full Ablation table. Match this division; don't collapse everything into one center column.)

The left rail is sticky/fixed during scroll with scroll-spy highlighting of the current section (standard docs-site pattern) — check if any existing sticky-positioning pattern already exists elsewhere in the codebase (e.g. the header is already `sticky top-0`) and reuse that CSS approach.

## 6. VISUAL DESIGN SYSTEM

Same institutional system as prior pages (Section 6 in Prompts 1-3 applies identically). Page-specific: this page can afford slightly more generous internal padding within content panels than the dense terminal pages, since it's a reference/report-reading experience rather than a live-monitoring dashboard — but do not introduce rounded mega-cards, gradients, or a lighter/friendlier palette; it should still read as "institutional research report," matching the existing color/typography tokens, not a marketing one-pager.

## 7. SEMANTIC COLOR RULES

Same mapping as prior pages. Page-specific: the ablation table's "Delta" column uses green for positive/improving deltas and red for negative/degrading deltas (already the convention in the current negative-results table) — preserve this exactly. The donut chart's error-category colors should be chosen for clear differentiation but should not be assigned arbitrary meaning beyond category identity (they're not "good/bad" colors, just category colors) — pick from the existing extended palette if one exists (check `tailwind.config.ts` for any additional chart-specific color tokens beyond the core semantic set) rather than inventing new hex values.

## 8. DATA TRUTH RULES

This page's version of the five-state model is slightly different in emphasis: the concern here isn't "is this fetched live vs. cached" (research results are inherently static/versioned, not live-fetched), it's **"is this number backed by a versioned, traceable artifact, or is it a loose literal typed into a component?"** Treat "artifact-backed" as this page's equivalent of LIVE, and "hardcoded literal with no traceable source" as this page's equivalent of DEMO/UNAVAILABLE. Every number on this page must ultimately be traceable to the `ResearchArtifact` interface object (Section 9/14), even if — for this implementation pass — that object is a stub/fixture rather than a real generated file. Do not, under any circumstances, type a new bare numeric literal into a new component file as part of this pass, even if it matches what's currently in `app/metrics/page.tsx` — route everything through the interface.

## 9. EXACT DATA FEASIBILITY

| Element | Status | Notes |
|---|---|---|
| Core Result stat cards (accuracy, improvement, corrections, extraction failures, reasoning errors) | LEGACY / UNVERIFIED — architecturally must become ARTIFACT-INTERFACE-DRIVEN | Confirmed a real predictions file (`arithmetic_test_predictions.json`, n=873 reference) and a large evaluation notebook exist in the repo, but no verified line-by-line link to these exact displayed numbers. Build the interface; populate with a stub matching current displayed values for now (do not change the numbers), but structure the code so swapping in a real generated artifact later requires no further refactor. |
| Ablation table rows | LEGACY / UNVERIFIED, same treatment | |
| Negative results table | LEGACY / UNVERIFIED, same treatment | |
| Error taxonomy breakdown | LEGACY / UNVERIFIED, same treatment | |
| Statistical significance (p-values) for ablation rows | NOT CONFIRMED to exist anywhere | Only add this column if your stub/fixture explicitly provides it; do not invent p < 1e-6-style values not sourced from anything |
| System Architecture pipeline diagram (stage names) | REAL, SAFE | Matches the actual backend pipeline confirmed via the Verify page's audit — build as static, accurate, non-numeric content |
| Reproducibility links — Paper PDF | REAL, FIXABLE NOW | Files exist at `research/finverify_paper.pdf` and `research/finverify_numerical_hallucination_llm.pdf` |
| Reproducibility links — GitHub, Dataset, Environment/Dockerfile | UNCONFIRMED whether public URLs/files exist for all of these | Verify each one exists in the repo/is a real public URL before linking; if not, mark that specific badge as unavailable rather than linking to `#` again |
| "Reproduce Results" one-click action | UNSUPPORTED as a functional action | No evidence of an automated reproduction script/pipeline; render as a link to relevant instructions/README if one exists, or a disabled/coming-soon state otherwise |
| "Research Alert — updated" banner | METADATA-DRIVEN, not live | Source from the artifact interface's static metadata fields, not a live feed |
| Git commit hash / evaluation date fields | UNCONFIRMED | Populate from your stub's metadata; do not fabricate a specific-looking commit hash if you don't have a real one — use a clearly placeholder value like the stub's own version tag if needed, and note this in your final report |

## 10. INTERACTION SPECIFICATION

- **Left-rail navigation**: clicking a section label scroll-jumps to that section's anchor; scroll-spy highlights the currently-visible section as the user scrolls manually. This is the primary and only major interaction pattern on this page.
- **Citation/BibTeX**: a "copy" button copies the citation text to clipboard — standard, safe, low-risk to implement.
- **Reproducibility badges**: clicking a badge either opens the real linked resource in a new tab (for confirmed-real links like the Paper PDF) or shows a disabled/tooltip state (for unconfirmed ones) — do not make every badge look equally clickable if some don't actually go anywhere real.
- **Table row hover**: standard hover-highlight, matching existing table conventions elsewhere in the app.
- **No live-updating interactions are expected on this page** — unlike Workspace/Verify/Market, this page's content doesn't change during a session; the "alive" feeling here comes from information density and clear structure, not motion.

## 11. ANIMATION / LIVE FEEL

Minimal. A gentle scroll-spy highlight transition on the left nav is appropriate. **Do not reuse the existing `AnimatedCounter` count-up-on-scroll-into-view pattern for the new Core Result stat cards** — while visually appealing, an animated count-up implies the number was "computed live," which is the wrong signal for a page whose numbers are explicitly under audit; render the stat cards' values as static text, not an animated counter, in this pass (this is a deliberate downgrade from the current page's behavior, done for honesty reasons, not a visual regression to apologize for).

## 12. RESPONSIVE BEHAVIOR

Desktop-first, but this page is closer to a "long report" than a dense live dashboard, so it degrades more gracefully than the other three by nature. For narrower viewports: collapse the left-rail navigation into a dropdown/hamburger-style section-jump menu, stack the center/right columns vertically. This page can reasonably tolerate more responsive polish time than Workspace/Verify/Market since its content is naturally more linear/stackable — but still don't over-invest relative to the other pages' priorities.

## 13. FUNCTIONALITY THAT MUST SURVIVE

- Whatever chart rendering `MetricsChart.tsx`/the "Accuracy Progression" bar chart currently does — preserve the underlying chart library usage, just reskin/repoint its data source.
- The existing ablation/negative-results table data (values must not change — only their data-plumbing architecture changes, per Section 9).
- Any existing scroll or intersection-observer based behavior that's worth preserving conceptually (even though you're removing the specific count-up animation, per Section 11, other scroll-triggered reveals if present can stay, minus the counting-up-a-number part).

## 14. COMPONENT CREATION PLAN

**`ResearchLeftNav.tsx`** — PURPOSE: sticky section-jump navigation with scroll-spy. INPUT PROPS: `sections: {id: string, label: string}[]`. STATE: currently-active section id via intersection observer. Purely presentational/navigational, no data-truth concerns.

**`ResearchArtifact` type** (put in a shared types file, e.g. `lib/research.ts`) — the central interface everything on this page reads from:
```
interface ResearchArtifact {
  dataset: string; sampleCount: number; model: string; evaluationDate: string;
  finVerifyEngineVersion: string; gitCommit?: string;
  coreResult: { finalAccuracy: number; improvementMultiplier: number;
    dvlCorrections: number; extractionFailurePct: number; reasoningErrorPct: number; };
  ablations: { configuration: string; accuracy: number; ci: [number, number];
    delta?: number; pValue?: number; }[];
  negativeResults: { configuration: string; accuracy: number; ci: [number, number];
    delta: number; }[];
  errorTaxonomy: { category: string; count: number; pct: number; }[];
  limitations: string[]; keyFindings: string[];
  lastUpdatedNote?: string;
}
```
Build a stub/fixture object matching this shape, populated with the current page's existing displayed values (do not change the numbers — only change where they live and how they flow into components), clearly marked in a comment as "STUB — replace with generated research_results.json artifact once evaluation audit concludes."

**`CoreResultStats.tsx`, `AblationTable.tsx` (extends/wraps existing `AblationSection.tsx`), `ErrorBreakdownDonut.tsx` (replaces bar-list in `ErrorTaxonomy.tsx`), `BenchmarkSetupPanel.tsx`, `KeyFindingsPanel.tsx`, `SystemArchitectureDiagram.tsx`, `LimitationsPanel.tsx`, `ReproducibilityPanel.tsx`, `CitationPanel.tsx`, `ResearchAlertBanner.tsx`** — each takes the `ResearchArtifact` (or a relevant slice of it) as props; none should contain bare numeric literals internally.

## 15. COMPONENT REUSE PLAN

Reuse: whatever chart library/pattern `MetricsChart.tsx` already uses (don't switch charting libraries), `AblationSection.tsx`'s table-rendering logic (refactor its data source, keep its rendering approach), the existing `.panel` design primitives. Why: the visual presentation of the ablation/negative-results tables is already reasonably close to the target — the real work here is the data-architecture refactor (Section 9), not a visual rebuild of tables that already look fine.

## 16. DO NOT BUILD YET / PLACEHOLDER BEHAVIOR

| Feature | Render as |
|---|---|
| "Reproduce Results" one-click automated reproduction | DISABLED / link to README or relevant script folder instead, not a fake working button |
| Any Reproducibility badge whose target file/URL you can't confirm exists | Disabled/greyed, not linked to `#` |
| Statistical significance (p-value) column | Only if stub provides it; otherwise omit the column entirely rather than showing empty cells |
| Live "Research Alert" changelog feed | Static single line from stub metadata only |
| Any number not confirmed against your stub `ResearchArtifact` object | Do not add it |

## 17. SHARED NAVIGATION

Reuse the top-level 4-way nav shell (WORKSPACE/VERIFY/MARKET/RESEARCH) established in the Workspace prompt — do not rebuild it; this page's new `ResearchLeftNav.tsx` (Section 14) is a **separate, page-internal** navigation element and should not be confused with or replace the shared top-level product nav. `/metrics` must continue to work at its current path — no route changes, even though the nav label reads "RESEARCH."

## 18. IMPLEMENTATION ORDER INSIDE THE PAGE

**STEP 1** — Inspect only: `app/metrics/page.tsx`, `components/AblationSection.tsx`, `components/ErrorTaxonomy.tsx`, `components/MetricsChart.tsx`.

**STEP 2** — Fix the dead GitHub/Paper PDF links first (isolated, safe, do it before the larger refactor).

**STEP 3** — Define the `ResearchArtifact` interface and build the stub fixture, transcribing (not altering) the current page's existing numbers into it.

**STEP 4** — Refactor `AblationSection.tsx` and `ErrorTaxonomy.tsx` to consume the new interface instead of internal/passed-in literals.

**STEP 5** — Build `ResearchLeftNav.tsx` and the overall 3-column shell (left nav / main content / right rail).

**STEP 6** — Build the new presentational panels (Executive Summary, Benchmark Setup, Key Findings, System Architecture, Limitations, Reproducibility, Citation, Research Alert banner) — all reading from the same `ResearchArtifact` stub.

**STEP 7** — Convert `ErrorTaxonomy.tsx`'s visual treatment from bar-list to donut.

**STEP 8** — Remove the `AnimatedCounter` count-up behavior from the stat cards per Section 11; render as static text.

**STEP 9** — Visual polish against target.

**STEP 10** — Responsive pass.

**STEP 11** — Run test plan (Section 19).

## 19. TEST PLAN

`npm run lint`, `npx tsc --noEmit`, `npm run build` — actual output. Manual: confirm every number displayed on the rebuilt page matches what was displayed on the current live page (i.e., confirm you transcribed the stub correctly and didn't accidentally alter any figure). Confirm the GitHub/Paper PDF links now resolve to real files/URLs instead of `#`. Confirm scroll-spy left-nav correctly highlights the active section when manually scrolling through the whole page. Confirm the stat cards no longer animate/count up (per Section 11's deliberate change) and instead render as static values immediately.

## 20. VISUAL ACCEPTANCE CHECKLIST

- [ ] 3-column layout (left nav / main content / right rail) matches target's division of content
- [ ] Left nav scroll-spy highlighting works
- [ ] Error breakdown renders as a donut, not a bar-list
- [ ] Ablation/negative-results tables retain current numbers exactly, just restyled/re-sourced
- [ ] Reproducibility/Citation panels present and visually consistent with the rest of the app
- [ ] No new rounded-mega-card or gradient styling introduced

## 21. FUNCTIONAL ACCEPTANCE CHECKLIST

- [ ] All displayed numbers unchanged from current page (transcription accuracy check)
- [ ] Every number is sourced from the `ResearchArtifact` interface/stub, not a bare literal in a new component
- [ ] GitHub/Paper PDF links now point to real resources
- [ ] Stat cards no longer use the count-up animation
- [ ] "Reproduce Results" and any unconfirmed Reproducibility badges are honestly disabled, not fake-functional
- [ ] Build succeeds, no new TypeScript errors

## 22. SCOPE GUARD

Do not modify `app/workspace/*`, `app/page.tsx`, `app/market/page.tsx`, `app/dashboard/page.tsx`, any backend Python file, any evaluation notebook/script. **Do not change, "correct," round, or re-derive any research number during this pass** — your job is where the numbers live architecturally, not what they are; any concern about correctness belongs to the separate ongoing audit, not this implementation task. Do not install new npm dependencies without flagging. No commit, no push. If you find yourself wanting to "fix" a number because it seems inconsistent with something else in the repo (e.g. the notebook), STOP and report the discrepancy instead of editing it.

## 23. FINAL RESPONSE FORMAT

Same structure as Prompt 1 Section 23, verbatim, plus one additional line: `## Numbers transcription check (confirm all displayed values match the pre-existing live page exactly)`. No commit. No push. Then STOP for review.
