# @finverify/extension

The FinVerify browser extension — now a thin client of `@finverify/core`.
See the monorepo root README for the overall structure.

## What lives here vs. in @finverify/core

| Here (extension-specific) | In @finverify/core (shared) |
|---|---|
| DOM adapters (`src/adapters/`) — reading ChatGPT's markup | Claim detection/domain plugins |
| `chrome.runtime` messaging protocol + transport (`src/messaging/`) | Trust scoring, retry/backoff, dedup, batching, cancellation |
| React UI (`src/ui/`, `src/content/`, `src/popup/`) | The event-driven engine itself |
| Background worker (`src/background/`) — thin, delegates to core's `createHttpTransport` | — |

If you're looking for claim-extraction regexes, trust color logic, or
retry/backoff — they moved to `packages/core/src/`. This app should never
need its own copy of any of that again; if you find yourself writing
domain-verification or network-reliability logic inside `apps/extension`,
that's a sign it belongs in `@finverify/core` instead.

## Status

| Layer | State |
|---|---|
| ChatGPT adapter | **Verified**, active (`chatgpt.com`, `chat.openai.com`) |
| Claude / Gemini / Copilot / Perplexity adapters | Inert stubs — see `docs/adding-a-provider.md` |
| Verification engine (dedup, batching abstraction, cancellation, retry/backoff) | In `@finverify/core`, consumed here via `src/engineInstance.ts` |
| Inline live verification (streaming-aware, no click required) | Implemented |
| Plugin-based domain verification | Implemented in core; extension currently registers only `financePlugin` |
| Hover explanations / provenance display | `title` attributes on claim rows today, no rich hover UI |
| True backend batch endpoint | Not yet — abstracted in core so only `session.ts` changes when it lands |

## Build

From the monorepo root (builds `@finverify/core` first, which this app depends on):

```bash
npm install
npm run build
```

Or from this directory directly (assumes `@finverify/core` is already built):

```bash
npm run build
```

Output lands in `dist/`. Load it unpacked:

1. `chrome://extensions`
2. Enable **Developer mode**
3. **Load unpacked** → select `apps/extension/dist/`
4. Open `https://chatgpt.com`, ask a question with numbers in the answer.
   A small colored dot appears in the message's toolbar as soon as claims
   are detected (even mid-stream) — click it to expand the verification
   card.

## Key architectural decisions worth knowing before changing things

- **Three separate Vite configs**, not one. Rollup hoisting shared code
  (e.g. React, or `@finverify/core` itself) into a chunk the content
  script tries to `import` would break, since MV3 content scripts run as
  classic scripts, not ES modules. Each entry (`content`, `background`,
  `popup`) builds independently as a self-contained IIFE with
  `@finverify/core` inlined directly into each bundle that needs it.
- **Verification goes through the background worker**, never straight
  `fetch` from the content script — the content script runs inside the
  host page's context and is subject to whatever CSP that product ships;
  the background worker isn't. The background worker calls
  `@finverify/core`'s `createHttpTransport()` directly (no CORS
  restriction there), so retry/backoff logic isn't reimplemented here.
- **`src/messaging/chromeTransport.ts`** is the extension's only
  implementation of core's `VerificationTransport` interface — it's the
  entire "how does this specific client reach the network" concern,
  intentionally isolated to one file.
