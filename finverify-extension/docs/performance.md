# Performance

Real numbers where a number could actually be produced in this
environment; explicitly marked where it couldn't be, rather than
estimated.

## Bundle size (real — `node scripts/perf/bundle-size.mjs`)

Measured against a production build (`npm run build`), current as of this
writing:

| File | Raw | Gzipped |
|---|---|---|
| `src/content/index.js` | 477 KB | **148 KB** |
| `src/content/index.css` | 5.1 KB | 1.4 KB |
| `src/background/index.js` | 2.8 KB | 1.3 KB |
| `src/popup/index.js` | 148 KB | 48 KB |
| `src/popup/popup.css` | 5.1 KB | 1.3 KB |

**The number that matters most is `content/index.js`'s 148 KB gzipped** —
it loads on every ChatGPT page view. That's almost entirely React +
ReactDOM (bundled directly into the IIFE — see `apps/extension/README.md`
on why each entry must be self-contained). This is a real, measured
finding, not a guess, and worth flagging honestly: **a future
architectural conversation about swapping React for something smaller
(Preact is API-compatible and roughly 10x smaller) would directly address
this**, but that's an architecture change and out of scope for this pass
per the current freeze — recorded here as a candidate for when "we
discover a real limitation" applies.

## Claim extraction & engine throughput (real — `node scripts/perf/engine-throughput.mjs`)

Against the real built `@finverify/core`, no browser involved:

- Extracting claims from a ~6.85 KB dense financial text block: **~0.56ms per run** (200-run average).
- Session verification throughput against a mock transport with a
  simulated 2ms per-call latency, at varying concurrency:

  | Concurrency | Claims/sec |
  |---|---|
  | 1 | 455 |
  | 3 | 1,149 |
  | 10 | 4,461 |

  Confirms the concurrency-limited worker pool in
  `VerificationSession.verify()` actually parallelizes as designed —
  throughput scales roughly linearly with concurrency up to the point
  where claim count itself becomes the bottleneck.

## DOM scan latency, memory, CPU overhead (NOT measured here — see why)

`apps/extension/e2e/performance.spec.ts` is written and ready — it
measures "last-message-added → last-badge-visible" latency across a
20-message conversation, plus `JSHeapUsedSize`/`Nodes`/`ScriptDuration`/
`TaskDuration` deltas via a CDP session — but **I could not execute it in
this sandbox**: Playwright's Chromium binary downloads from
`cdn.playwright.dev`, which isn't reachable from here (confirmed via a
direct `npx playwright install chromium` attempt, which failed with a
"Host not in allowlist" error). See `apps/extension/e2e/README.md` for
the same caveat as it applies to the functional E2E suite.

This will produce real numbers the first time it runs in GitHub Actions
CI (`.github/workflows/ci.yml`'s `e2e` job) or on a machine with normal
internet access — until then, this section is deliberately left without
fabricated figures rather than presenting a guess as a measurement.

## What to do once real browser numbers exist

Turn `performance.spec.ts`'s `console.log` output into either:
- a CI artifact compared run-over-run (simplest — catches regressions
  without needing to pick a "correct" absolute number), or
- hard thresholds once there's a deliberate product decision about
  acceptable overhead (e.g. "badge must appear within Xms of a message
  settling" for a typical conversation length).

Neither is implemented yet since picking a threshold before having a
single real measurement would be guessing, not engineering.
