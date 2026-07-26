# E2E tests

## What these test, and what they don't

These tests load the **real, unmodified, production-built** extension
(`apps/extension/dist`, exactly what ships) via Playwright's persistent-
context extension-loading mechanism, and drive it against a **local
fixture page**, not live `chatgpt.com`.

**Why not live ChatGPT:**
- There's no way to authenticate a CI runner as a ChatGPT account.
- Live ChatGPT's DOM changes without notice; a test suite that depends on
  it breaks for reasons that have nothing to do with a real regression in
  this codebase, which is the opposite of what CI should give you.
- Scraping/automating a third-party product you don't own in CI is
  fragile and can run afoul of that product's terms of service, quite
  apart from the technical problems above.

**What's real:** the adapter (`adapters/chatgpt/index.ts`), the
orchestrator, the engine (`@finverify/core`, actually bundled in), the
background worker, and the UI — all exactly as built. The fixture page
(`e2e/fixtures/chatgpt-fixture.html`) exists purely to give that real code
the same DOM shape (`data-message-author-role="assistant"`, an `article`
wrapper, a `button[aria-label="Copy"]` toolbar) it expects on the real
product, with test-only JS helpers (`window.__fvAddCompleteReply`,
`window.__fvSimulateStreamingReply`, `window.__fvRemoveMessage`) to drive
it deterministically instead of depending on a live model actually
generating text.

**What's mocked:** the network. `/v1/verify` and `/health` responses are
intercepted at the Playwright `context.route()` level and answered with
canned JSON — the extension code has no idea it isn't talking to the real
FinVerify backend. This is the only thing that differs from a real run;
see `e2e/setup/prepare-test-extension.mjs`'s comment for the one (and
only) other difference (an extra `matches` entry so the real content
script also runs on the fixture's local origin).

## What this means the adapter selectors are NOT tested against

The fixture's markup is *my best-effort model* of ChatGPT's real DOM as
of when `adapters/chatgpt/index.ts` was written — see
`docs/adding-a-provider.md`'s point about selectors needing live
verification. If OpenAI's real markup has since diverged from what the
adapter expects, these tests will still pass (they test the adapter
against the fixture, which matches the adapter's assumptions by
construction) while the real extension could be broken on the live site.
**A green E2E run is not a substitute for periodically loading the actual
extension against real chatgpt.com and confirming injection still
works.**

## Running locally

```bash
cd apps/extension
npm run build        # tests run against the real dist/, not source
npx playwright install chromium
npm run test:e2e
```

## Running in this sandbox / restricted-network environments

Playwright's browser binaries download from `cdn.playwright.dev`, which
is not on every environment's network allowlist. If `npx playwright
install` fails with a "Host not in allowlist" error, that's why — the
test suite itself is still valid and will run in GitHub Actions CI (see
`.github/workflows/ci.yml`), which has open egress, or on a local machine
with normal internet access.
