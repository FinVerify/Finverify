# FinVerify Terminal — Workspace UI Inspection & Implementation Blueprint

**Repo inspected:** `github.com/FinVerify/Finverify` (main, current HEAD)
**Scope:** Read-only inspection. No files modified, no commits made, no dependencies installed.
**Inputs used:** repo source, `planning/UI_ARCHITECTURE_REPORT.md`, `planning/UI_IMPLEMENTATION_PLAN.md`, target screenshot (Workspace v1.3), current screenshot (Terminal/Market v1.2), and the uploaded `antigravity_prompts.md` task brief.

---

## 1. Executive Assessment

Two claims in the task brief do not match the repository as it currently exists. Both need to be resolved before any prompt is handed to an implementation agent, because they change what "Workspace-only, don't touch anything else" actually means in practice.

**Conflict A — Route migration is not done.**
The brief states `/` → Workspace, `/terminal` → Verify, `/market` → Market, `/metrics` → Research, `/dashboard` → Dashboard, and says this is "DONE." In the actual repo:
- `/` (`app/page.tsx`) is still the **original Terminal/DVL query demo** — the same page shown in your "current" screenshot, with the `TERMINAL | MARKET` pill toggle in the header.
- The Workspace lives at its own route, **`/workspace`** (`app/workspace/page.tsx`), not at `/`.
- **There is no `/terminal` route at all** — no `app/terminal/` directory exists anywhere.
- `/market`, `/metrics`, `/dashboard` do exist and match the brief.

So the real current routing is: `/` = Terminal (old), `/workspace` = Workspace, `/market` = Market, `/metrics` = Research, `/dashboard` = Dashboard, with **no route currently named "Verify."**

**Conflict B — The responsive fix described as tested at 1440/1280/1200/1024/900/768/600/390px does not exist in code.**
`app/workspace/page.tsx` still uses the pre-fix pattern: a single Tailwind `lg:` breakpoint (1024px, the Tailwind default — there are no custom 1280/1200/900/600 breakpoints defined in `tailwind.config.ts`). Below 1024px the page renders **only** a "⚠ VIEWPORT TOO NARROW" panel with a link to `/market` (`app/workspace/page.tsx`, `lg:hidden` block); the grid, alert banner, and bottom bar are all `hidden lg:*` and render nothing below 1024px. There is no 1024–1279px compact layout and no stacked layout — the binary "blocker vs. full 3-column grid" behavior the brief says was removed is exactly what's still there.

I'm flagging these rather than silently working around them, per the brief's own instruction to surface spec/reality conflicts. Practically, this means:
- The Antigravity prompt should not assume Workspace already lives at `/` — if you want it there, that's a real (small) routing change, not a no-op.
- Responsive work for Workspace is **not** a "refinement pass" — it's still an open Phase 1-level task, and should be sequenced accordingly (see §12).

**The good news:** aside from those two items, the Workspace is much closer to the target screenshot than the brief assumes. The center-column world map (`GlobalTransactionMonitor.tsx`) is close to pixel-parity with the target already — same city list, same dollar figures, same legend, same "GLOBAL STATS (24H)" box, same embedded command bar. The right column (News/Filing/Earnings/Sector) is structurally complete. The design token system (`t-*` colors, `.panel`/`.trust-badge` primitives, JetBrains Mono) is shared and consistent. The real gap is concentrated in one place: **everything the target shows below the map** (Verification Pulse, Recent Activity / Needs Attention / Coverage, Live Verification Trace) doesn't exist yet, and the left-column Integrity Monitor and Watchlist need visual/data work. See §5.

I also found a reference conflict: the brief says to treat `docs/antigravity_prompts.md` as "the primary design/specification reference," but **no such file exists in the repo** (searched exhaustively). What does exist, and is clearly the actual living spec — it's cited by section number directly in code comments (e.g. `FocusView.tsx`: *"Per §6 of UI_IMPLEMENTATION_PLAN.md"*) — is `planning/UI_IMPLEMENTATION_PLAN.md` (736 lines) alongside `planning/UI_ARCHITECTURE_REPORT.md` (314 lines) and `planning/FRONTEND_FILE_MAP.md`. Antigravity should be pointed at those three files, not at a nonexistent `docs/antigravity_prompts.md`.

---

## 2. Current Frontend Architecture

- **Stack:** Next.js 14.2 (App Router), React 18, TypeScript, Tailwind 3. No state library — `useState`/`useEffect`/one React Context (`ConnectionProvider` in `lib/connection.tsx`) for backend health.
- **No map/geo library** — the world map is a hand-authored SVG with hardcoded coordinates (`CITIES` array, viewBox 0–1000 / 0–500) in `GlobalTransactionMonitor.tsx`. No mapping dependency to preserve or avoid duplicating.
- **No icon library** — icons throughout are Unicode glyphs/emoji (▶ ✓ ⚠ 🕐 🔒 ⧉), not `lucide-react` or similar.
- **Charts:** `recharts` only (AreaChart/LineChart sparklines). Already a dependency; sufficient for everything in the target screenshot.
- **Fonts:** `@fontsource/jetbrains-mono` (self-hosted, already matches target's monospace terminal typography).
- Dead dependencies: `@clerk/nextjs`, `@clerk/themes` are still listed in `package.json` but auth was fully stripped (confirmed via `middleware.ts` comment). Not a Workspace concern, but worth a one-line note in the final report to whoever eventually does dependency cleanup — do not remove during Workspace work, out of scope.

### Route tree (actual, not per the brief)

```
RootLayout (app/layout.tsx)
├── ConnectionProvider
├── <header> — logo, "v1.2", NavModeToggle (Terminal|Market pill), NavHealthIndicator,
│              links: WORKSPACE (/workspace), DASHBOARD (/dashboard), RESEARCH (/metrics)
├── <TickerBar />
└── <main>
    ├── /            → app/page.tsx            Terminal (old DVL query demo, 662 lines)
    ├── /workspace    → app/workspace/page.tsx  Workspace (the target of this project)
    ├── /market       → app/market/page.tsx     Market Mode
    ├── /dashboard    → app/dashboard/page.tsx  Query history
    ├── /metrics      → app/metrics/page.tsx    Research/paper results
    └── /og           → app/og/route.tsx        OG image (not a page)
```

No `/terminal` route exists. If "Verify" is meant to be the old Terminal page under a new name/path, that's a routing decision this report cannot make for you — flagged for a decision, not resolved.

---

## 3. Current Workspace Architecture

`app/workspace/page.tsx` owns one piece of state — `selectedSymbol` — and composes:

```
WorkspacePage (app/workspace/page.tsx)
├── MarketAlertBanner            components/workspace/MarketAlertBanner.tsx   — static, hardcoded 5-item ALERTS array
├── [3-column grid, lg: only — no responsive variants below 1024px]
│   ├── Left column (280px)
│   │   ├── MarketPulsePanel     components/workspace/MarketPulsePanel.tsx    — live (getMarketIndices), fallback data
│   │   ├── WatchlistPanel       components/workspace/WatchlistPanel.tsx      — live quotes, 30s poll, DEMO badge when offline
│   │   └── IntegrityMonitorPanel components/workspace/IntegrityMonitorPanel.tsx — 100% static DEMO_DATA, no fetch at all
│   ├── Center column (fluid)
│   │   └── FocusView            components/workspace/FocusView.tsx
│   │       ├── default state: renders ONLY <GlobalTransactionMonitor />, fills 100% of center column
│   │       └── selected state: company header + 6-tab strip (Integrity/Verification/Financials/Evidence/Timeline/Filings),
│   │                            reusing EarningsVerification.tsx and MetricPanel.tsx
│   │           GlobalTransactionMonitor  components/workspace/GlobalTransactionMonitor.tsx (365 lines)
│   │             — SVG world map, city nodes, animated arcs, legend, GLOBAL STATS (24H) box,
│   │               sector filter tabs, and an embedded command-bar input ("Ask FinVerify anything...")
│   │               with quick-action buttons. All data hardcoded (CITIES, ARCS arrays).
│   └── Right column (300px)
│       ├── NewsRadarPanel       components/workspace/RightColumnPanels.tsx   — static
│       ├── FilingRadarPanel     components/workspace/RightColumnPanels.tsx   — static
│       ├── EarningsRadarPanel   components/workspace/RightColumnPanels.tsx   — static (renamed to "Earnings Calendar" per code comment)
│       └── SectorMonitorPanel   components/workspace/RightColumnPanels.tsx   — static
└── WorkspaceBottomBar           components/workspace/WorkspaceBottomBar.tsx  — status footer only (online/data sources/last updated/connection/sparkline)
```

**Dead file found:** `app/workspace/WorkspaceTopBar.tsx` (18 lines) is not imported anywhere in the codebase (confirmed by grep across all `.tsx`). The component actually in use is `components/workspace/WorkspaceTopBar.tsx` (55 lines) — but that one *also* isn't imported into `app/workspace/page.tsx` (the page inherits the root layout's header instead, per the comment in `app/workspace/layout.tsx`: *"Now inherits root layout's header + TickerBar."*). So there are **two** unused `WorkspaceTopBar` files. Flag for Antigravity: don't edit either without first confirming with the user whether a dedicated Workspace-only top bar (distinct from the root nav) is actually wanted — right now Workspace shares the same header as Terminal/Market/Dashboard/Research, which is why your current screenshot's nav doesn't match the target's `WORKSPACE  VERIFY  MARKET  RESEARCH` pill design at all.

---

## 4. Target Workspace Architecture (from screenshot)

Reading top to bottom, left to right:

- **Global shell:** `FINVERIFY TERMINAL  v1.3` wordmark, then nav pills `WORKSPACE  VERIFY  MARKET  RESEARCH` (Workspace active), right-aligned `MODEL: llama-3.1-8b-instant`, live dot, `SYSTEM HEALTH — ALL SYSTEMS OPERATIONAL`, notification bell with badge, logo mark.
- **Ticker strip:** scrolling row of symbol/price/change chips (unchanged in spirit from current).
- **Market alert banner:** amber, scrolling, `● MARKET ALERTS` tag + timestamped items + `VIEW ALL (8)`.
- **Left column:** Market Pulse (chart + S&P 500/NASDAQ/VIX row) → Watchlist (8-row table with a colored verif.-status dot per row, `EDIT`/`+ ADD SYMBOL`/`VIEW ALL`) → Integrity Monitor (`DEMO` tag, 4 stat rows, `VIEW INTEGRITY DASHBOARD`).
- **Center column:**
  1. Global Transaction Monitor (map) — **already close to parity**, see §5.
  2. **Verification Pulse** stat strip — 5 big numbers: Claims Checked, Verified, Corrected, Conflicts, Unresolved, each with a small % delta.
  3. Three-panel row: **Recent Verification Activity** (live feed, checkmark/warning icons) · **Needs Attention** (5 items, severity tags HIGH/MEDIUM/LOW) · **Verification Coverage** (per-company table: Verified/Corrected/Conflicts/Trust Score).
  4. **Live Verification Trace** — a horizontal 6-step pipeline (Claim Extracted → Entity Resolved → Evidence Retrieved → Calculation Reconstructed → Constraints Check → Result), each step a small card with a timestamp.
  5. **Command bar** — full-width, `Analyze Apple 10-Q filing` chip + `Ask anything or select an action...` input + send button, with 4 quick-action buttons below (Verify a Claim / Analyze Filing / Check Earnings / Upload Document).
- **Right column:** News Radar → Filing Radar → Earnings Calendar → Sector Monitor. Structurally matches current already.
- **Bottom status bar:** Workspace Online / Data Sources 28/28 Active / Last Updated / Connection Secure / System Status — matches current `WorkspaceBottomBar` closely.

---

## 5. Workspace Current → Target Gap Analysis

| Area | Current | Target | Gap | Files involved | Risk |
|---|---|---|---|---|---|
| **A. Global shell** | Root layout header shared across all 5 routes; `TERMINAL \| MARKET` pill, not workspace-aware | Dedicated `WORKSPACE VERIFY MARKET RESEARCH` pill nav + model/health status on the right | Full nav redesign, and it must not break Terminal/Market/Dashboard/Research which share this same header | `app/layout.tsx`, `components/NavModeToggle.tsx`, `components/NavHealthIndicator.tsx` | **HIGH** — this is a shared component; any change ripples to every route |
| **B. Navigation** | `<a>` tags, full page reload per nav click; no active-route highlighting logic for 4 pill states | Persistent pill nav with active-state highlighting for 4 routes | Needs route-aware active state (e.g. `usePathname()`), ideally `next/link` | `app/layout.tsx` | MEDIUM |
| **C. Header (model/health)** | `NavHealthIndicator` exists but format/position doesn't match target's `MODEL: ... ● LIVE / SYSTEM HEALTH` block | Right-aligned model + live dot + system health + bell | Needs inspection of `NavHealthIndicator.tsx` internals before deciding modify-vs-rebuild | `components/NavHealthIndicator.tsx` | LOW |
| **D. Main grid** | `grid-cols-[280px_1fr_300px]`, `lg:` only, no intermediate breakpoints | Same 3-column shape, functional at 1024–1279 and stacked below | Add compact + stacked variants (see §8) | `app/workspace/page.tsx` | **HIGH** (this is the "responsive fix" that isn't actually done) |
| **E. Hero/map area** | `GlobalTransactionMonitor.tsx` — SVG map, arcs, legend, stats box, sector tabs, embedded command bar | Same map, same numbers, same legend | **Near parity already.** Minor: confirm sector-tab row still present/matches; command bar here is redundant with target's separate bottom command bar (see M) | `components/workspace/GlobalTransactionMonitor.tsx` | LOW |
| **F. Market Pulse** | Live (`getMarketIndices`) w/ fallback, `SPX/NDX/VIX` labels, 5 timeframe tabs | Same shape, labels read "S&P 500 / NASDAQ / VIX" | Cosmetic label mapping only — do not touch data logic | `components/workspace/MarketPulsePanel.tsx` | LOW |
| **G. Watchlist** | Live quotes (30s poll), `DEMO MODE` badge on failure, no explicit verif.-status dot column visible in code review | Table w/ colored verification-status dot per row | Confirm whether a verif.-status column exists — needs live browser check, flagged as unclear from static read | `components/workspace/WatchlistPanel.tsx` | MEDIUM |
| **H. Integrity Monitor** | 100% static `DEMO_DATA`, no fetch | Same DEMO framing acceptable (target itself is tagged `DEMO`) but visual layout differs (4 metric rows vs. flagged-company list) | Needs side-by-side visual diff, likely CSS/layout-only change, not a data change | `components/workspace/IntegrityMonitorPanel.tsx` | LOW |
| **I. News/Filing/Earnings/Sector panels** | All 4 present, static content, structurally matches target | Same | Minor copy/format polish only | `components/workspace/RightColumnPanels.tsx` | LOW |
| **J. Verification metrics (Verification Pulse)** | **Does not exist anywhere in the codebase** | 5-stat strip below the map | New component. Must determine real data source before building — see §6 | New file, likely `components/workspace/VerificationPulsePanel.tsx` | MEDIUM — new component, but must not fabricate numbers |
| **K. Activity/Attention/Coverage** | **Does not exist** | 3-panel row (Recent Activity / Needs Attention / Coverage) | New components. Same data-sourcing caution as J | New files | MEDIUM |
| **L. Live Verification Trace** | **Does not exist** | 6-step horizontal pipeline visualization | New component; visually distinctive (this is the single most bespoke piece of the target design) | New file | MEDIUM — no existing analog to reuse from |
| **M. Command bar** | Embedded *inside* `GlobalTransactionMonitor.tsx`, only visible in the map's default state | Persistent, full-width, below the Live Verification Trace, with 4 quick-action buttons | Needs to be extracted into its own component so it's not tied to map visibility; must reconcile with the one already embedded in the map (avoid two command bars) | `components/workspace/GlobalTransactionMonitor.tsx` (extract from), new `CommandBar.tsx` | MEDIUM — behavioral change, verify the existing `verifyNumber`/`queryLLM` wiring is preserved |
| **N–P. Empty/loading/error states** | Present for some panels (e.g. `EvidencePanel` in `FocusView.tsx` has explicit loading/empty text) inconsistently across panels | Not fully visible in a single static screenshot | Needs a pass once new components exist; flag as Phase-9-level polish, not blocking | multiple | LOW |
| **Q. Hover/active/selected** | Present in tab strips, watchlist rows (`hover:bg-white/[0.02]` pattern used repeatedly) | Consistent with target's restrained hover treatment | Reuse the existing `hover:bg-white/[0.02]` convention for new components rather than inventing a new one | multiple | LOW |
| **R. Responsive states** | See D — effectively absent below 1024px | Full support 1440→390 | Real, open work — see §8 and §12 | `app/workspace/page.tsx` and all child panels | **HIGH** |

---

## 6. Functionality/Data That Must Be Preserved

Confirmed real (do not touch without explicit sign-off):
- `MarketPulsePanel` → `getMarketIndices()` (`lib/api.ts`), 30s poll, graceful fallback to static `FALLBACK_INDICES`.
- `WatchlistPanel` → live quote fetching, 30s poll, `DEMO MODE` badge logic when backend is offline.
- `FocusView` tab wiring → reuses `EarningsVerification.tsx` and `MetricPanel.tsx` (existing, real DVL-backed components) rather than duplicating logic — this reuse must be preserved.
- `GlobalTransactionMonitor`'s embedded command input calls `verifyNumber` / `queryLLM` (`lib/api.ts`) — real backend calls, not decorative. If the command bar is extracted to a standalone component (gap M above), this wiring must move with it, not be reimplemented.
- `useConnection()` (`lib/connection.tsx`) backend-health context — used by `WorkspaceBottomBar` and `MarketPulsePanel`'s siblings; do not fork a second connection-status mechanism.
- `selectedSymbol` state, owned by `WorkspacePage`, threaded through `WatchlistPanel`, `IntegrityMonitorPanel`, and `FocusView` — this is the entire interaction model tying the three columns together. Preserve the prop contract exactly.

Confirmed **not** real — flagged, not to be presented as live in any new copy or in Antigravity's implementation:
- `IntegrityMonitorPanel` — entirely static `DEMO_DATA`, zero network calls.
- `MarketAlertBanner` — hardcoded 5-item array, no fetch, no timestamp logic (times are string literals).
- `GlobalTransactionMonitor` — every city/volume/%-change/arc value is a hardcoded literal, not computed or fetched. (This carries forward the same known caveat already documented in `planning/UI_ARCHITECTURE_REPORT.md` for other pages — consistent with the team's existing "demo-first" stance, not a new issue.)
- `RightColumnPanels` (News/Filing/Earnings/Sector) — static arrays.

**Data question that must be answered before building J/K/L (§5):** the target's Verification Pulse numbers (1,248 claims checked, 1,082 verified, 94 corrected, etc.), the Recent Activity feed, the Needs Attention list, the Coverage table, and the Live Verification Trace timestamps all *look* like they should come from the DVL backend (`finverify-terminal/backend`), since this is the whole product's core function. I did not find an existing frontend fetch or backend endpoint that clearly serves this exact shape of data in the areas I inspected (`lib/api.ts`'s exported functions cover query/verify/market/fundamentals/earnings/history — no obvious "verification pulse/coverage/trace" endpoint was visible in my pass). **This needs a real backend audit before Antigravity builds these three sections**, or they will end up hardcoded the same way `GlobalTransactionMonitor` is — which may be acceptable for a demo, but should be a decision made explicitly, not defaulted into.

---

## 7. Visual Design System

Extracted from `tailwind.config.ts` and `app/globals.css` — already institutional/terminal-styled, and already matches the target's aesthetic closely. Nothing here needs to change; new components should consume these tokens, not invent new ones.

- **Page background:** `#0a0a0a` (`t-bg`), plus a very faint 44px grid overlay (`body.terminal-ambience`).
- **Panel background:** `#111111` (`t-surface`), `1px solid #1e1e1e` border (`t-border`), `4px` radius — this is the `.panel` class, used everywhere.
- **Typography:** JetBrains Mono throughout (self-hosted via `@fontsource`), all-caps labels with `letter-spacing: 0.08em` on panel headers.
- **Text colors:** primary `#e0e0e0`, secondary `#888`, muted `#444`.
- **Status/accent colors:** green `#00ff88` (positive/verified), amber `#fbbf24` (warning/medium), red `#f87171` (negative/error), blue `#60a5fa`, cyan `#22d3ee`, purple `#a78bfa`.
- **Trust badges:** `.trust-high/medium/low` — tinted background at 8% opacity, 1px border at 20% opacity, matches target's HIGH/MEDIUM/LOW tags exactly.
- **Glow states:** `.glow-green/amber/red` — soft box-shadow, used on FocusView's company header band.
- **Hover convention:** `hover:bg-white/[0.02]` — extremely restrained, consistent with a Bloomberg-terminal feel rather than a SaaS dashboard. New components (Verification Pulse, Activity/Attention/Coverage, Live Trace) should follow this exact convention, not a heavier card-hover-lift pattern.

Overall assessment: the intended design is unambiguously **dense, institutional, financial-terminal-inspired** — and the current codebase already nails this. The risk isn't "the design system needs work," it's "new components (J/K/L) need to be built *disciplined enough* to not look like a bolt-on SaaS card grid next to everything else."

---

## 8. Responsive Architecture Audit

**Current reality** (not what the brief claims): `app/workspace/page.tsx` defines exactly one behavioral split, at Tailwind's default `lg` (1024px):

```
< 1024px  → "⚠ VIEWPORT TOO NARROW" panel only, everything else hidden (lg:hidden vs hidden lg:*)
≥ 1024px  → full 3-column grid, fixed at grid-cols-[280px_1fr_300px]
```

There is no 1280px/1200px/900px/600px/390px-specific behavior anywhere in `tailwind.config.ts` (no custom `screens` defined) or in the Workspace component tree. At exactly 1024px, `280px + 1fr + 300px` with `6px` gaps leaves very little room for the center column on a 1024px-wide viewport before scrollbars, so even the ≥1024 case may be tight at the low end — this needs actual browser verification, not just code reading.

This means: the responsive work described in the brief as "already done and tested at 8 breakpoints" is a **real, unstarted (or reverted) piece of work.** Recommend not asking Antigravity to "refine" it — ask it to build it, using the compact/stacked structure the brief describes as the target:
- **≥1280px:** current 3-column layout as-is.
- **1024–1279px:** compact — likely narrower fixed columns or a 2-column layout with right column moved below/collapsed.
- **<1024px:** stacked single column, in priority order (map/verification first, watchlist/pulse next, radar panels last) — replacing the "too narrow" blocker entirely.

Any new center-column content (Verification Pulse, Activity/Attention/Coverage, Live Trace, Command Bar — §5 J–M) must be designed with this in mind from the start, since it's new vertical content that has to reflow at every breakpoint, not just fit inside the existing 1fr column.

---

## 9. Shared Component & Dependency Audit

**Reusable as-is (don't recreate):**
- `.panel` / `.panel-header` / `.trust-badge` / `.status-dot` CSS primitives (`globals.css`) — use for every new component.
- `TrustBadge` inline component pattern in `FocusView.tsx` (HIGH/MEDIUM/LOW pill) — same visual language should back the "risk" tags in the target's Needs Attention panel.
- The `hover:bg-white/[0.02]` row-hover convention, used identically in `WatchlistPanel`, `FocusView`'s filings list, etc.
- `useConnection()` context for any new "live" badge.
- `recharts` `AreaChart`/`LineChart` sparkline pattern (already used 2×) — sufficient for the Live Verification Trace if it needs any mini-charts, no new charting library needed.

**No existing equivalent (genuinely new):**
- Verification Pulse stat strip (5 big numbers + deltas) — closest analog is the Watchlist's price/% pattern but at a different visual scale; recommend a new small `StatBlock` component rather than repurposing Watchlist internals.
- Horizontal step-pipeline visualization (Live Verification Trace) — nothing in the current component set resembles this; build new, keep it self-contained.
- Needs Attention severity-tagged list — close to `IntegrityMonitorPanel`'s flagged-company pattern; worth checking whether that internal list-row component can be extracted and reused rather than rebuilt.

**Dependencies:** none of the target's new sections require a new npm package. Stat strips, tables, and a step pipeline are all achievable with plain divs + Tailwind + the existing `recharts`, consistent with the rest of the app. **Do not add an icon library or a charting library for this work** — every icon in the target screenshot (✓, ⚠, dots) is achievable with the Unicode-glyph convention already in use.

---

## 10. File-by-File Change Plan

| Component | Current file | Current responsibility | Target responsibility | Change type | Risk | Preserve logic? |
|---|---|---|---|---|---|---|
| Global nav | `app/layout.tsx` | Shared header for all 5 routes | Workspace-aware pill nav (Workspace/Verify/Market/Research) + model/health block | Layout modification | HIGH (shared) | Yes — must not break other routes |
| Workspace grid + responsive | `app/workspace/page.tsx` | Single `lg:` breakpoint, "too narrow" blocker | Full 1440→390 responsive shell | Layout modification | HIGH | Yes — preserve `selectedSymbol` state contract |
| Market Pulse | `components/workspace/MarketPulsePanel.tsx` | Live index data, SPX/NDX/VIX labels | Same, relabeled S&P 500/NASDAQ/VIX | CSS-only / copy | LOW | Yes |
| Watchlist | `components/workspace/WatchlistPanel.tsx` | Live quotes | Confirm verif.-status dot column | Needs browser verification first | MEDIUM | Yes |
| Integrity Monitor | `components/workspace/IntegrityMonitorPanel.tsx` | Static demo, flagged-company layout | Static demo, 4-metric-row layout | Layout modification | LOW | N/A (already static) |
| Global Transaction Monitor | `components/workspace/GlobalTransactionMonitor.tsx` | Map + legend + stats + sector tabs + embedded command bar | Same, minus the embedded command bar (moved out per M) | Component extraction (command bar out) | MEDIUM | Yes — preserve `verifyNumber`/`queryLLM` calls when extracting |
| Verification Pulse | *(none)* | — | 5-stat strip | New component | MEDIUM | N/A — flag data source first |
| Activity/Attention/Coverage | *(none)* | — | 3-panel row | New component(s) | MEDIUM | N/A — flag data source first |
| Live Verification Trace | *(none)* | — | 6-step pipeline | New component | MEDIUM | N/A — flag data source first |
| Command Bar | embedded in `GlobalTransactionMonitor.tsx` | Query input tied to map visibility | Persistent bottom command bar | Component extraction + new component | MEDIUM | Yes — carry over existing API wiring |
| News/Filing/Earnings/Sector | `components/workspace/RightColumnPanels.tsx` | Static, structurally matches target | Same, minor polish | CSS-only | LOW | N/A |
| Bottom status bar | `components/workspace/WorkspaceBottomBar.tsx` | Status footer | Same | No change | LOW | Yes |
| Dead file | `app/workspace/WorkspaceTopBar.tsx` | Unused | — | Delete (flag to user first, don't auto-delete) | LOW | N/A |

---

## 11. Risk Assessment

**HIGH RISK**
- Editing `app/layout.tsx` for the nav redesign — this file is shared by all 5 routes (`/`, `/workspace`, `/market`, `/dashboard`, `/metrics`). A careless change breaks navigation everywhere, not just Workspace.
- Building the real responsive grid (§8) — this is genuinely unstarted work, not a refinement, so it carries the risk profile of new work: horizontal overflow, map SVG viewBox scaling issues, ticker/alert-banner marquee behavior at narrow widths, and the interaction between `selectedSymbol`-driven `FocusView` content and a stacked mobile layout.
- Fabricating data for Verification Pulse / Activity / Attention / Coverage / Live Trace if the backend audit (§6) isn't done first — this is explicitly called out by the brief as forbidden, and it's the single easiest place for an implementation agent to quietly invent numbers because "the card needs something in it."

**MEDIUM RISK**
- Extracting the command bar out of `GlobalTransactionMonitor.tsx` without carrying over its existing `verifyNumber`/`queryLLM` wiring correctly (duplicated or dropped functionality).
- Two dead `WorkspaceTopBar.tsx` files with the same name in different directories — an agent grepping for "WorkspaceTopBar" and editing the wrong one (or both) is a realistic mistake.
- `Watchlist` verification-status-dot column — unconfirmed from static code read; building against a wrong assumption here wastes a phase.

**LOW RISK**
- Design-token consistency — the system is already solid and shared; low risk of drift as long as new components are told explicitly to reuse `.panel`/`.trust-badge`/color tokens rather than inventing new ones.
- Right-column panels and Market Pulse — already structurally close to target, changes here are cosmetic.

---

## 12. Recommended Implementation Sequence

Derived from the actual gaps found (not the brief's generic 10-phase template):

**Phase 0 — Resolve the two conflicts from §1 with the user before any code work.**
Confirm: (a) should Workspace actually move to `/`, or does "Workspace-first" just mean "work on the `/workspace` route first"? (b) is the Verification Pulse / Activity / Attention / Coverage / Live Trace data expected to be real (needs backend audit) or acceptable as clearly-labeled demo data (like `IntegrityMonitorPanel` already is)? Do not proceed past Phase 1 without answers — everything downstream depends on these.

**Phase 1 — Responsive foundation.**
Files: `app/workspace/page.tsx`. Replace the binary `lg:`-only split with real 1280/1024/<1024 behavior per §8. Validate at all 8 viewports (§13) *before* adding any new content — building new sections on top of a broken responsive shell means redoing both.

**Phase 2 — Global shell / nav (if Phase 0 confirms scope includes it).**
Files: `app/layout.tsx`, `components/NavModeToggle.tsx`, `components/NavHealthIndicator.tsx`. High risk, shared file — smallest possible diff, verify all 5 routes after.

**Phase 3 — Command bar extraction.**
Files: `components/workspace/GlobalTransactionMonitor.tsx` (remove embedded bar, preserve its API calls), new `components/workspace/CommandBar.tsx`, wire into `app/workspace/page.tsx` as a persistent bottom-of-center element.

**Phase 4 — Verification Pulse stat strip.**
New component. Data source resolved in Phase 0.

**Phase 5 — Activity / Attention / Coverage 3-panel row.**
New components, same data caveat.

**Phase 6 — Live Verification Trace.**
New component — most bespoke visual piece, do last among the new center-column additions so the surrounding layout is already stable.

**Phase 7 — Left column polish.**
`WatchlistPanel.tsx` (confirm/add verif.-status dots), `IntegrityMonitorPanel.tsx` (layout match to target's 4-row format), `MarketPulsePanel.tsx` (label rename only).

**Phase 8 — Right column polish.**
`RightColumnPanels.tsx` — copy/format only, already structurally close.

**Phase 9 — Dead file cleanup.**
Flag both `WorkspaceTopBar.tsx` files to the user; delete only with explicit confirmation, only after Phase 2 makes clear whether either is actually needed.

**Phase 10 — Full regression pass.**
Per §13.

---

## 13. Validation & Regression Checklist

- `npm run build` (or repo's equivalent) — must complete without TypeScript errors.
- `npm run lint` — no new warnings introduced.
- Route check: `/`, `/workspace`, `/market`, `/dashboard`, `/metrics` all still load and their nav links still resolve correctly after any `app/layout.tsx` change.
- Browser check at **1440, 1280, 1200, 1024, 900, 768, 600, 390px** — for each: no horizontal overflow, grid collapses/stacks as designed (not just "doesn't crash"), map SVG scales without clipping, ticker and alert-banner marquees still animate smoothly, watchlist table doesn't truncate illegibly, new center-column sections (Pulse/Activity/Trace/Command Bar) reflow sensibly rather than just disappearing.
- Console: zero hydration errors, zero client console errors, on every route above.
- Network: confirm `getMarketIndices`, watchlist quote fetch, and the command bar's `verifyNumber`/`queryLLM` calls still fire and succeed after the command-bar extraction (Phase 3) — this is the single most likely place for a silent regression.
- Interaction: `selectedSymbol` flow still works end-to-end — clicking a watchlist row / integrity-flagged company selects it, `FocusView` switches to the company state, all 6 tabs render, deselect (✕) returns to the map default state.
- Manual visual comparison against the target screenshot, section by section, using the breakdown in §5 as the checklist (A through R).

---

## 14. Future Verify / Market / Research Architecture Notes

*(High-level only, per the brief — not a detailed plan.)*

- **Verify:** No `/terminal` route exists; the closest current analog is `/` (`app/page.tsx`, the original 662-line DVL query demo — 3-column: Query Input | Results stack | Session/Errors/Stats tabs). If "Verify" is meant to replace or rename this page, that's a routing decision, not a visual one — resolve in Phase 0 territory before Verify work starts.
- **Market:** `/market/page.tsx` — per `planning/UI_ARCHITECTURE_REPORT.md`'s own assessment, this is "already very close to the target workspace's shape" (3-column, live/demo toggling, symbol switching). Likely the least visual work of the three remaining routes.
- **Research:** `/metrics/page.tsx` — described in the planning docs as containing reusable primitives (stat cards, trust badges, filter tabs) already shared with other pages; visual work here is probably additive rather than a rebuild.
- **Shared-component risk across all three:** any component genuinely shared with Workspace (e.g. `TrustBadge`, `.panel` primitives, `NavHealthIndicator`) should be identified explicitly before Verify/Market/Research work begins, so Workspace-phase changes to shared files don't get silently re-litigated later.

---

## 15. Antigravity Master Implementation Prompt

```
You are implementing the FinVerify Terminal Workspace UI. This is a real, partially-built
Next.js 14 App Router application — inspect before you edit anything.

SCOPE: Workspace ONLY (the /workspace route and its component tree under
components/workspace/). Do not touch Verify, Market, Research, or Dashboard, EXCEPT where
a change to app/layout.tsx (shared by all routes) is explicitly required and documented below.

KNOWN CONFLICTS BETWEEN SPEC AND REALITY — READ FIRST:
1. Workspace currently lives at /workspace, NOT at /. / is still the original Terminal/DVL
   query demo (app/page.tsx). There is no /terminal route. Do not move or rename any route
   unless the user has explicitly confirmed this in advance — ask, don't assume.
2. The responsive fix described in prior planning as "done and tested at 8 breakpoints" is
   NOT implemented in app/workspace/page.tsx. It currently has exactly one Tailwind lg:
   (1024px) breakpoint: below it, a "VIEWPORT TOO NARROW" message and nothing else; above
   it, the fixed 3-column grid. Building real 1280/1024/<1024 responsive behavior is
   Phase 1, real open work — not a refinement pass.
3. The design spec referenced as docs/antigravity_prompts.md does not exist in this repo.
   The actual living spec is planning/UI_IMPLEMENTATION_PLAN.md, planning/UI_ARCHITECTURE_REPORT.md,
   and planning/FRONTEND_FILE_MAP.md — read these first, they are cited by section number
   directly in code comments (e.g. FocusView.tsx references "§6 of UI_IMPLEMENTATION_PLAN.md").

RULES:
- Do NOT change routes. Do NOT modify the backend. Do NOT modify verification/DVL logic.
- Do NOT invent or fabricate data. If a target-design element (Verification Pulse stat strip,
  Recent Verification Activity, Needs Attention, Verification Coverage, Live Verification
  Trace) needs data the current frontend/backend doesn't already expose, STOP and flag it
  to the user instead of hardcoding plausible-looking numbers. (IntegrityMonitorPanel.tsx
  and GlobalTransactionMonitor.tsx are pre-existing, team-acknowledged demo-data components —
  do not use them as precedent for silently adding more without asking.)
- Preserve all existing API calls: getMarketIndices (MarketPulsePanel.tsx), the watchlist
  quote-polling logic (WatchlistPanel.tsx), and verifyNumber/queryLLM (currently embedded
  in GlobalTransactionMonitor.tsx's command input — carry this wiring over intact if you
  extract the command bar into its own component).
- Preserve the selectedSymbol state contract: owned by WorkspacePage (app/workspace/page.tsx),
  passed to WatchlistPanel, IntegrityMonitorPanel, and FocusView. Do not restructure this
  without explicit sign-off.
- Reuse existing primitives: .panel / .panel-header / .trust-badge / .status-dot (globals.css),
  the hover:bg-white/[0.02] row-hover convention, the t-* Tailwind color tokens, and recharts
  for any charts. Do not add new npm dependencies (no icon library, no map library, no new
  chart library) — everything in the target screenshot is achievable with what's already here.
- There are two files named WorkspaceTopBar.tsx (app/workspace/WorkspaceTopBar.tsx and
  components/workspace/WorkspaceTopBar.tsx) and NEITHER is currently imported by
  app/workspace/page.tsx. Do not assume either is "the" top bar. Flag this to the user
  before touching either file.
- Implement incrementally, in the phase order below. Validate after each phase (build, lint,
  route check, browser check at 1440/1280/1200/1024/900/768/600/390px, console check) before
  moving to the next.
- If, during implementation, you find the actual code disagrees with this prompt or with
  planning/UI_IMPLEMENTATION_PLAN.md in a way not already listed above, STOP and flag it
  rather than guessing which one is right.

IMPLEMENTATION ORDER:
Phase 0 (you, before coding): confirm with the user (a) whether Workspace should move to /
  and Terminal be renamed/relocated to /terminal, and (b) whether Verification Pulse /
  Activity / Attention / Coverage / Live Trace should be wired to a real backend endpoint
  (requires a backend audit first) or built as explicitly-labeled demo data like
  IntegrityMonitorPanel already is. Do not proceed past Phase 1 without answers.
Phase 1: Real responsive behavior for app/workspace/page.tsx — 1280px+ current grid,
  1024-1279px compact layout, <1024px stacked layout, replacing the viewport-too-narrow
  blocker. Validate at all 8 breakpoints before continuing.
Phase 2 (only if Phase 0 confirms nav scope): Workspace-aware pill nav
  (WORKSPACE/VERIFY/MARKET/RESEARCH) in app/layout.tsx. This file is shared by all 5 routes —
  smallest possible diff, verify every route still loads and links resolve after.
Phase 3: Extract the command bar out of GlobalTransactionMonitor.tsx into its own persistent
  component, preserving its verifyNumber/queryLLM wiring, positioned below the center column
  content per the target screenshot.
Phase 4: New Verification Pulse stat-strip component (data source per Phase 0 decision).
Phase 5: New Recent Verification Activity / Needs Attention / Verification Coverage
  three-panel row (same data-source caveat).
Phase 6: New Live Verification Trace horizontal pipeline component.
Phase 7: Left column polish — WatchlistPanel.tsx (confirm/add verification-status dot
  column), IntegrityMonitorPanel.tsx (layout match to target's 4-metric-row format),
  MarketPulsePanel.tsx (relabel SPX/NDX/VIX to S&P 500/NASDAQ/VIX — copy only).
Phase 8: Right column polish — RightColumnPanels.tsx, copy/format only.
Phase 9: Flag both WorkspaceTopBar.tsx files to the user; delete only with explicit
  confirmation.
Phase 10: Full regression pass per the validation checklist above.
```

---

## 16. Final "DO NOT TOUCH" List

- `app/page.tsx` (Terminal/DVL demo at `/`) — out of scope entirely.
- `app/market/page.tsx`, `app/dashboard/page.tsx`, `app/metrics/page.tsx` — out of scope entirely, except as noted in §14 if a component is confirmed genuinely shared.
- `finverify-terminal/backend/**` — no backend modifications under any circumstance in this phase.
- `EarningsVerification.tsx`, `MetricPanel.tsx` — reused by `FocusView`, do not modify their internals, only how `FocusView` calls them.
- `lib/api.ts`, `lib/connection.tsx`, `lib/market.ts`, `lib/dvl.ts`, `lib/history.ts` — existing data/state layer, read-only for this phase unless a new endpoint is explicitly authorized after the Phase 0 backend-data decision.
- Routing (`app/**/page.tsx` file locations, `next.config.mjs`) — no route additions, removals, or renames without the explicit Phase 0 confirmation described above.
- `package.json` — no new dependencies.
- Any `.git` operations beyond read-only inspection (`git status`, `git log`, `git diff`) — no commits.
