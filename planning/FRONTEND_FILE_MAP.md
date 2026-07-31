# FinVerify Frontend — File Map & Migration Classification

Legend: **KEEP** (use as-is, no changes needed for the workspace) · **MODIFY** (reuse but adapt) · **REPLACE** (concept needed, but rewrite rather than adapt) · **ARCHIVE** (not part of the workspace, leave alone, don't touch) · **NEW** (recommended new file, doesn't exist yet)

All paths relative to `finverify-terminal/frontend/`.

---

## `app/`

| File | Purpose | Class. | Reason / Suggested future responsibility |
|---|---|---|---|
| `app/layout.tsx` | Root layout: header nav, TickerBar, ConnectionProvider | **MODIFY** | Keep `ConnectionProvider` wrapper and health-check pattern. Nav should gain a workspace entry point (or the workspace replaces `/` entirely — decide before implementation). Switch remaining `<a>` tags to `next/link`. |
| `app/page.tsx` | "/" Terminal — full DVL query demo (hero, capabilities, 3-col query UI) | **ARCHIVE** (as the workspace's home) / pieces **MODIFY** | Do not delete — it's a working, valuable demo of the DVL and may stay as a separate route (e.g. move to `/terminal`) once the workspace becomes the new `/`. Its sub-logic (`handleSubmit`, `clientDVL`, `advancePipeline`, `DEMO_CASES`) should be extracted into `lib/` so both the legacy Terminal and the new workspace's persistent Query Input can share it (see NEW: `lib/queryPipeline.ts` below). |
| `app/error.tsx` | Global error boundary | **KEEP** | Applies workspace-wide already; no change needed. |
| `app/loading.tsx` | Global loading UI | **KEEP** | Fine as the route-transition fallback; workspace should have its own internal skeleton states per-panel in addition to this. |
| `app/globals.css` | Design tokens, `.panel`/`.trust-badge`/`.glow-*`/animations | **MODIFY** | Keep everything; **add** new primitives for the workspace: a denser `.panel-compact` variant (spec calls for ~25% less whitespace than current), heatmap grid cell classes, and a bottom-bar-specific scrolling feed style. |
| `app/dashboard/page.tsx` | Query history (localStorage), stats, filters, re-run | **ARCHIVE** | Not part of the 3-column workspace vision; leave as a separate utility route. Its `StatsRow`/`TrustBadge`/`HistoryRow` patterns are candidates to inform (not replace) the workspace's own history/session panel if one is added later. |
| `app/market/page.tsx` | "/market" — closest existing analog to the target workspace (Watchlist / Metrics-or-Earnings tabs / MarketContext) | **REPLACE** (superseded by the workspace) | This page's *shape* (3-column, symbol-driven center panel) is the direct precursor to the Dynamic Focus View pattern — study it closely — but its child components should be individually ported (see below) rather than keeping this route as-is; the new workspace's Focus View needs more sub-tabs (Verification/Integrity/Evidence/Timeline/Financials) than this page's simple metrics/earnings toggle. |
| `app/metrics/page.tsx` | "/metrics" — research/paper results page | **ARCHIVE** | Unrelated to the workspace vision (this is a research-marketing page, not a data panel). Leave untouched. Its `AnimatedCounter`/`StatCard` pattern is reusable elsewhere if needed (see components section). |
| `app/og/route.tsx` | OG image generation | **ARCHIVE** | Unrelated to the UI workspace; a metadata/SEO route. |

---

## `components/`

| File | Purpose | Class. | Reason / Suggested future responsibility |
|---|---|---|---|
| `AblationSection.tsx` | Research page: ablation table + bar chart | **ARCHIVE** | Belongs to `/metrics` only; not part of workspace. Chart-with-custom-tooltip pattern can be referenced for new charts (e.g. Financial Health Timeline) but the component itself stays put. |
| `DVLReport.tsx` | PDF audit report export (client-side `@react-pdf/renderer`) | **KEEP** | Fully reusable as-is. Wire it into the workspace's Focus View or a per-company "export" action; no changes needed to the component itself, just where it's invoked from. |
| `EarningsVerification.tsx` | SEC fundamentals + earnings-transcript red-flag claim list | **MODIFY** | This is the strongest existing seed for the workspace's **Verification Radar**. Keep the claim-row expand/collapse UX, trust-breakdown bar, and flagged/all toggle. Needs: (1) extraction from its current "full center panel" sizing down into a Focus-View sub-tab, (2) generalization beyond earnings-transcript claims to also show the Integrity Score's underlying "why" reasoning described in the spec (§6.2). |
| `ErrorTaxonomy.tsx` | Research page: donut chart of error types | **ARCHIVE** | Belongs to `/metrics` only. |
| `HeroNetwork.tsx` | Animated SVG world-map hero background | **ARCHIVE** | Purely decorative for the Terminal's hero section; the workspace has no hero section per the spec (value must show immediately, no marketing hero). |
| `MarketContext.tsx` | Right column: index cards, static sector bars, DVL engine status box | **MODIFY** | Index-card portion → directly feeds the workspace's **Market Pulse** panel (left column). Sector-bar portion is static/fake data today — needs a real data source or must be visually marked illustrative before reuse, per spec's "no generic widgets" principle. DVL-engine-status box is redundant with the spec's own Verification Radar / Integrity Score panels — likely drop it in the new workspace rather than port it. |
| `MetricPanel.tsx` | 2×2 grid of DVL-verified financial metric cards (per symbol) | **MODIFY** | Strong seed for the Focus View's **Financials** sub-tab. Uses client-side DVL (`lib/dvl.ts`) rather than backend-verified data — decide whether the workspace should call the backend's (unused) `/market/all-metrics` instead, for consistency with the Verification Radar's backend-sourced claims. |
| `MetricsChart.tsx` | Unused duplicate of Ablation/ErrorTaxonomy charts | **ARCHIVE** (dead code) | Not imported anywhere in the app. Flagged as dead code in the architecture report — do not port, do not delete without confirming with the team first (per instructions to only report, not delete). |
| `NavHealthIndicator.tsx` | Top-nav backend health dot (LIVE/DEGRADED) | **KEEP** | Reusable as-is for the workspace's top-bar status indicator (matches the target mockup's `[🟢]` element). |
| `NavModeToggle.tsx` | Terminal/Market pill switch in top nav | **REPLACE** | Once the workspace exists, this two-way toggle likely needs to become a router between Terminal (legacy demo) / Workspace (new default) / possibly Market Mode (retired or merged in) — rebuild rather than extend, since it's only built for 2 routes. |
| `QueryInput.tsx` | Left-column tall query box: DVL status dashboard, textarea, execute/demo buttons, sample chips, keyboard shortcuts | **MODIFY** | The textarea + submit + keyboard-shortcut logic (Enter, Cmd/Ctrl+Enter, Escape-to-clear) is the right foundation for the workspace's **persistent bottom Query Input bar**. Needs significant re-skinning: today it's a tall vertical panel meant to fill a whole column; the spec calls for a slim, single-line bottom bar. Extract the DVL-status-dashboard sub-block separately — it doesn't belong in a slim bottom bar and could move into a Focus View default state instead. |
| `QueryInterpretation.tsx` | Small strip showing detected query type/keywords/armed DVL rules | **KEEP** | Small, self-contained, reusable as-is in the legacy Terminal; not part of the workspace's core panels, but no harm keeping it wired into whichever surface still runs ad hoc queries. |
| `TerminalPanel.tsx` | Raw LLM output display with fake token/latency footer | **MODIFY** | If the workspace's persistent Query Input still needs a "raw result" display area, reuse this pattern, but replace the fake `Math.random()` latency figure with a real measurement (start timer at fetch, stop at response) before shipping it in a more prominent, "professional software" context. |
| `TickerBar.tsx` | Scrolling marquee of live/demo stock quotes | **MODIFY** | Could remain the top strip above the workspace, or be folded into/replaced by the Market Pulse panel. If kept, wire it to the existing `/ws/market` WebSocket instead of its current 30s polling, to reduce redundant Finnhub calls. |
| `TrustScore.tsx` | Verified-output display: large number, trust badge + tooltip, correction pipeline visualization | **MODIFY** | The trust-badge-with-tooltip pattern and the raw→corrections→verified pipeline visualization are directly reusable for the workspace's **Integrity Score** display (large prominent score + breakdown), though the Integrity Score is a different underlying metric (composite 0-100, not a single verified number) — treat this as a strong visual/interaction reference, not a drop-in component. |
| `VerificationLog.tsx` | DVL correction pipeline log with animated pipeline-stage indicator | **MODIFY** | The pipeline-stage visualization (`compile → resolve → retrieve → math → trust → verified`) and staggered log-entry animation are reusable for showing "why is this flagged" inside the Verification Radar or Focus View, but the component is currently tightly coupled to the single-query DVL flow — needs generalizing to arbitrary claims, not just one number. |
| `Watchlist.tsx` | Left-column: live/demo quotes with synthetic sparklines, click-to-select | **MODIFY** | Directly feeds the workspace's left-column **Watchlist** panel. Keep the click-to-select-symbol interaction (this is exactly the "click any company to load" behavior the Focus View needs). Sparklines are synthetic random walks today (`generateSparkline`) — replace with real historical price data before/while building this out further, since a sparkline is exactly the kind of thing users will notice is fake. |

---

## `lib/`

| File | Purpose | Class. | Reason / Suggested future responsibility |
|---|---|---|---|
| `lib/api.ts` | Typed FastAPI client: query/verify/health/market/fundamentals/earnings/history/websocket | **MODIFY** | Core file, keep and extend. Add typed calls for whatever new backend endpoints the Integrity Score / Opportunity Scanner / Trust Heatmap / Financial Health Timeline require (none of these exist server-side yet, per this audit — new endpoints + new client functions both needed). Also: several exports are currently unused (`getMarketQuotes`, `getAllMetrics`, `getVerifiedMetric`, `createMarketWebSocket`, `saveToHistory`, `getHistory`, `clearHistoryRemote`) — the WebSocket one especially should finally be put to use for the workspace's live Market Pulse panel. |
| `lib/market.ts` | Direct-from-browser Finnhub client (quotes, basic financials) | **MODIFY** | Before extending, resolve the redundant-Finnhub-call risk noted in the architecture report (frontend and backend may both be hitting Finnhub with the same free-tier key). Prefer routing all market data through the backend + WebSocket once that's confirmed, and either retire or keep this only as an emergency client-side fallback. |
| `lib/dvl.ts` | Client-side DVL fallback (used only by `MetricPanel.tsx`) | **REPLACE** (consolidate) | Duplicate of the more complete inline `clientDVL()` in `app/page.tsx`. Consolidate into a single shared `lib/clientDvl.ts` used by both the legacy Terminal and any workspace panel needing an offline fallback, incorporating the more complete logic (scale + sign + magnitude) from `page.tsx`'s version. |
| `lib/history.ts` | localStorage-backed query history (shared by Terminal + Dashboard) | **KEEP** | Self-contained and working; not part of the workspace's core panels but no reason to touch it unless the workspace also wants a query-history feed. |
| `lib/connection.tsx` | `ConnectionProvider` — backend health polling context | **KEEP** | Reusable as-is; this is the right pattern to extend (see NEW: `WorkspaceStreamProvider` below) rather than replace. |

---

## Config / misc

| File | Purpose | Class. | Reason |
|---|---|---|---|
| `middleware.ts` | Pass-through (Clerk stripped) | **KEEP** | No auth needed for the workspace per the spec; leave as-is. |
| `next.config.mjs` | Empty Next config | **KEEP** | No changes needed. |
| `tailwind.config.ts` | Color tokens, fonts, animations | **MODIFY** | Extend (don't replace) with any new keyframes/utilities the workspace needs (e.g. a heatmap-cell color scale, a denser spacing scale if 25% whitespace reduction requires new arbitrary values used repeatedly enough to warrant tokens). |
| `package.json` | Dependencies | **MODIFY** | Remove dead `@clerk/nextjs`/`@clerk/themes` deps (confirm with team first — reported as dead code, not deleted here). Add any new chart/data library only if `recharts` proves insufficient for the Trust Heatmap (a heatmap isn't a `recharts` primitive — likely needs a hand-rolled CSS grid, which doesn't require a new dependency). |
| `public/widget.js` | Embeddable widget | **ARCHIVE** | Unrelated to the workspace; separate embeddable product surface. |

---

## Recommended NEW files (don't exist yet)

| File | Responsibility |
|---|---|
| `lib/workspaceStream.tsx` | New React Context (sibling to `ConnectionProvider`) subscribing to the existing `/ws/market` WebSocket (via `lib/api.ts`'s already-defined but unused `createMarketWebSocket()`), fanning out quotes/events to Market Pulse, Intelligence Feed, and any other live panel. This is Milestone 2's `useWorkspaceStream` from the target spec — the transport already exists server-side, this file is the missing frontend consumer. |
| `lib/clientDvl.ts` | Consolidated client-side DVL fallback (see `lib/dvl.ts` REPLACE note above), replacing both existing duplicates. |
| `lib/queryPipeline.ts` | Extraction of `app/page.tsx`'s `handleSubmit`/`advancePipeline`/`clientDVL`/`DEMO_CASES` logic, so the workspace's persistent bottom Query Input can reuse the exact same query-routing behavior (demo-question fast path / LLM path / offline fallback) without duplicating it a second time. |
| `app/workspace/page.tsx` (or replace `app/page.tsx`) | The new Intelligence Workspace route itself — 3-column + bottom-bar shell per the target spec's layout diagram. |
| `app/workspace/layout.tsx` | Dedicated layout for the workspace if it needs its own header/chrome distinct from the root layout (e.g. to achieve true `h-screen`/no-scroll framing without fighting the root layout's existing header + TickerBar heights). |
| `components/workspace/MarketPulsePanel.tsx` | Left column — adapts `Watchlist.tsx` + `MarketContext.tsx`'s index-card portion; consumes `lib/workspaceStream.tsx`. |
| `components/workspace/OpportunityScanner.tsx` | Left column — genuinely new; needs a backend endpoint returning flagged-claim counts per company (does not exist yet). |
| `components/workspace/FocusView.tsx` | Center column — the dynamic, click-driven company drill-down; composes adapted `EarningsVerification.tsx` (Verification/Evidence), adapted `MetricPanel.tsx` (Financials), and new Integrity Score + Financial Health Timeline sub-panels. |
| `components/workspace/IntegrityScore.tsx` | Genuinely new — composite 0–100 metric (Consistency 40% + SEC agreement 30% + DVL confidence 30% per spec §6.1); needs new backend computation, does not exist in the frontend or (as far as this audit could determine) the backend. |
| `components/workspace/TrustHeatmap.tsx` | Genuinely new — color-coded grid of per-company integrity scores; no `recharts` primitive fits this, will be a hand-rolled CSS grid. |
| `components/workspace/FinancialHealthTimeline.tsx` | Genuinely new — sparkline of integrity score *over time* with annotations; distinct from the existing (synthetic) price sparklines in `Watchlist.tsx`/`MetricPanel.tsx`. |
| `components/workspace/NewsRadar.tsx`, `FilingRadar.tsx`, `EarningsRadar.tsx`, `SectorMonitor.tsx` | Right column — genuinely new; `SectorMonitor` can reuse `MarketContext.tsx`'s sector-bar JSX pattern once backed by real data, the other three have no existing analog. |
| `components/workspace/IntelligenceFeed.tsx` | Bottom bar — genuinely new continuous event log; can borrow layout/animation ideas from `VerificationLog.tsx`'s staggered-entry pattern and `page.tsx`'s `sessionEvents` state pattern, but needs to aggregate across all panel types, not just one query's pipeline. |
| `components/workspace/PersistentQueryInput.tsx` | Bottom bar — adapts `QueryInput.tsx` (see MODIFY note above) into a slim always-visible bar; wires to `lib/queryPipeline.ts`. |
