# Contributing to FinVerify

## Setup

```bash
git clone <repo>
cd finverify
npm install     # installs and symlinks every workspace package
npm run build   # builds @finverify/core, then @finverify/extension
```

## Where things live

See the root `README.md`'s "Where to look for what" table first. Short
version: verification logic (claim detection, trust scoring, retry,
batching, dedup, cancellation) lives in `packages/core`; the browser
extension (`apps/extension`) is a thin client — DOM adapters, a
chrome-messaging transport, UI wiring, nothing else. If you're adding
logic to `apps/extension` that isn't one of those three things, it
probably belongs in `packages/core` instead.

## Before opening a PR

```bash
npm run lint          # eslint across the whole monorepo
npm run typecheck     # tsc --noEmit for both packages
npm run test:coverage # @finverify/core's unit tests, with coverage
npm run build         # full build, both packages
```

All four run in CI (`.github/workflows/ci.yml`) on every PR; running them
locally first saves a round trip. `apps/extension` also has:

```bash
cd apps/extension
npm run typecheck:e2e  # typechecks the Playwright suite (separate tsconfig — see e2e/README.md)
npm run test:e2e       # requires `npx playwright install chromium` first
```

## Adding to @finverify/core

- **New domain plugin** (healthcare, legal, aerospace, climate, ...): see
  `packages/core/README.md`'s "Adding a domain plugin" section. Add unit
  tests for your plugin's `detectClaims`/`buildQuestion`/`offlineFallback`
  the same way `test/finance-detect.test.ts` does for the finance plugin.
- **Anything else in core**: this package targets >90% line coverage
  (enforced in CI via `vitest.config.ts`'s `coverage.thresholds`, not just
  aspirational) — new logic needs new tests, not just a passing build.
  Look at `test/session.test.ts` for the level of rigor expected,
  particularly around cancellation/dedup edge cases — those are exactly
  the kind of thing that looks fine until a concurrent-request race
  proves otherwise.

## Adding to the extension

- **New AI product adapter** (Claude, Gemini, Copilot, Perplexity, or one
  not yet stubbed): see `apps/extension/docs/adding-a-provider.md`. Do not
  flip `verified: true` or add a host to `manifest.json` without actually
  testing selectors against the live product first.
- **UI changes**: `src/ui/InlineBadge.tsx` and `src/ui/VerificationCard.tsx`
  are the only two components. Both consume `@finverify/core`'s
  `VerifiedClaim`/`EngineEvent` types — they should never need
  finance-specific logic of their own.

## Architecture changes

The current architecture (monorepo split, event-driven plugin-based
engine, thin extension client) reflects a deliberate decision to freeze
major structural changes unless testing surfaces a concrete limitation
that requires one. If you think something needs restructuring, the bar
is: what test, benchmark, or real usage revealed the limitation? "This
would be cleaner" isn't sufficient on its own — "the dedup cache races
under X condition, here's a failing test" is.

## Commit / PR expectations

- Keep PRs scoped to one concern (one plugin, one provider adapter, one
  bug fix) — this codebase's history is easiest to navigate when a commit
  answers one question.
- If a change touches behavior a test doesn't cover, add the test in the
  same PR, not as a follow-up.
- Reference which of `docs/architecture.md` (extension) or
  `packages/core/README.md` (core) your change affects, if any, so
  documentation doesn't silently drift from what the code actually does.
