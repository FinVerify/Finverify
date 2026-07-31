# FinVerify Intelligence Workspace — UI Implementation Plan

Status: **Engineering blueprint. Ready for Claude Code.**
Depends on: `UI_ARCHITECTURE_REPORT.md`, `FRONTEND_FILE_MAP.md` (already produced — treat as source of truth, do not re-derive).
Repo: `finverify-terminal/frontend` (Next.js 14 App Router, TypeScript, Tailwind 3, recharts, no state library).

This document is the single contract for implementation. Every layout, sizing, component boundary, file placement, and interaction decision below is final. Claude Code should not re-decide any of it — only build it, panel by panel, milestone by milestone.

---

## 1. Executive Summary

**Old UI:** `app/page.tsx` ("/") is a query-driven DVL demo. It shows a hero section, three static capability cards, and a 3-column grid (Query Input | Results stack | Session/Errors/Stats tabs) — but the center and right columns are **empty until a query is submitted**. Verification is proven only reactively, one query at a time.

**New Workspace:** a new route (`app/workspace/page.tsx`, wired up as noted in §10/§11) that renders a permanent 3-column-plus-bottom-bar layout, populated with real (or gracefully-degraded fallback) data the instant it loads. Nothing waits for user input. The bottom bar keeps the query interaction alive, but it is now one panel among many, not the entry point to the whole app.

**The transformation, panel by panel:**

```
OLD                                          NEW
──────────────────────────────────────────────────────────────────────
Hero + capability cards (marketing)     →    Removed. No hero. Value shows immediately.
QueryInput (tall left column)           →    PersistentQueryInput (slim bottom bar)
TerminalPanel / VerificationLog /       →    Absorbed into Focus View (Verification
  TrustScore (reactive result stack)         Radar sub-tab) + Intelligence Feed
Watchlist ("/market" left column)       →    Watchlist panel (left column, unchanged position)
MarketContext index cards               →    Market Pulse panel (left column, top)
MarketContext sector bars               →    Sector Monitor panel (right column)
(nothing existed)                       →    Integrity Monitor panel (left column) — NEW
MetricPanel ("/market" center)          →    Focus View → Financials sub-section
EarningsVerification ("/market" center) →    Focus View → Verification Radar sub-section
(nothing existed)                       →    Focus View → Integrity Score, Evidence,
                                              Financial Health Timeline — NEW
(nothing existed)                       →    News Radar, Filing Radar, Earnings Radar
                                              (right column) — NEW
(nothing existed)                       →    Intelligence Feed (bottom bar, above query) — NEW
ConnectionProvider (health polling)     →    Kept as-is + new sibling WorkspaceStreamProvider
```

No existing functionality is deleted. `app/page.tsx` (Terminal) and `app/market/page.tsx` (Market Mode) remain reachable as legacy/demo routes per §11 — they are not touched during this build except for nav-link changes.

---

## 2. Workspace Philosophy

**Information density.** The workspace uses the same monospace, small-type, thin-border aesthetic already established in `globals.css` (`text-[9px]`–`text-[12px]`, 1px borders, 4px radius), but pushes density further: panel internal padding drops from the Terminal's `p-3`/`p-4` pattern to `p-2`/`p-2.5`, and row heights in list-style panels (Watchlist, News Radar, Filing Radar) target ~24–28px instead of the Terminal's ~32–36px. Target: roughly 25% less whitespace than the existing `/market` page, matching the spec's explicit density requirement.

**Bloomberg inspiration, not Bloomberg imitation.** Multi-panel, always-on, keyboard-operable, dark, monospace — yes. Bloomberg's exact chrome (function-key bars, orange-on-black) — no. The existing `t-green`/`t-amber`/`t-red`/`t-cyan` palette stays; it already reads as "professional terminal," not "chat app."

**FinVerify differentiation — the one rule that governs every panel decision below.** Before any panel is built, ask: *if you deleted the DVL/verification signal from this panel, would it still be worth having?* If yes, it's a generic finance widget and must gain a proprietary angle before being accepted (see §5 for how each panel satisfies this). This is why, e.g., Market Pulse (§5.1) is not just index prices — it's index prices **plus** a live count of pending verification checks; and why Sector Monitor (§5.10) is not just sector performance — it's average integrity score per sector, not average price return.

**Professional software you keep open all day.** No page reloads between interactions (`next/link`/client-state navigation only, never full `<a>` navigation within the workspace shell), no layout shift on data arrival (skeleton states reserve final size), and no auto-scrolling/stealing-focus behavior outside the Intelligence Feed (which is expected to auto-scroll, like a real terminal feed).

**Verification first.** The Dynamic Focus View's default (no-selection) state is Market Intelligence + Quick Stats — not a blank state, not a "type a question" prompt. The persistent Query Input is always visible but never blocks the rest of the screen from being useful.

---

## 3. Final Layout Specification

### 3.1 Viewport & Root Frame

- The workspace route renders inside its **own dedicated layout** (`app/workspace/layout.tsx`, see §11), separate from the existing root layout's Terminal-oriented chrome, to guarantee a true no-page-scroll frame.
- Root frame: `h-screen w-screen overflow-hidden flex flex-col`, background `bg-t-bg` (`#0a0a0a`) with the existing `.terminal-ambience` grid texture class from `globals.css` applied to `<body>`.
- No `<html>`/page-level scrolling anywhere. Every scrollable region is an explicit `overflow-y-auto` panel body with a fixed-height parent.

### 3.2 Top Bar (sticky, 40px)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ FINVERIFY — INTELLIGENCE WORKSPACE          14:32:21   [●LIVE]  ⚙ ⌘K   │  40px
└─────────────────────────────────────────────────────────────────────────┘
```
- Height: `h-[40px]`, `border-b border-t-border`, `bg-t-bg`, `sticky top-0 z-50`.
- Left: wordmark (`FINVERIFY` in `t-green`, `— INTELLIGENCE WORKSPACE` in `t-secondary`), reusing the existing header's typography scale from `app/layout.tsx`.
- Right, left-to-right: live clock (client-only, updates every second, `text-[10px] font-mono text-t-secondary tabular-nums`), `NavHealthIndicator` (reused as-is per file map), a settings gear icon-button (opens a lightweight saved-workspace/preferences popover — stubbed in Milestone 1, wired in Milestone 4), and a small `⌘K`/`Ctrl+K` hint badge (see §7 keyboard shortcuts).
- This top bar **replaces** the existing root layout's header + `TickerBar` combination for the workspace route only; Market Pulse (§5.1) absorbs the ticker's function. Legacy routes (`/`, `/market`) keep their existing header/TickerBar untouched.

### 3.3 Main Grid (fills remaining viewport height)

```
height = 100vh - 40px (top bar) - 36px (bottom bar height, see 3.5)
```

- `flex-1 grid grid-cols-[280px_1fr_300px] gap-[6px] p-[6px] min-h-0` on desktop (≥1280px).
- Column widths are **fixed pixel widths** for left/right (not percentage), so the center Focus View absorbs all extra width on large monitors — this matches the target mockup's implied proportions better than percentage columns at very wide viewports, and avoids the two existing pages' inconsistent 32/42/26 vs 25/50/25 ratios (per architecture report §4.5) by picking one canonical rule: **fixed 280px / fluid / fixed 300px**.
- Responsive behavior:
  - `≥1280px`: 3 columns as above.
  - `1024px–1279px`: left column collapses to a slim 56px icon rail (panel titles replaced by icons + a badge count, click to flyout); center and right remain 2-column (`grid-cols-[56px_1fr_260px]`).
  - `<1024px`: workspace is **not supported** in this milestone set — render a "Best viewed at ≥1024px width" notice with a link back to `/market` (legacy). Mobile/tablet workspace support is explicitly out of scope for Milestones 1–4; do not build responsive stacking for narrow viewports.
- Each of the three columns is itself `flex flex-col gap-[6px] min-h-0 overflow-hidden` — panels inside stack vertically and each panel manages its own internal scroll (`overflow-y-auto`), never the column itself scrolling as one unit (this preserves independent panel scrolling per the spec).

### 3.4 Column Contents & Panel Heights

**Left column (280px fixed width):**
| Panel | Height |
|---|---|
| Market Pulse | `h-[220px]` fixed |
| Watchlist | `flex-1 min-h-[160px]` (fills remaining space) |
| Integrity Monitor | `h-[200px]` fixed |

**Center column (fluid):**
| Panel | Height |
|---|---|
| Focus View | `flex-1` (fills entire center column — it is the only center panel) |

**Right column (300px fixed width):**
| Panel | Height |
|---|---|
| News Radar | `h-[180px]` fixed |
| Filing Radar | `h-[160px]` fixed |
| Earnings Radar | `h-[160px]` fixed |
| Sector Monitor | `flex-1 min-h-[120px]` (fills remaining space) |

Rationale for which panels get `flex-1` vs fixed height: Watchlist and Sector Monitor are list/bar-style panels whose content count varies (more symbols, more sectors) so they should absorb extra vertical space; Market Pulse, Integrity Monitor, News/Filing/Earnings Radar have a fairly fixed number of rows (indices, top-N flagged companies, top-N headlines) so a fixed height with internal scroll is more predictable.

### 3.5 Bottom Bar (sticky, two-row, 36px + variable feed height)

```
┌───────────────────────────────────────────────────────────────────────┐
│ 📡 14:31 Apple 10-Q filed   14:32 Tesla discrepancy detected   ...    │  28px — Intelligence Feed (1 line, auto-scroll)
├───────────────────────────────────────────────────────────────────────┤
│ 🔍 [Type a question or ticker...]                    [⏎] [🔎] [📊]   │  36px — Persistent Query Input
└───────────────────────────────────────────────────────────────────────┘
```
- Total bottom bar region: `h-[64px]` fixed, `border-t border-t-border`, `bg-t-bg sticky bottom-0 z-40`.
- Intelligence Feed row: `h-[28px] overflow-hidden`, single-line auto-scrolling ticker of the most recent event (see §5.11 for the interaction that expands it).
- Persistent Query Input row: `h-[36px] flex items-center px-3 gap-2`, single-line input (not the old multi-row textarea), submit icon-buttons on the right.
- The Intelligence Feed row is **expandable**: clicking it (or pressing the down-caret) grows it to `h-[160px]` (pushing the main grid's available height down by the delta — the main grid container's height calculation in §3.3 must be reactive to this, not a hardcoded constant) to show a scrollable multi-line feed. Collapsing returns to 28px. This expand/collapse state lives in the workspace shell's local state (not global context).

### 3.6 Overflow & Scroll Behavior Summary

- Root: no scroll.
- Main grid: no scroll (fixed height, `overflow-hidden`).
- Each column: no scroll (`overflow-hidden`), children stack with gaps.
- Each panel body: `overflow-y-auto`, independent scrollbar (existing thin scrollbar styling from `globals.css` `::-webkit-scrollbar` rules applies unchanged).
- Focus View sub-tab content area: `overflow-y-auto` within the Focus View's own fixed-height frame.
- Bottom bar: no scroll except the expanded Intelligence Feed state described above.

---

## 4. Component Hierarchy

```
WorkspaceLayout (app/workspace/layout.tsx)
└── WorkspaceStreamProvider (lib/workspaceStream.tsx) — wraps everything below
    └── ConnectionProvider (lib/connection.tsx, reused unchanged, nested inside stream provider)
        └── WorkspacePage (app/workspace/page.tsx)
            ├── WorkspaceTopBar (components/workspace/WorkspaceTopBar.tsx)
            │   ├── Wordmark (inline)
            │   ├── LiveClock (inline)
            │   ├── NavHealthIndicator (components/NavHealthIndicator.tsx — REUSED UNCHANGED)
            │   ├── SettingsButton (inline, stub in M1)
            │   └── ShortcutHint (inline)
            ├── WorkspaceGrid (inline layout wrapper in page.tsx, or components/workspace/WorkspaceGrid.tsx)
            │   ├── LeftColumn
            │   │   ├── MarketPulsePanel (components/workspace/MarketPulsePanel.tsx)
            │   │   │   └── IndexCard[] (inline, adapted from MarketContext.tsx)
            │   │   ├── WatchlistPanel (components/workspace/WatchlistPanel.tsx — adapted from Watchlist.tsx)
            │   │   │   └── WatchlistRow[] (inline)
            │   │   └── IntegrityMonitorPanel (components/workspace/IntegrityMonitorPanel.tsx)
            │   │       └── FlaggedCompanyRow[] (inline)
            │   ├── CenterColumn
            │   │   └── FocusView (components/workspace/FocusView.tsx)
            │   │       ├── FocusViewDefault (components/workspace/focus-view/FocusViewDefault.tsx)
            │   │       │   ├── MarketIntelligenceSummary (inline)
            │   │       │   └── QuickStats (components/workspace/focus-view/QuickStats.tsx — adapted from metrics/page.tsx's StatCard/AnimatedCounter)
            │   │       └── FocusViewCompany (components/workspace/focus-view/FocusViewCompany.tsx)
            │   │           ├── CompanyHeader (inline — name, ticker, large Integrity Score)
            │   │           ├── FocusViewTabs (inline — tab strip)
            │   │           ├── IntegrityScorePanel (components/workspace/focus-view/IntegrityScorePanel.tsx)
            │   │           ├── VerificationRadar (components/workspace/focus-view/VerificationRadar.tsx — adapted from EarningsVerification.tsx)
            │   │           ├── FinancialsPanel (components/workspace/focus-view/FinancialsPanel.tsx — adapted from MetricPanel.tsx)
            │   │           ├── EvidencePanel (components/workspace/focus-view/EvidencePanel.tsx — adapted from EarningsVerification.tsx's fundamentals section)
            │   │           ├── FinancialHealthTimeline (components/workspace/focus-view/FinancialHealthTimeline.tsx)
            │   │           └── FilingsPanel (components/workspace/focus-view/FilingsPanel.tsx — shares data with right-column FilingRadar, company-filtered)
            │   └── RightColumn
            │       ├── NewsRadarPanel (components/workspace/NewsRadarPanel.tsx)
            │       │   └── NewsItemRow[] (inline)
            │       ├── FilingRadarPanel (components/workspace/FilingRadarPanel.tsx)
            │       │   └── FilingItemRow[] (inline)
            │       ├── EarningsRadarPanel (components/workspace/EarningsRadarPanel.tsx)
            │       │   └── EarningsItemRow[] (inline)
            │       └── SectorMonitorPanel (components/workspace/SectorMonitorPanel.tsx — adapted from MarketContext.tsx's sector-bar block)
            │           └── SectorBar[] (inline)
            └── WorkspaceBottomBar (components/workspace/WorkspaceBottomBar.tsx)
                ├── IntelligenceFeed (components/workspace/IntelligenceFeed.tsx — pattern borrowed from VerificationLog.tsx's staggered animation)
                │   └── FeedItem[] (inline)
                └── PersistentQueryInput (components/workspace/PersistentQueryInput.tsx — adapted from QueryInput.tsx)
```

All `components/workspace/*` files live in a **new** `components/workspace/` subdirectory (the first subdirectory the `components/` folder will have — current structure is flat per the architecture report). `focus-view/` is a nested subdirectory under it for the Focus View's own sub-panels, since it has the most internal structure of any single panel.

---

## 5. Detailed Panel Specifications

Every panel below follows the same template. Read §6 afterward for the Focus View's extended treatment (it's the most complex panel and gets its own dedicated section beyond this one).

### 5.1 Market Pulse (left, top, 220px)

- **Purpose / why it exists:** immediate "is the market calm or stressed" read, at a glance, before anything else loads.
- **Data shown:** S&P 500, NASDAQ, VIX, 10Y yield, BTC, Gold, Oil, USD/INR — price, change, change%, each with a "last updated" timestamp. Plus one FinVerify-proprietary line: **"X verifications pending"** — a live count of in-flight/queued DVL checks across the whole system (the differentiation angle — a generic ticker doesn't have this).
- **Data source:** indices/FX/commodities → `WorkspaceStreamProvider` (§9) subscribed to `/ws/market`, backed by backend's existing `/market/indices` endpoint (per architecture report §6.4) for initial paint, then live WebSocket updates. "Verifications pending" count → **new backend field** required (see below).
- **Existing component to reuse:** `MarketContext.tsx`'s index-card rendering block (the `.map()` over `indices` with the up/down glow styling) — port the JSX pattern, not the whole component (drop its sector-bar and DVL-status-box sections, which move to Sector Monitor and are dropped respectively).
- **New backend required:** yes — a lightweight endpoint or WebSocket field exposing count of pending/recent verification operations. If this cannot be built in time for Milestone 2, ship Milestone 1–2 with this line hidden (do not fake the number — an explicit "—" placeholder is acceptable, a random number is not, per the architecture report's caution against compounding synthetic-data issues).
- **Interactions:** no click interactions (informational only). Hover on any index row shows a tooltip with prior-close and day-range (new, small, non-blocking).
- **Loading state:** render `FALLBACK_INDICES` (already defined in `MarketContext.tsx`, reuse the constant) immediately, never a spinner — matches the existing "never a stuck loading state" pattern noted approvingly in the architecture report.
- **Empty state:** N/A (fallback data always present).
- **Error state:** if the WebSocket disconnects, freeze last-known values, add a small `text-t-amber` "STALE" tag next to the timestamp (reuse the existing `stale` field pattern already present on `MarketQuote` in `lib/api.ts`).
- **Hover behavior:** tooltip as above.
- **Click behavior:** none.
- **Animations:** on value update, flash the changed number green/red for 200ms (see §9 "Market update" animation spec).
- **Update strategy:** Live via WebSocket (5–10s per spec's cadence table), matching existing backend's 5s `/ws/market` push interval.
- **Dependencies:** `WorkspaceStreamProvider`, `lib/api.ts` (`MarketQuote` type, `getMarketIndices` for first paint).
- **Acceptance criteria:**
  - [ ] Renders fallback data with zero network latency on first paint.
  - [ ] Updates live within one WebSocket tick after connection.
  - [ ] Shows STALE tag within 15s of a dropped connection.
  - [ ] "Verifications pending" line present (or explicit placeholder, never fabricated).
  - [ ] No layout shift between fallback and live data (same row height/structure).

### 5.2 Watchlist (left, fills remaining space)

- **Purpose:** user's tracked companies, always visible, the primary click-to-focus entry point into the Focus View.
- **Data shown:** symbol, price, change, change%, sparkline, **integrity score badge** (new field — the differentiation angle: a generic watchlist doesn't show trust, this one does).
- **Data source:** quotes from `WorkspaceStreamProvider`; integrity score per symbol from a **new** backend endpoint (see Integrity Score, §6.5) — until that endpoint exists, show quotes only and omit the badge column entirely rather than fabricate a score.
- **Existing component to reuse:** `Watchlist.tsx` almost entirely — same column layout, same click-to-select interaction (`onSelectSymbol`), same live/demo indicator. **Change required:** replace `generateSparkline()`'s synthetic random walk with real intraday price history once available from the backend; until then, keep the synthetic sparkline but do not add new synthetic elements (don't compound the issue further — see architecture report §9 risk #3).
- **New backend required:** yes, for the integrity-score badge column only; quotes already work via existing infrastructure.
- **Interactions:** click a row → sets the workspace's `selectedSymbol` state → Focus View transitions to `FocusViewCompany` (see §6.3 for the full transition spec).
- **Loading state:** reuse `Watchlist.tsx`'s existing pattern — quotes render immediately from fallback/last-known data.
- **Empty state:** if the user's watchlist is empty (post-M4 personalization), show "No symbols tracked — click any company elsewhere in the workspace to add it" with a subtle border-dashed placeholder row.
- **Error state:** per-row `⚠ STALE DATA` tag, reused from existing `Watchlist.tsx` pattern.
- **Hover behavior:** row highlights (`hover:bg-white/[0.02]`, already the existing pattern).
- **Click behavior:** selects symbol; selected row gets `border-l-t-green` highlight (existing pattern, unchanged).
- **Animations:** row-level flash-on-update (see §9).
- **Update strategy:** Live (WebSocket).
- **Dependencies:** `WorkspaceStreamProvider`, workspace-level `selectedSymbol` state (owned by `WorkspacePage`, passed down — see §12).
- **Acceptance criteria:**
  - [ ] Clicking a row updates Focus View within one render cycle, no page navigation.
  - [ ] Selected row visually distinct.
  - [ ] Sparkline renders without layout shift.
  - [ ] Integrity badge omitted gracefully (not blank/broken) until backend support exists.

### 5.3 Integrity Monitor (left, bottom, 200px) — formerly "Opportunity Scanner"

- **Purpose:** surfaces where to look first — the single most-cited "killer feature" panel in the target spec.
- **Data shown:** company name + count of flagged claims (e.g., "Tesla 3", "Coinbase 2", "Intel 4"), sorted descending by flag count. Zero-flag companies (e.g. "Nvidia 0", "Apple 0") shown at the bottom in muted styling, not omitted — their presence is itself a signal ("nothing wrong here").
- **Data source:** **new backend endpoint** aggregating flagged-claim counts per company across all verification activity (earnings claims, fundamentals corrections). Does not exist today — closest existing analog is `EarningsVerification.tsx`'s per-company `flagged_count`, which the new endpoint should generalize across all tracked companies at once rather than one company at a time.
- **Existing component to reuse:** none directly — this is new UI, though its row styling (name + count + click-to-select) should visually match Watchlist's row pattern for consistency.
- **New backend required:** yes, this is the panel's core dependency; cannot ship real data without it. Milestone 1 ships this panel with mock/static data explicitly labeled as such (a small "DEMO DATA" tag, matching the existing convention already used in `MarketPanel`/`market/page.tsx` for Finnhub-less states).
- **Interactions:** click a row → same `selectedSymbol` transition as Watchlist.
- **Loading state:** skeleton rows (3–5 grey placeholder bars) while first fetch resolves; not a spinner.
- **Empty state:** "No flagged claims across tracked companies" centered message if the aggregate is genuinely empty.
- **Error state:** if the endpoint fails, fall back to a static demo dataset (mirroring the target spec's own mockup numbers: Tesla 3, Coinbase 2, Intel 4, Nvidia 0, Apple 0) with a visible "DEMO DATA" tag — never fail silently into a blank panel.
- **Hover behavior:** row highlight, tooltip showing most recent flag's claim type.
- **Click behavior:** selects symbol (same as Watchlist).
- **Animations:** new flagged claim → row briefly highlights amber for 400ms (see §9).
- **Update strategy:** event-driven (on new verification), per the spec's update-cadence table.
- **Dependencies:** new backend endpoint, `selectedSymbol` state.
- **Acceptance criteria:**
  - [ ] Rows sorted by flag count descending, zero-flag rows visually de-emphasized but present.
  - [ ] Click transitions Focus View correctly.
  - [ ] Demo-data fallback clearly labeled, never presented as live.
  - [ ] New flags trigger the amber highlight animation.

### 5.4 Focus View — see full treatment in §6. Summary spec table entry:

- **Purpose:** the workspace's single reason to exist — turns passive browsing into active investigation.
- **Data source:** varies by sub-tab, detailed in §6.
- **Existing components to reuse:** `EarningsVerification.tsx` (Verification Radar, Evidence), `MetricPanel.tsx` (Financials).
- **New backend required:** yes, for Integrity Score and Financial Health Timeline specifically.
- Full interaction/loading/empty/error/animation spec: see §6.

### 5.5 News Radar (right, top, 180px)

- **Purpose:** curated financial news relevant to tracked/flagged companies, with recency signal.
- **Data shown:** category tag (Earnings/SEC/Fed/M&A/Guidance/Buybacks/Dividends), one-line headline, relative timestamp (2m/5m/18m/1h).
- **Data source:** **new backend endpoint** (or extension of existing news-adjacent data if the backend's `finnhub` integration already fetches company news server-side — verify before building; not confirmed present in the frontend-only architecture audit).
- **Existing component to reuse:** none directly; row layout should match Filing/Earnings Radar for visual consistency (all three are "list of timestamped items with a category tag" — consider a single generic `RadarListPanel` presentational component parameterized by category-color-map and data, to avoid three near-duplicate implementations; see §11 file plan).
- **New backend required:** yes.
- **Interactions:** click a news item → if it references a tracked company, sets `selectedSymbol`; otherwise expands inline to show a 1–2 sentence summary (no navigation away from the workspace).
- **Loading state:** skeleton rows.
- **Empty state:** "No recent news" centered message.
- **Error state:** last-known list frozen, `STALE` tag on the panel header.
- **Hover behavior:** row highlight.
- **Animations:** new item enters via a 250ms slide-in from top (see §9 "Feed item" spec — same animation family as the Intelligence Feed, for visual consistency between all "streaming list" panels).
- **Update strategy:** polled every 60s per spec's cadence table.
- **Dependencies:** new backend endpoint.
- **Acceptance criteria:**
  - [ ] New items animate in without pushing older items off-panel abruptly (smooth reflow).
  - [ ] Clicking a company-linked item updates Focus View.
  - [ ] Category tags color-coded consistently with Filing/Earnings Radar.

### 5.6 Filing Radar (right, middle, 160px)

- **Purpose:** latest SEC filings with a risk flag — a direct verification signal, not generic news.
- **Data shown:** company, form type (10-Q/10-K/8-K/etc.), timestamp, risk flag (derived from whether the filing's figures triggered a DVL correction on ingestion).
- **Data source:** backend already has SEC EDGAR ingestion (`ingestion/sec_edgar.py`, noted in the architecture report's brief mention of backend structure) and a `/v1/fundamentals/{ticker}` endpoint — **new aggregate endpoint required** to list *recent filings across all tracked companies* rather than per-ticker, since the existing endpoint is ticker-scoped.
- **Existing component to reuse:** none directly (see News Radar's note on a shared `RadarListPanel` primitive).
- **New backend required:** yes (aggregate/cross-ticker endpoint).
- **Interactions:** click → sets `selectedSymbol` and pre-selects the Focus View's Filings sub-tab.
- **Loading / empty / error states:** same pattern as News Radar.
- **Animations:** same 250ms slide-in as News Radar.
- **Update strategy:** event-driven (on new filing ingestion).
- **Dependencies:** new backend endpoint.
- **Acceptance criteria:**
  - [ ] Risk flag visually distinguishes flagged vs clean filings (color, not just text).
  - [ ] Click opens directly to the Filings sub-tab of Focus View, not just the default company view.

### 5.7 Earnings Radar (right, bottom-middle, 160px)

- **Purpose:** upcoming/live earnings awareness — tells the user when a Verification Radar update is imminent.
- **Data shown:** company, date/status (LIVE/TODAY/18m/TOM), pre/post-market indicator.
- **Data source:** **new backend endpoint** (earnings calendar — Finnhub's free tier includes an earnings calendar endpoint per the target spec's data-source table; not yet integrated anywhere in the current frontend or, as far as this audit determined, the backend).
- **Existing component to reuse:** none.
- **New backend required:** yes.
- **Interactions:** click → sets `selectedSymbol`.
- **Loading / empty / error:** same pattern as News/Filing Radar.
- **Animations:** LIVE items pulse (reuse `.live-pulse` class from `globals.css`, already defined and used elsewhere for live indicators).
- **Update strategy:** cached, refreshed every 15 minutes per spec's cadence table.
- **Dependencies:** new backend endpoint.
- **Acceptance criteria:**
  - [ ] LIVE items visually pulse using the existing `.live-pulse` utility class.
  - [ ] Click transitions Focus View correctly.

### 5.8 Sector Monitor (right, fills remaining space)

- **Purpose:** at-a-glance sector health — but sector **trust**, not sector price return (the differentiation angle called out explicitly in the target spec).
- **Data shown:** sector name, average integrity score across companies in that sector (bar chart), not the current implementation's average price change.
- **Data source:** derived from the same new Integrity Score backend support needed by Focus View (§6.5) and Watchlist's badge column, aggregated per sector.
- **Existing component to reuse:** `MarketContext.tsx`'s sector-bar JSX block (the `.map()` over `SECTORS` with the width-scaled bar) — reuse the *visual pattern* only; the underlying data must change from hardcoded price-change percentages to real integrity-score averages once available.
- **New backend required:** yes (sector-level integrity aggregation).
- **Interactions:** click a sector bar → filters Watchlist/Integrity Monitor to that sector (client-side filter, no new fetch needed) — new interaction, not present in the existing `MarketContext.tsx`.
- **Loading state:** skeleton bars.
- **Empty state:** N/A (sectors are a fixed taxonomy).
- **Error state:** if integrity aggregation is unavailable, fall back to the existing hardcoded price-change bars **with an explicit "PRICE CHANGE (DEMO)" label** rather than silently showing what looks like a trust metric but isn't — this is the one place in the whole workspace where reusing the existing component verbatim would violate the "no generic widgets" principle unless clearly labeled.
- **Hover behavior:** tooltip with company count in sector.
- **Animations:** bar width transitions smoothly (300ms ease) on data change.
- **Update strategy:** event-driven (on verification updates affecting sector composition).
- **Dependencies:** new backend endpoint, client-side sector filter state (shared with Watchlist/Integrity Monitor — see §12).
- **Acceptance criteria:**
  - [ ] Bars represent integrity, not price, once backend support lands; clearly labeled otherwise.
  - [ ] Clicking a sector filters left-column panels without a network request.

### 5.9 Intelligence Feed (bottom bar, top row, 28px collapsed / 160px expanded)

- **Purpose:** the connective tissue — a single continuous log of everything happening across the workspace (verifications, filings, news, market moves), the terminal's "pulse."
- **Data shown:** timestamped one-line events, aggregated from every other panel's activity.
- **Data source:** `WorkspaceStreamProvider` — every panel's data-fetch/update should also push a short event description into a shared feed buffer (new client-side aggregation logic; no new backend endpoint required, this is a frontend fan-in of already-fetched data).
- **Existing component to reuse:** `VerificationLog.tsx`'s staggered fade-in animation pattern (the `visibleCount` + `setInterval` reveal mechanic) and `app/page.tsx`'s `sessionEvents` state pattern (capped array, most-recent-first) — port the *pattern*, generalize the *source* from one query's pipeline to all panels.
- **New backend required:** no (client-side aggregation of existing/new panel data).
- **Interactions:** click the collapsed row (or a caret icon) → expands to 160px, multi-line, scrollable. Click again → collapses.
- **Loading state:** "Awaiting activity..." placeholder text (matches existing empty-state tone from `sessionEvents.length === 0` case in `app/page.tsx`).
- **Empty state:** same as loading state until first event arrives.
- **Error state:** N/A (client-side aggregation, no independent failure mode).
- **Hover behavior:** pauses auto-scroll while collapsed-row marquee is mid-scroll (matches `TickerBar.tsx`'s existing `hover:animation-play-state:paused` pattern — reuse that CSS approach).
- **Click behavior:** expand/collapse as above; clicking an individual feed item (in expanded state) jumps the Focus View to the relevant company if applicable.
- **Animations:** new item slides in from the right (collapsed marquee state, reusing `TickerBar.tsx`'s marquee CSS) or fades in from top (expanded list state, reusing `VerificationLog.tsx`'s stagger). Both target 250ms.
- **Update strategy:** live, on any event from any panel.
- **Dependencies:** `WorkspaceStreamProvider`, all other panels (as event sources).
- **Acceptance criteria:**
  - [ ] Every panel's meaningful state change produces exactly one feed entry (no duplicate spam).
  - [ ] Expand/collapse preserves scroll position correctly.
  - [ ] Capped buffer (suggest last 100 events) to avoid unbounded memory growth.

### 5.10 Persistent Query Input (bottom bar, bottom row, 36px)

- **Purpose:** preserves the existing `/query` verification pipeline as the workspace's "ask anything" entry point — the one interaction carried over unchanged in function, changed in presentation.
- **Data shown:** single-line input, submit affordances.
- **Data source:** N/A (input only); submission calls the existing `/query`/`/verify` pipeline exactly as today.
- **Existing component to reuse:** `QueryInput.tsx`'s textarea logic, keyboard shortcuts (Enter, Cmd/Ctrl+Enter, Escape-to-clear), and — critically — `app/page.tsx`'s `handleSubmit`/`clientDVL`/`DEMO_NUMS` routing logic, extracted per the file map's `lib/queryPipeline.ts` recommendation so this bar doesn't duplicate that logic a second time.
- **New backend required:** no — this is the one panel with zero new backend dependency; it's a straight port of working functionality.
- **Interactions:** type + Enter/click submit → runs the query pipeline; result surfaces in the Focus View (new behavior — previously results surfaced in the same column as the input; now they must route into whichever Focus View state is relevant, or a lightweight inline result toast if no company context applies).
- **Loading state:** input disabled, submit icon shows a small spinner/pulse (reuse `status-dot amber` pattern from `globals.css`).
- **Empty state:** placeholder text `"Type a question or ticker..."` per the target mockup.
- **Error state:** inline error text appears briefly below the bar (reuse the existing red-bordered error panel pattern from `app/page.tsx`, condensed to fit a single line).
- **Hover behavior:** N/A.
- **Click behavior:** submit button and the three trailing icon-buttons (`⏎` execute, `🔎` presumably "search mode," `📊` presumably "jump to metrics" per the mockup) — the latter two icons' exact behavior is **not specified in the target spec beyond the glyphs shown**; implement `🔎` as a no-op placeholder that opens the same input focus (parity with `⏎`) and `📊` as a shortcut that, if a company is selected, jumps Focus View to Financials — flag both to the product owner for confirmation before Milestone 4 polish, since the spec's ASCII mockup doesn't define their behavior precisely.
- **Animations:** none beyond the existing loading pulse.
- **Update strategy:** N/A (request/response, not streaming).
- **Dependencies:** `lib/queryPipeline.ts` (new, extracted), `ConnectionProvider` (for `backendOnline` routing).
- **Acceptance criteria:**
  - [ ] `Enter` submits, `Cmd/Ctrl+Enter` submits, `Escape` clears — all three preserved from `QueryInput.tsx`.
  - [ ] Same demo-question fast-path / LLM-path / offline-fallback routing behavior as today, verified against `DEMO_NUMS` test questions.
  - [ ] Focused via `Ctrl+F` global shortcut (see §7).
  - [ ] Never blocks the rest of the workspace while a query is in flight.

### 5.11 Focus View sub-panels (Integrity Score, Verification Radar, Financials, Evidence, Financial Health Timeline, Filings)

Specified in full in §6, not repeated here to avoid duplication — §6 is the authoritative detailed spec for all six Focus View sub-sections.

---

## 6. Dynamic Focus View — Full Specification

The Focus View is the center column's sole occupant. It has exactly two top-level states:

### 6.1 Default State (no company selected)

- Rendered on initial workspace load and whenever the user explicitly deselects (see §6.4).
- Contents, top to bottom:
  1. **Market Intelligence summary** — 2–3 lines of auto-generated text describing current top movers and sector leaders (e.g. "NVDA leads gainers at +2.3%. 3 companies flagged today, up from 1 yesterday."). Data source: derived client-side from Watchlist + Integrity Monitor data already in memory — no new fetch needed for this specific text.
  2. **Quick Stats** — three stat cards: "Claims Verified" (session or global count), "Corrections Applied," "Avg Integrity Score." Reuses the `AnimatedCounter`/`StatCard` pattern from `app/metrics/page.tsx`, extracted into `components/workspace/focus-view/QuickStats.tsx` per §4's hierarchy (this is the one piece of `/metrics` page code that migrates into the workspace, per the file map's note that this pattern is "reusable elsewhere if needed").
- No sub-tabs are shown in this state.
- Loading state: Quick Stats numbers count up from 0 on first mount (existing `AnimatedCounter` behavior, unchanged) — this is acceptable here since it's a one-time entrance animation, not a recurring loading state.

### 6.2 Company-Selected State — Structure

Triggered by `selectedSymbol !== null` (set by clicking any row in Watchlist, Integrity Monitor, News/Filing/Earnings Radar, or Sector Monitor's company-level drill-in if added later).

```
┌─────────────────────────────────────────────────────────────┐
│  TESLA INC (TSLA)                          Integrity: 61 🟨 │  ← CompanyHeader, ~56px
├─────────────────────────────────────────────────────────────┤
│ [INTEGRITY] [VERIFICATION] [FINANCIALS] [EVIDENCE] [TIMELINE] [FILINGS] │ ← tab strip, ~32px
├─────────────────────────────────────────────────────────────┤
│                                                               │
│   (active tab's content, scrollable)                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

- **CompanyHeader:** company name, ticker, and the large prominent Integrity Score (0–100, color-coded 🟩/🟨/🟥 per the spec's heatmap convention) — always visible regardless of which tab is active, since it's the anchor fact for the whole drill-down.
- **Tab strip:** six tabs — Integrity, Verification, Financials, Evidence, Timeline, Filings — styled as the existing tab-button pattern already used in `app/page.tsx`'s right-column session/errors/stats tabs and `market/page.tsx`'s metrics/earnings toggle (active tab gets `border-b border-t-{color} bg-white/[0.02]`, reuse this exact pattern).
- Default active tab on selection: **Integrity** (the composite score is the first thing worth seeing, before drilling into any one signal).

### 6.3 State Transition (Default → Company-Selected)

- No page navigation, no route change — pure client state (`selectedSymbol` lives in `WorkspacePage`, passed down as a prop or via context per §12).
- Transition animation: the Default state fades out (150ms) while the CompanyHeader + tab strip fade/slide in (200ms) — subtle, not jarring; avoid a hard cut given how central this panel is to the "keep it open all day" feel.
- Data for the newly selected company begins fetching **immediately on click**, in parallel with the transition animation — no additional user-visible delay beyond actual network latency.
- Deselection: a small "✕ Back to overview" control in the CompanyHeader area returns to Default state; also, per §7, `Escape` deselects if a company is currently focused (this is a **new** global shortcut, not present in the current app, and takes priority over `QueryInput`'s existing Escape-to-clear behavior only when the query input is not itself focused — see §7 for the precise priority rule).

### 6.4 Sub-Tab Specifications

**6.4.1 Integrity (default active tab)**
- New panel: `IntegrityScorePanel.tsx`.
- Shows: the composite score breakdown — Consistency (40% weight), SEC Agreement (30%), DVL Confidence (30%) — as three sub-bars or a small radar/bar chart, plus one sentence explaining the current score in plain language (e.g. "Score driven down by 2 unresolved SEC disagreements").
- Data source: **new backend computation** — this formula does not exist anywhere in the current frontend or (per this audit's frontend-only scope) backend. This is the single largest piece of genuinely new backend work in the whole plan.
- Loading: skeleton bars for each of the three components.
- Empty: N/A once a company is selected (score should always be computable if any verification data exists for that company); if truly no data exists for a newly-added/obscure ticker, show "Insufficient verification history for an Integrity Score yet."
- Error: if the new endpoint fails, show the existing simple `TrustScore.tsx`-style single-number/badge as a degraded fallback rather than the full breakdown, with a small "breakdown unavailable" note.

**6.4.2 Verification**
- Adapted panel: `VerificationRadar.tsx`, direct evolution of `EarningsVerification.tsx`.
- Shows: the red-flag report header (flag rate, trust breakdown bar — all ported unchanged from `EarningsVerification.tsx`), the flagged/all-claims toggle, and each claim row with its expand/collapse detail (DVL analysis, raw vs verified, claim type badge) — this entire interaction model ports essentially unchanged; the only structural change is that it now lives inside a tab rather than being the whole center panel.
- Data source: existing `getEarningsVerification()` call from `lib/api.ts`, unchanged.
- Loading/empty/error: identical to `EarningsVerification.tsx`'s existing states, ported unchanged.

**6.4.3 Financials**
- Adapted panel: `FinancialsPanel.tsx`, direct evolution of `MetricPanel.tsx`.
- Shows: the 2×2 (or expanded, if space allows in the wider Focus View column vs. the old 42–50%-width center column) grid of DVL-verified metric cards — profit margin, ROE, P/E, revenue growth — with the correction log below.
- Data source: existing `getBasicFinancials()` (Finnhub client) + `clientDVL()` — per the file map, decide whether to migrate this to the backend's (currently unused) `/market/all-metrics` for consistency with Verification's backend-sourced claims; **recommendation: migrate to backend-sourced data in Milestone 3** when the Integrity Score backend work is already underway, to avoid running two different trust-computation code paths (client DVL vs backend DVL) side-by-side in the same Focus View.
- Loading/empty/error: identical to `MetricPanel.tsx`'s existing states, ported unchanged (including its existing "DEMO DATA" / "FINNHUB LIVE" badge convention).

**6.4.4 Evidence**
- Adapted panel: `EvidencePanel.tsx`, evolution of `EarningsVerification.tsx`'s "SEC Filing Data" collapsible section (the `FundamentalCard` grid).
- Shows: SEC filing source metrics (net income, revenue, total assets, EPS, etc.) each with its DVL trust badge and filing period/date — same `FundamentalCard` component, just promoted from a collapsible sub-section of Earnings Verification into its own dedicated tab.
- Data source: existing `getFundamentals()` call from `lib/api.ts`, unchanged.
- Loading/empty/error: identical to existing pattern.

**6.4.5 Timeline**
- New panel: `FinancialHealthTimeline.tsx`.
- Shows: sparkline of the company's Integrity Score **over time** (distinct from the synthetic price sparklines elsewhere), with annotation markers at points where a discrepancy was detected or resolved (e.g. "Discrepancy detected Q2," "Recovered Q3," per the target spec's example).
- Data source: **new backend requirement** — needs historical integrity-score snapshots per company, which do not exist today (today's DVL/verification results are computed per-query, not stored as a time series). This is new backend work of similar scope to the Integrity Score itself; consider building both in the same backend milestone since the Timeline is essentially "Integrity Score, sampled over time and stored."
- Loading: skeleton sparkline shape.
- Empty: "No historical data yet — Integrity Score history begins accumulating from today" for newly-tracked companies (an honest empty state, not a fabricated backfilled history).
- Error: hide the panel content, show "Timeline unavailable" rather than falling back to a fake trend line (unlike Financials/Watchlist sparklines, this is a decision-relevant trust signal, not a price sparkline — the bar for "acceptable to fake" is higher here per the architecture report's core caution).

**6.4.6 Filings**
- New/shared panel: `FilingsPanel.tsx`, company-filtered view of the same data source as the right-column Filing Radar (§5.6), scoped to just the selected company.
- Shows: this company's filing history with risk flags, same visual pattern as Filing Radar rows but not time-scrolling/live — a static (per-load) filtered list.
- Data source: same new aggregate filings endpoint as Filing Radar, filtered client-side or via a query param by ticker.
- Loading/empty/error: consistent with Filing Radar's states.

---

## 7. Interaction Model

**Hover:** row highlight (`hover:bg-white/[0.02]`, existing pattern) on every clickable list row across all panels. Tooltips (new) on Market Pulse index rows and Sector Monitor bars only — no tooltips elsewhere, to avoid the workspace feeling fussy.

**Click:** selects a company (`selectedSymbol` state change) from any of: Watchlist row, Integrity Monitor row, News/Filing/Earnings Radar item (if company-linked), Sector Monitor bar (filters, does not select a single company). Clicking the Focus View's tab strip switches sub-tab without affecting `selectedSymbol`. Clicking the Intelligence Feed's collapsed row expands it; clicking an expanded feed item may set `selectedSymbol` if company-linked.

**Keyboard shortcuts (all new except where noted):**
| Shortcut | Action |
|---|---|
| `Ctrl+F` / `⌘F` | Focus the Persistent Query Input (new) |
| `Enter` (while input focused) | Submit query (existing, from `QueryInput.tsx`) |
| `Ctrl+Enter` / `⌘Enter` | Submit query (existing, from `QueryInput.tsx`) |
| `Escape` (input focused, has text) | Clear input text (existing, from `QueryInput.tsx`) |
| `Escape` (input not focused, company selected) | Deselect company, return Focus View to Default (new — see §6.3 priority note: only fires when the input itself doesn't have unsaved text to clear, to avoid the two Escape behaviors fighting) |
| `Ctrl+K` / `⌘K` | Open command palette / settings popover (new, stubbed Milestone 1, functional Milestone 4) |
| `↑` / `↓` (Watchlist focused) | Move selection up/down the watchlist (new — keyboard-only navigation, Milestone 4 polish item) |
| `1`–`6` (company selected) | Jump directly to Focus View tab N (new — Integrity/Verification/Financials/Evidence/Timeline/Filings in tab-strip order, Milestone 4 polish item) |

**Navigation:** entirely client-state driven within the workspace — no route changes for company selection, tab switching, or feed expand/collapse. The only real navigation events are: entering the workspace route itself, and leaving it (e.g. via the top-bar link back to legacy `/` or `/market`, if such a link is kept — see §11 for the decision on whether `/` is replaced or the workspace lives at a new path).

**Panel switching:** Focus View tab strip only; no other panel has internal tabs in this design (Market Pulse, Watchlist, etc. are single-view panels).

**Selection / deselection:** see §6.3.

**Scrolling:** each panel body scrolls independently (§3.6); the Intelligence Feed auto-scrolls its own marquee/list unless the user is hovering (pauses) or has manually scrolled up in the expanded state (in which case new items still append but do not force-scroll the user's view back down — reuse the "don't yank scroll position" consideration already implicit in `app/page.tsx`'s capped-and-prepended `sessionEvents` array, generalized here to respect manual scroll position).

**Search:** the Persistent Query Input doubles as symbol search — if the input's text exactly matches a tracked ticker (case-insensitive), pressing Enter selects that company in Focus View directly rather than routing through the DVL query pipeline. This is a **new** branch in the query-routing logic (to be added to the extracted `lib/queryPipeline.ts`, distinct from the existing `DEMO_NUMS`/advisory-detection routing).

**Query flow:** unchanged from today's `handleSubmit` logic (advisory detection → demo-question fast path → LLM path → offline fallback), just relocated per §5.10 and extended with the new ticker-search branch above.

---

## 8. Design System

All values below are extensions of the existing `tailwind.config.ts`/`globals.css` tokens documented in the architecture report — no palette replacement.

- **Typography:** JetBrains Mono only, unchanged. Workspace-specific sizes: panel headers `text-[10px] font-bold uppercase tracking-wider` (existing `.panel-header .label` class, reused verbatim); row text `text-[10px]`–`text-[11px]`; Integrity Score large display `text-[28px] font-bold` (slightly smaller than the Terminal's `text-[32px]` `TrustScore.tsx` display, to fit the CompanyHeader's more compact 56px height).
- **Spacing:** panel internal padding `p-2` to `p-2.5` (denser than existing Terminal `p-3`); inter-panel gaps `gap-[6px]` (existing pages use `gap-2` = 8px; the workspace goes tighter per its density requirement); row vertical padding `py-1.5` to `py-2` (existing Terminal rows use `py-2` to `py-2.5`).
- **Colors:** unchanged — `t-bg`/`t-surface`/`t-border`/`t-primary`/`t-secondary`/`t-muted`/`t-green`/`t-amber`/`t-red`/`t-blue`/`t-cyan`/`t-purple`, all reused from `tailwind.config.ts`. **New semantic mapping to codify:** Integrity Score bands — 🟩 HIGH = `t-green` (score ≥ 80), 🟨 MEDIUM = `t-amber` (50–79), 🟥 LOW = `t-red` (< 50). These thresholds are a product decision that should be confirmed but are specified here as the default so Claude Code doesn't need to invent them.
- **Borders:** unchanged — `border border-t-border`, `rounded` (4px), via the existing `.panel` class.
- **Corner radius:** 4px throughout (existing `.panel` class value), no exceptions for new panels.
- **Animations/transitions:** see §9 for the full inventory; general rule — entrances 150–250ms ease-out, value-flash 200ms, hover transitions 150ms (existing `transition-colors duration-150` pattern used throughout the current codebase, reused).
- **Hover:** `hover:bg-white/[0.02]` for rows (existing pattern, reused everywhere), `hover:bg-white/[0.04]` reserved for the currently-selected item's hover state to keep it visually distinct from unselected hover.
- **Focus:** input focus ring uses existing `focus:border-t-green/30` pattern from `QueryInput.tsx`'s textarea, adapted to the new single-line input.
- **Tables:** no new table component needed — the Radar panels (News/Filing/Earnings) are row-lists, not `<table>` elements, styled consistently with existing row patterns (Watchlist, Dashboard's HistoryRow) rather than the `<table>` markup used in `AblationSection.tsx`/`metrics/page.tsx`'s Robustness table (those remain confined to the legacy `/metrics` page).
- **Cards:** `.panel` class, unchanged, is the only card primitive needed.
- **Badges:** `.trust-badge` + `.trust-high`/`.trust-medium`/`.trust-low` (existing, reused verbatim) for all trust/integrity indicators across every panel — do not invent a second badge style for the Integrity Score bands; map HIGH/MEDIUM/LOW trust levels and 🟩/🟨/🟥 integrity bands onto the same three existing CSS classes.
- **Icons:** continue the existing Unicode-glyph convention (no icon library dependency introduced) — ✓ ✗ ⚠ ▲ ▼ ● ■ 🚩 📡 🔍 ⏎ 🔎 📊 ⌘ per both the existing codebase's usage and the target spec's own mockup glyphs.
- **Glow:** `.glow-green`/`.glow-amber`/`.glow-red` (existing, reused) applied to the CompanyHeader's Integrity Score container based on its band, and to Market Pulse index cards on significant moves (reusing the existing `bg-glow`/`glow-red` pattern already present in `MarketContext.tsx`).
- **Density:** ~25% less whitespace than `/market` page, per §2 — enforced via the padding/gap values specified above, not left to per-component judgment.

---

## 9. Animations

| Name | Trigger | Duration | Mechanism | Purpose |
|---|---|---|---|---|
| Market value flash | WebSocket price update changes a displayed number | 200ms | Brief background-color flash green (increase) or red (decrease) via a CSS class toggle + `setTimeout` removal, applied to Market Pulse rows and Watchlist rows | Draws the eye to what just changed without a jarring re-render |
| Integrity flag pulse | New flagged claim appears in Integrity Monitor | 400ms | Amber background pulse (`animate-pulse`-style keyframe, one-shot not infinite) on the affected row | Signals new risk information has arrived |
| Feed item slide (marquee/collapsed) | New Intelligence Feed event | 250ms | Reuse `TickerBar.tsx`'s `ticker-scroll`/marquee CSS mechanics, generalized from stock quotes to arbitrary event text | Keeps the collapsed feed feeling alive without being distracting |
| Feed item fade (expanded) | New Intelligence Feed event while expanded | 250ms | Reuse `VerificationLog.tsx`'s `animate-fade-in` + staggered `visibleCount` reveal mechanic | Matches the existing Terminal's established "log entry arriving" feel |
| Focus View transition | `selectedSymbol` changes (Default ↔ Company) | 150ms out / 200ms in | Fade + slight vertical slide (translate 4px), sequential not simultaneous, using the existing `globals.css` `fadeIn` keyframe pattern extended with a `translateY` variant | Signals a real state change (not just new data) without a hard jump-cut |
| CompanyHeader Integrity Score entrance | New company selected, score first renders | 600ms count-up | Reuse the exact `TrustScore.tsx`/`TerminalPanel.tsx` `requestAnimationFrame` eased-count-up pattern (`1 - Math.pow(1-p,3)` easing), applied to the 0–100 Integrity Score instead of a raw verified number | Visual continuity with the existing Terminal's "verified output" reveal, now applied to the new metric |
| Tab switch | User clicks a Focus View tab | 150ms | Simple crossfade (`transition-opacity duration-150`), no slide, to keep tab-switching feeling instantaneous even though it's animated | Avoids jankiness on frequent tab switching during investigation |
| Sector bar width change | New integrity aggregation data | 300ms ease | `transition-all duration-300` on bar `width` style (existing pattern already present in `MarketContext.tsx`'s sector bars, reused unchanged) | Smooth reflow, matches existing behavior |
| Live pulse (status dots, LIVE badges) | Ongoing, while status is "live"/backend online | 2s loop | Reuse existing `.live-pulse`/`animate-glow-pulse` keyframes verbatim, no changes | Established convention, do not reinvent |
| Reduced motion | User has `prefers-reduced-motion: reduce` | N/A | All of the above respect the existing global override in `globals.css` (`animation-duration: 0.01ms !important`) — verify every new keyframe added for this plan is covered by that existing blanket rule, since it targets `*`/`*::before`/`*::after` and should apply automatically, but confirm no new animation is implemented via `requestAnimationFrame` loops that bypass CSS (the two count-up animations use RAF, not CSS keyframes — these must add their own explicit reduced-motion check, mirroring how `TerminalPanel.tsx`/`TrustScore.tsx` currently do NOT check for reduced motion today; this is a pre-existing gap worth closing while touching this code, not a new requirement invented for the workspace) | Accessibility |

---

## 10. Implementation Order

### Milestone 1 — Workspace Shell + Mock/Fallback Data
**Goal:** the full 3-column + bottom-bar layout exists, every panel renders (with fallback/mock/demo data where live backend support doesn't exist yet), click-to-focus works, no live data required yet.

- **Files created:** `app/workspace/layout.tsx`, `app/workspace/page.tsx`, `components/workspace/WorkspaceTopBar.tsx`, `components/workspace/WorkspaceBottomBar.tsx`, `components/workspace/MarketPulsePanel.tsx`, `components/workspace/WatchlistPanel.tsx`, `components/workspace/IntegrityMonitorPanel.tsx`, `components/workspace/FocusView.tsx`, `components/workspace/focus-view/FocusViewDefault.tsx`, `components/workspace/focus-view/QuickStats.tsx`, `components/workspace/focus-view/FocusViewCompany.tsx`, `components/workspace/NewsRadarPanel.tsx`, `components/workspace/FilingRadarPanel.tsx`, `components/workspace/EarningsRadarPanel.tsx`, `components/workspace/SectorMonitorPanel.tsx`, `components/workspace/IntelligenceFeed.tsx`, `components/workspace/PersistentQueryInput.tsx`, `lib/queryPipeline.ts`, `lib/clientDvl.ts` (consolidation).
- **Files modified:** `tailwind.config.ts` (add any new keyframes needed for §9's Focus View transition if not expressible via existing utilities), `globals.css` (density utilities, heatmap-cell classes stubbed for Milestone 3), `app/layout.tsx` (add a nav entry point to the new workspace route — decide final routing per open question in §11).
- **Files untouched:** everything under legacy `app/page.tsx`, `app/market/page.tsx`, `app/dashboard/page.tsx`, `app/metrics/page.tsx`, and all existing `components/*.tsx` (Watchlist.tsx, MetricPanel.tsx, EarningsVerification.tsx, etc. are read/ported-from, not edited in place — see §11's exact per-file plan for the "adapt, don't rewrite" instruction, meaning: copy-and-adapt into the new workspace files, do not modify the originals, since legacy routes still depend on them unchanged).
- **Dependencies:** none beyond what's already installed (`recharts`, existing Tailwind config).
- **Testing:** manual click-through of every panel's happy path; confirm no page-level scroll exists at any viewport ≥1024px; confirm `Escape`/`Enter`/`Ctrl+Enter` still work in the new Persistent Query Input exactly as in the old `QueryInput.tsx`.
- **Completion criteria:** every panel in §5 renders with either real (where already wired, e.g. Market Pulse indices, Watchlist quotes) or clearly-labeled demo data (where new backend is pending); clicking any company-linked row anywhere updates Focus View; no console errors; matches §3's layout spec pixel-for-pixel on a 1440px-wide viewport.

### Milestone 2 — WebSocket Wiring + Existing Endpoint Integration
**Goal:** replace polling with the already-existing-but-unused `/ws/market` WebSocket; wire up every endpoint the architecture report identified as "exported but unused."

- **Files created:** `lib/workspaceStream.tsx` (`WorkspaceStreamProvider`).
- **Files modified:** `components/workspace/MarketPulsePanel.tsx`, `components/workspace/WatchlistPanel.tsx` (switch from `setInterval` polling to `WorkspaceStreamProvider` subscription), `lib/api.ts` (no functional change needed — `createMarketWebSocket()` already exists, just gets its first caller), `lib/market.ts` (resolve the redundant-Finnhub-call risk flagged in the architecture report — either retire direct client-side Finnhub calls in favor of the backend-sourced WebSocket, or explicitly justify keeping both if the backend confirmed not to double-call Finnhub).
- **Files untouched:** all Focus View sub-panels (Milestone 3 territory), all right-column Radar panels (still need new backend endpoints, Milestone 3 territory).
- **Dependencies:** confirmed backend `/ws/market` behavior (already exists per architecture report — verify it sends the shape `WorkspaceStreamProvider` expects; adjust the provider's parsing, not the backend, if there's a mismatch, unless the backend also needs to add fields like the "verifications pending" count from §5.1).
- **Testing:** disconnect/reconnect the WebSocket manually (e.g. via backend restart) and confirm the STALE-tag fallback behavior specified in §5.1 activates correctly; confirm no duplicate Finnhub calls happen simultaneously from client and server.
- **Completion criteria:** Market Pulse and Watchlist update via WebSocket push, not polling; `createMarketWebSocket()` and previously-unused `lib/api.ts` exports now have at least one real caller each (or are explicitly still marked unused pending a documented reason).

### Milestone 3 — New Backend-Dependent Panels
**Goal:** everything genuinely new gets real backend support and stops being demo data — Integrity Score, Integrity Monitor, Financial Health Timeline, News/Filing/Earnings Radar, Sector Monitor's integrity aggregation.

- **Files created:** none new on the frontend beyond what Milestone 1 already stubbed — this milestone is primarily about connecting Milestone-1 UI to Milestone-3 backend endpoints (backend file changes are out of scope for this frontend-focused plan, but each frontend file below has a corresponding backend dependency called out in §5's per-panel specs).
- **Files modified:** `components/workspace/IntegrityMonitorPanel.tsx`, `components/workspace/focus-view/IntegrityScorePanel.tsx`, `components/workspace/focus-view/FinancialHealthTimeline.tsx`, `components/workspace/NewsRadarPanel.tsx`, `components/workspace/FilingRadarPanel.tsx`, `components/workspace/EarningsRadarPanel.tsx`, `components/workspace/SectorMonitorPanel.tsx`, `lib/api.ts` (add typed client functions for every new endpoint).
- **Files untouched:** shell/layout files from Milestone 1, WebSocket provider from Milestone 2 (Market Pulse/Watchlist don't need further changes here unless the "verifications pending" field requires extending the WebSocket payload, in which case `lib/workspaceStream.tsx` gets a small addition).
- **Dependencies:** new backend endpoints (Integrity Score computation, per-company and per-sector aggregation, cross-ticker filings/news/earnings-calendar endpoints) — these are backend engineering work not covered by this frontend plan's file list, but every frontend file above is blocked on its corresponding endpoint existing.
- **Testing:** for each panel, verify the documented error-state fallback (§5) actually triggers correctly when its endpoint is unavailable, not just the happy path.
- **Completion criteria:** every "New backend required: yes" panel in §5 shows real (not demo-labeled) data end-to-end; every panel's specified error/empty state has been manually triggered and confirmed correct at least once.

### Milestone 4 — Workspace UX Polish
**Goal:** the interaction-model niceties from §7 that aren't load-bearing for basic functionality — keyboard navigation, command palette, saved workspaces, compare mode.

- **Files created:** `components/workspace/CommandPalette.tsx` (wired to the `Ctrl+K` stub from Milestone 1), any saved-workspace persistence layer (likely reusing `lib/history.ts`'s localStorage pattern, or the previously-unused Supabase `/v1/history/*` endpoints per the architecture report's note that they exist but aren't called — this is a good use for them).
- **Files modified:** `components/workspace/WatchlistPanel.tsx` (arrow-key navigation), `components/workspace/FocusView.tsx` (1–6 tab-jump shortcuts), `components/workspace/WorkspaceTopBar.tsx` (functional settings button).
- **Files untouched:** everything else.
- **Dependencies:** Milestones 1–3 complete and stable.
- **Testing:** full keyboard-only click-through (no mouse) covering every shortcut in §7's table.
- **Completion criteria:** every keyboard shortcut in §7 functions; saved workspaces (if built) persist across reloads; the two ambiguous Persistent Query Input icon-buttons (`🔎`/`📊`, flagged in §5.10) have been resolved with the product owner and implemented per that resolution.

---

## 11. Exact File Modification Plan

This section makes every file placement decision explicit, resolving the file map's `NEW` recommendations into exact final paths and clarifying the "adapt, don't rewrite" instruction with a concrete rule: **existing components listed as MODIFY/REPLACE in `FRONTEND_FILE_MAP.md` are never edited in place. Their logic is ported into new files under `components/workspace/`. The original files remain untouched so the legacy `/` and `/market` routes continue working unmodified.**

**Open routing question to resolve before Milestone 1 begins (flagged, not decided here):** does the workspace become the new `/` (replacing today's Terminal as the app's default landing experience), or does it live at a new path like `/workspace` with `/` and `/market` demoted to a "Legacy Demo" nav entry? Both `UI_ARCHITECTURE_REPORT.md` §9 and this plan assume the latter (new path, legacy routes preserved) since it's lower-risk and reversible, but this is a product decision, not an engineering one — confirm before Milestone 1's nav-link changes land.

### Create
| New file | Ported from | Notes |
|---|---|---|
| `app/workspace/layout.tsx` | — | New dedicated layout, §3.1 |
| `app/workspace/page.tsx` | Structural inspiration: `app/market/page.tsx`'s 3-column grid pattern | Owns `selectedSymbol`, feed-expanded state (§12) |
| `components/workspace/WorkspaceTopBar.tsx` | Structural inspiration: `app/layout.tsx`'s header | — |
| `components/workspace/WorkspaceBottomBar.tsx` | — | Composes `IntelligenceFeed` + `PersistentQueryInput` |
| `components/workspace/MarketPulsePanel.tsx` | `components/MarketContext.tsx` (index-card block only) | §5.1 |
| `components/workspace/WatchlistPanel.tsx` | `components/Watchlist.tsx` (near-total port) | §5.2 |
| `components/workspace/IntegrityMonitorPanel.tsx` | — (genuinely new) | §5.3 |
| `components/workspace/FocusView.tsx` | — (new composition root) | §6 |
| `components/workspace/focus-view/FocusViewDefault.tsx` | — (new) | §6.1 |
| `components/workspace/focus-view/QuickStats.tsx` | `app/metrics/page.tsx`'s `StatCard`/`AnimatedCounter` | §6.1 |
| `components/workspace/focus-view/FocusViewCompany.tsx` | — (new composition root) | §6.2 |
| `components/workspace/focus-view/IntegrityScorePanel.tsx` | — (genuinely new) | §6.4.1 |
| `components/workspace/focus-view/VerificationRadar.tsx` | `components/EarningsVerification.tsx` (claims-list portion) | §6.4.2 |
| `components/workspace/focus-view/FinancialsPanel.tsx` | `components/MetricPanel.tsx` (near-total port) | §6.4.3 |
| `components/workspace/focus-view/EvidencePanel.tsx` | `components/EarningsVerification.tsx` (`FundamentalCard` section) | §6.4.4 |
| `components/workspace/focus-view/FinancialHealthTimeline.tsx` | — (genuinely new) | §6.4.5 |
| `components/workspace/focus-view/FilingsPanel.tsx` | Shares logic with `FilingRadarPanel.tsx` | §6.4.6 |
| `components/workspace/NewsRadarPanel.tsx` | — (genuinely new; consider a shared `RadarListPanel` presentational base, see §5.5) | §5.5 |
| `components/workspace/FilingRadarPanel.tsx` | — (genuinely new) | §5.6 |
| `components/workspace/EarningsRadarPanel.tsx` | — (genuinely new) | §5.7 |
| `components/workspace/SectorMonitorPanel.tsx` | `components/MarketContext.tsx` (sector-bar block only) | §5.8 |
| `components/workspace/IntelligenceFeed.tsx` | `components/VerificationLog.tsx` (stagger animation), `app/page.tsx` (`sessionEvents` pattern) | §5.9 |
| `components/workspace/PersistentQueryInput.tsx` | `components/QueryInput.tsx` (input + shortcuts) | §5.10 |
| `lib/workspaceStream.tsx` | `lib/connection.tsx` (Context pattern) | §12 |
| `lib/queryPipeline.ts` | `app/page.tsx` (`handleSubmit`/`advancePipeline`/`clientDVL`/`DEMO_CASES`) | §5.10, §7 |
| `lib/clientDvl.ts` | Consolidates `lib/dvl.ts` + `app/page.tsx`'s inline `clientDVL` | Per file map's REPLACE note |
| `components/workspace/RadarListPanel.tsx` (optional, recommended) | — | Shared presentational base for News/Filing/Earnings Radar if the three end up near-identical in practice |

### Modify (existing files, small targeted changes only)
| File | Change |
|---|---|
| `app/layout.tsx` | Add nav entry to the workspace route; switch `<a>` tags to `next/link` per architecture report §9 risk #4 |
| `tailwind.config.ts` | Add any keyframes §9's animations need that aren't expressible with existing utilities (e.g. a `translateY` fade variant for the Focus View transition, if `fadeIn` isn't reused as-is) |
| `globals.css` | Add density utility classes (`.panel-compact` per file map), heatmap-cell classes if a Trust Heatmap panel is added later (not in this plan's panel list — the spec's "Left column: Integrity Monitor" replaces the earlier draft's separate Trust Heatmap concept; confirm this consolidation is intentional before building a separate heatmap component) |
| `lib/api.ts` | Add typed functions for every new backend endpoint identified in §5/§6 (Integrity Score, cross-ticker filings/news/earnings-calendar, sector aggregation) |
| `lib/market.ts` | Resolve redundant-Finnhub-call risk per Milestone 2 |
| `package.json` | Remove dead `@clerk/nextjs`/`@clerk/themes` deps (confirm with team first, per architecture report) |

### Replace
None — no existing file is wholesale replaced in place. `lib/dvl.ts` is superseded by `lib/clientDvl.ts` but the file map's own guidance is to consolidate via a new file, not edit the old one in place (since `MetricPanel.tsx`, untouched, still imports it) — **decision:** once `FinancialsPanel.tsx` (the new workspace copy) is ported and migrated to backend-sourced DVL per §6.4.3, the *legacy* `MetricPanel.tsx` continues importing the old `lib/dvl.ts` unchanged, since it's not being touched. `lib/dvl.ts` therefore is not deleted or replaced — it simply stops being the pattern for *new* code.

### Archive (confirmed untouched)
`app/page.tsx`, `app/market/page.tsx`, `app/dashboard/page.tsx`, `app/metrics/page.tsx`, `app/og/route.tsx`, `components/AblationSection.tsx`, `components/ErrorTaxonomy.tsx`, `components/HeroNetwork.tsx`, `components/MetricsChart.tsx` (dead code, still not deleted), `components/NavModeToggle.tsx` (superseded in spirit by the new top bar's nav, but the old component is not deleted since legacy routes still use it), `components/DVLReport.tsx` (kept, reused by reference from the new Focus View later if desired, not modified), `components/QueryInterpretation.tsx`, `components/TerminalPanel.tsx`, `components/TickerBar.tsx`, `components/TrustScore.tsx`, `components/VerificationLog.tsx`, `components/Watchlist.tsx`, `components/MarketContext.tsx`, `components/MetricPanel.tsx`, `components/EarningsVerification.tsx`, `lib/history.ts`, `lib/dvl.ts`, `lib/connection.tsx` (used, not modified — only wrapped by the new provider), `middleware.ts`, `next.config.mjs`, `public/widget.js`.

---

## 12. Component Dependency Map

| Component | Imports | Children | State owned | Shared context consumed | API/data usage |
|---|---|---|---|---|---|
| `WorkspacePage` | all top-level workspace components, `lib/workspaceStream`, `lib/connection` | `WorkspaceTopBar`, `LeftColumn` panels, `FocusView`, `RightColumn` panels, `WorkspaceBottomBar` | `selectedSymbol: string \| null`, `feedExpanded: boolean`, `activeSectorFilter: string \| null` | — (this is the provider root's child, consumes both contexts) | none directly — delegates to children |
| `WorkspaceStreamProvider` | `lib/api.ts` (`createMarketWebSocket`) | wraps `ConnectionProvider` + `WorkspacePage` | WebSocket connection object, latest quotes/events buffer | — | `/ws/market` |
| `MarketPulsePanel` | `lib/api.ts` types | `IndexCard[]` (inline) | none (reads from context) | `WorkspaceStreamProvider` | `/market/indices` (first paint), WS thereafter |
| `WatchlistPanel` | `lib/api.ts` types | `WatchlistRow[]` (inline) | none (reads from context, writes `selectedSymbol` via prop callback from `WorkspacePage`) | `WorkspaceStreamProvider` | quotes via WS; integrity badge via new endpoint (M3) |
| `IntegrityMonitorPanel` | new API types | `FlaggedCompanyRow[]` (inline) | none | none directly | new aggregate-flags endpoint (M3) |
| `FocusView` | `focus-view/*` | `FocusViewDefault` or `FocusViewCompany` (conditional on `selectedSymbol`) | `activeTab` (which of the 6 sub-tabs) | receives `selectedSymbol` as prop from `WorkspacePage` | none directly (delegates to children) |
| `FocusViewDefault` | `QuickStats` | `QuickStats`, inline Market Intelligence summary | none | reads Watchlist/Integrity Monitor data (via prop drilling or a small shared derived-state hook — implementation detail, either is acceptable) | none directly |
| `FocusViewCompany` | `IntegrityScorePanel`, `VerificationRadar`, `FinancialsPanel`, `EvidencePanel`, `FinancialHealthTimeline`, `FilingsPanel` | the six sub-panels (only active tab mounted, or all mounted with `hidden` — recommend only-active-mounted to avoid 6 simultaneous fetches per company selection) | none (receives `symbol`, `activeTab` as props) | none | none directly |
| `IntegrityScorePanel` | new API types | — | none | none | new Integrity Score endpoint (M3) |
| `VerificationRadar` | `lib/api.ts` (`getEarningsVerification`) | `ClaimRow[]` (ported from `EarningsVerification.tsx`) | `viewMode` (flags/all), per-row `expanded` | none | `/v1/earnings/{ticker}` (existing, unchanged) |
| `FinancialsPanel` | `lib/api.ts` (`getBasicFinancials` or migrated backend call per M3), `lib/clientDvl.ts` or backend DVL | `MetricCard[]` (inline) | `metrics`, `loading` | none | Finnhub client (current) → migrate to `/market/all-metrics` (M3) |
| `EvidencePanel` | `lib/api.ts` (`getFundamentals`) | `FundamentalCard[]` (ported) | none | none | `/v1/fundamentals/{ticker}` (existing, unchanged) |
| `FinancialHealthTimeline` | new API types | — | none | none | new historical integrity-score endpoint (M3) |
| `FilingsPanel` | shared with `FilingRadarPanel` | — | none | none | new cross-ticker filings endpoint, ticker-filtered (M3) |
| `NewsRadarPanel` | new API types (or shared `RadarListPanel`) | `NewsItemRow[]` (inline) | none | writes `selectedSymbol` via callback if item is company-linked | new news endpoint (M3) |
| `FilingRadarPanel` | new API types | `FilingItemRow[]` (inline) | none | writes `selectedSymbol` via callback | new cross-ticker filings endpoint (M3) |
| `EarningsRadarPanel` | new API types | `EarningsItemRow[]` (inline) | none | writes `selectedSymbol` via callback | new earnings-calendar endpoint (M3) |
| `SectorMonitorPanel` | new API types | `SectorBar[]` (inline) | writes `activeSectorFilter` via callback | reads integrity aggregation | new sector-aggregation endpoint (M3) |
| `IntelligenceFeed` | none external (aggregates via props/context from all other panels' emitted events) | `FeedItem[]` (inline) | `feedBuffer` (capped array), reads `feedExpanded` from `WorkspacePage` | `WorkspaceStreamProvider` (if events are centralized there) or a lighter dedicated feed-event bus | none directly — client-side aggregation only |
| `PersistentQueryInput` | `lib/queryPipeline.ts`, `lib/connection` (`useConnection`) | none | `inputValue`, `isLoading` | `ConnectionProvider` (`backendOnline`) | `/query`, `/verify` (existing, via extracted pipeline) |

**Note on `IntelligenceFeed`'s event sourcing:** the cleanest implementation is for every other panel component to call a shared `emitFeedEvent(description)` function (exposed from `WorkspaceStreamProvider` or a sibling lightweight context) whenever it receives new data worth logging, rather than `IntelligenceFeed` polling every other panel's state directly. This keeps panels decoupled — `IntelligenceFeed` doesn't need to import or know about every other panel's internals, it just listens to one shared event stream. Claude Code should implement this as a small `pushEvent`/`useFeedEvents` pair alongside `lib/workspaceStream.tsx`, not as direct component-to-component coupling.

---

## 13. Acceptance Criteria (Exhaustive Checklist)

**Layout**
- [ ] Workspace renders with zero page-level scroll at ≥1280px viewport width.
- [ ] Three-column grid uses fixed 280px / fluid / fixed 300px widths exactly.
- [ ] Bottom bar is exactly 64px (28px feed + 36px input) collapsed, expands to 196px (160px + 36px) when feed is expanded.
- [ ] 1024–1279px viewport collapses left column to a 56px icon rail without breaking any interaction.
- [ ] <1024px viewport shows the "not supported" notice, no broken partial layout.
- [ ] Every panel scrolls independently; no panel's overflow affects another panel's layout.

**Panels — presence & data**
- [ ] Market Pulse: 8 line items (S&P, NASDAQ, VIX, 10Y, BTC, Gold, Oil, USD/INR) + verifications-pending line (or honest placeholder).
- [ ] Watchlist: renders all tracked symbols, sparkline present, integrity badge present or gracefully omitted.
- [ ] Integrity Monitor: sorted descending by flag count, zero-flag companies shown de-emphasized not hidden.
- [ ] Focus View Default: Market Intelligence summary text + 3 Quick Stats cards.
- [ ] Focus View Company: CompanyHeader + 6-tab strip, Integrity tab active by default on selection.
- [ ] News/Filing/Earnings Radar: each shows timestamped, categorized/typed rows with correct relative-time formatting.
- [ ] Sector Monitor: bars represent integrity (or explicitly-labeled demo price-change fallback).
- [ ] Intelligence Feed: aggregates events from at least Market Pulse, Watchlist, Integrity Monitor, and Focus View selection changes.
- [ ] Persistent Query Input: present, always visible, never obscured by any other panel.

**Interactions**
- [ ] Clicking any company-linked row in any panel (Watchlist, Integrity Monitor, News/Filing/Earnings Radar) updates `selectedSymbol` and transitions Focus View correctly.
- [ ] Sector Monitor bar click filters Watchlist/Integrity Monitor without a network request.
- [ ] Focus View tab strip switches sub-tab content without affecting `selectedSymbol`.
- [ ] "✕ Back to overview" control and `Escape` (per priority rule in §7) both correctly deselect and return to Default state.
- [ ] Intelligence Feed collapse/expand toggle works both directions, preserves scroll position on collapse→expand.

**Keyboard shortcuts**
- [ ] `Ctrl+F`/`⌘F` focuses Persistent Query Input from anywhere in the workspace.
- [ ] `Enter` and `Ctrl+Enter`/`⌘Enter` both submit from the query input, matching legacy `QueryInput.tsx` behavior exactly.
- [ ] `Escape` clears input text when input has unsaved text and is focused; deselects company when input is empty/unfocused and a company is selected; does neither destructively when both conditions could apply (input focused AND company selected AND input has text — input-clear takes priority per §7).
- [ ] `Ctrl+K`/`⌘K` opens the command palette/settings stub (Milestone 1) or full palette (Milestone 4).
- [ ] Arrow-key Watchlist navigation and 1–6 tab-jump shortcuts function (Milestone 4).

**Loading / empty / error states**
- [ ] Every panel listed in §5/§6 has its specified loading state verified to trigger on slow/first load (not just assumed).
- [ ] Every panel's empty state renders the exact specified copy/behavior, not a generic blank area.
- [ ] Every panel's error/stale state is manually triggered (e.g. by killing the backend or WebSocket) and confirmed to degrade as specified, never to a blank or broken panel.
- [ ] No panel silently fabricates data in an error state where §5/§6 specifies an honest empty/error message instead (Financial Health Timeline and Integrity Score are the two panels with zero tolerance for fake fallback data — verify these two specifically).

**Animations**
- [ ] All nine animations in §9's table are implemented with the specified trigger and duration.
- [ ] `prefers-reduced-motion: reduce` correctly disables/shortens every animation, including the two RAF-based count-up animations (Market Pulse/Watchlist value flash is CSS-based and covered by the existing global rule; CompanyHeader Integrity Score count-up is RAF-based and needs its own explicit check added, per §9's note).

**Update strategies**
- [ ] Market Pulse & Watchlist update live via WebSocket (Milestone 2), not polling, once Milestone 2 is complete.
- [ ] Integrity Monitor, Sector Monitor updates are event-driven (on new verification data), not time-polled.
- [ ] News Radar polls at 60s, Earnings Radar caches/refreshes at 15min, matching the spec's cadence table exactly.
- [ ] Financial Health Timeline and per-company data in Focus View fetch on-demand (on company selection), not preemptively for all companies.

**Data integrity / honesty**
- [ ] No new synthetic/fabricated data is introduced beyond what already exists (sparklines) without an explicit visual "demo"/"illustrative" label, per the architecture report's core caution.
- [ ] Sector Monitor's fallback state is clearly labeled "PRICE CHANGE (DEMO)" if integrity aggregation is unavailable, never presented as a trust metric.
- [ ] Financial Health Timeline shows an honest "no history yet" empty state rather than a backfilled fake trend for new companies.

**File hygiene**
- [ ] No existing file listed in §11's "Archive" table has been modified.
- [ ] Every file listed in §11's "Create" table exists at its specified path.
- [ ] `lib/dvl.ts` and the inline `clientDVL` in legacy `app/page.tsx` remain untouched; new code exclusively uses `lib/clientDvl.ts`.
- [ ] `components/MetricsChart.tsx` remains present but unimported (not deleted, per the standing instruction to only report dead code, not remove it, until the team confirms).
