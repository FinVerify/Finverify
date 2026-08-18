import { test, expect } from "./fixtures/test-base";
import type { BrowserContext, Route } from "@playwright/test";

const API_BASE = "https://aadi2026-finverify-api.hf.space";

/** Mocks the real FinVerify backend at the network level. This is
 *  deliberately the *only* thing that differs from production: the exact
 *  same built extension code (adapter, engine, transport, UI) runs
 *  unmodified — only the bytes coming back from `/v1/verify` and
 *  `/health` are faked, so these tests don't depend on a live backend,
 *  rate limits, or network flakiness.
 *
 *  `responseOverrides` lets a test control what `/v1/verify` returns —
 *  e.g. `{ verification_status: "contradicted", trust_score: "LOW",
 *  verified_value: 109.42e9, delta_pct: -16.36 }` — while every other
 *  field still reflects the real request, matching the actual
 *  V1VerifyResponse contract (see packages/core/src/types.ts). */
async function mockBackend(context: BrowserContext, calls: any[], responseOverrides: Record<string, unknown> = {}) {
  await context.route(`${API_BASE}/**`, async (route: Route) => {
    const url = route.request().url();
    if (url.endsWith("/health")) {
      return route.fulfill({ json: { status: "ok", dvl: "online", llm: "online", model: "e2e-mock" } });
    }
    if (url.endsWith("/v1/verify")) {
      const body = route.request().postDataJSON();
      calls.push(body);
      return route.fulfill({
        json: {
          question: body.question,
          raw_value: body.raw_value,
          verified_value: body.raw_value,
          correction_applied: null,
          trust_score: "HIGH",
          trust_color: "#00ff88",
          verification_status: "verified",
          delta_pct: 0,
          dvl_version: "e2e-mock",
          timestamp: new Date().toISOString(),
          ...responseOverrides,
        },
      });
    }
    return route.continue();
  });
}

/** Same as mockBackend, but /v1/verify fails outright — the technical
 *  failure ("VERIFICATION UNAVAILABLE") path, distinct from a claim the
 *  backend successfully checked and found no evidence for. */
async function mockBackendUnavailable(context: BrowserContext) {
  await context.route(`${API_BASE}/**`, async (route: Route) => {
    const url = route.request().url();
    if (url.endsWith("/health")) {
      return route.fulfill({ json: { status: "ok", dvl: "online", llm: "online", model: "e2e-mock" } });
    }
    if (url.endsWith("/v1/verify")) {
      return route.fulfill({ status: 503, json: { error: "backend unavailable" } });
    }
    return route.continue();
  });
}

test("injects a verification badge next to an assistant reply containing a financial claim", async ({ context }) => {
  await mockBackend(context, []);
  const page = await context.newPage();
  await page.goto("/chatgpt-fixture.html");

  await page.evaluate((text) => (window as any).__fvAddCompleteReply(text), "Revenue grew 12% to $94.9 billion this quarter.");

  const badge = page.locator("[data-finverify-badge] button");
  await expect(badge).toBeVisible({ timeout: 5000 });
});

test("does not inject a badge for a reply with no numeric/financial claims", async ({ context }) => {
  await mockBackend(context, []);
  const page = await context.newPage();
  await page.goto("/chatgpt-fixture.html");

  await page.evaluate((text) => (window as any).__fvAddCompleteReply(text), "Here is a purely qualitative answer with no numbers at all.");

  // Give the orchestrator's rAF-coalesced scan a moment to run, then
  // confirm it correctly chose not to mount anything.
  await page.waitForTimeout(500);
  await expect(page.locator("[data-finverify-badge]")).toHaveCount(0);
});

test("streaming: badge appears and verifies incrementally before the message finishes, without waiting for the toolbar", async ({ context }) => {
  const calls: any[] = [];
  await mockBackend(context, calls);
  const page = await context.newPage();
  await page.goto("/chatgpt-fixture.html");

  const streamPromise = page.evaluate(
    (text) => (window as any).__fvSimulateStreamingReply(text, { chunkSize: 8, intervalMs: 40 }),
    "First quarter revenue grew 12% to $94.9 billion, with EPS of $1.42 beating estimates significantly.",
  );

  // The badge should appear WHILE streaming is still in progress (the
  // fixture only reveals the Copy button — our streaming signal — once
  // the full text has been appended), proving verification starts on
  // partial text rather than waiting for generation to finish.
  const badge = page.locator("[data-finverify-badge] button");
  await expect(badge).toBeVisible({ timeout: 5000 });

  const toolbarVisibleMidStream = await page.locator(".toolbar.visible").count();
  expect(toolbarVisibleMidStream).toBe(0);

  await streamPromise;

  // After streaming completes, the full claim set should eventually be
  // verified (aria-label reports "verifying" while pending, then a trust
  // word once settled).
  await expect(badge).toHaveAttribute("aria-label", /verifying|high|medium|low/i, { timeout: 5000 });
  expect(calls.length).toBeGreaterThan(0);
});

test("clicking the badge expands a verification panel with per-claim trust info", async ({ context }) => {
  await mockBackend(context, []);
  const page = await context.newPage();
  await page.goto("/chatgpt-fixture.html");

  await page.evaluate((text) => (window as any).__fvAddCompleteReply(text), "Operating margin was 22.1% and revenue reached $4.2 billion.");

  const badge = page.locator("[data-finverify-badge] button");
  await expect(badge).toBeVisible({ timeout: 5000 });
  await badge.click();

  await expect(page.getByText(/Powered by/i)).toBeVisible({ timeout: 5000 });
  await expect(page.getByText(/22\.1%/)).toBeVisible();
});

test("verification requests sent to the backend carry the expected shape (question + raw_value)", async ({ context }) => {
  const calls: any[] = [];
  await mockBackend(context, calls);
  const page = await context.newPage();
  await page.goto("/chatgpt-fixture.html");

  await page.evaluate((text) => (window as any).__fvAddCompleteReply(text), "EPS of $1.42 beat estimates for the quarter overall.");

  await expect.poll(() => calls.length, { timeout: 5000 }).toBeGreaterThan(0);
  for (const call of calls) {
    expect(typeof call.question).toBe("string");
    expect(call.question.length).toBeGreaterThan(0);
    expect(typeof call.raw_value).toBe("number");
  }
});

test("removing a message from the DOM cleans up its badge (orchestrator prune + session cancellation)", async ({ context }) => {
  await mockBackend(context, []);
  const page = await context.newPage();
  await page.goto("/chatgpt-fixture.html");

  const articleId = await page.evaluate((text) => (window as any).__fvAddCompleteReply(text), "Net income of $500 million grew year over year.");
  await expect(page.locator("[data-finverify-badge]")).toHaveCount(1, { timeout: 5000 });

  await page.evaluate((id) => (window as any).__fvRemoveMessage(id), articleId);
  // The orchestrator prunes on its next scan (mutation-triggered or the
  // 4s safety-net interval) — allow enough time for either path.
  await expect(page.locator("[data-finverify-badge]")).toHaveCount(0, { timeout: 6000 });
});

test("CONTRADICTED: a claim the backend found evidence against renders distinctly, not as UNVERIFIED", async ({ context }) => {
  await mockBackend(context, [], {
    verification_status: "contradicted",
    trust_score: "LOW",
    trust_color: "#f87171",
    verified_value: 109.42e9,
    delta_pct: -16.36,
  });
  const page = await context.newPage();
  await page.goto("/chatgpt-fixture.html");

  await page.evaluate((text) => (window as any).__fvAddCompleteReply(text), "Apple's revenue for fiscal year 2025 was $94.04 billion.");

  const badge = page.locator("[data-finverify-badge] button");
  await expect(badge).toBeVisible({ timeout: 5000 });
  await expect(badge).toHaveText(/CONTRADICTED/i, { timeout: 5000 });
  await badge.click();
  await expect(page.getByText("CONTRADICTED", { exact: true }).first()).toBeVisible({ timeout: 5000 });
});

test("UNVERIFIED: no independent evidence found renders as amber/neutral, not red, and explains it is not an error", async ({ context }) => {
  await mockBackend(context, [], { verification_status: "unverified", trust_score: "MEDIUM", trust_color: "#fbbf24" });
  const page = await context.newPage();
  await page.goto("/chatgpt-fixture.html");

  await page.evaluate((text) => (window as any).__fvAddCompleteReply(text), "Gross margin was 41.2% for the quarter.");

  const badge = page.locator("[data-finverify-badge] button");
  await expect(badge).toBeVisible({ timeout: 5000 });
  await expect(badge).toHaveText(/UNVERIFIED/i, { timeout: 5000 });
  await badge.click();
  await expect(page.getByText(/no independent evidence found/i)).toBeVisible({ timeout: 5000 });
});

test("VERIFICATION UNAVAILABLE: a backend failure is shown distinctly from UNVERIFIED, with a retry prompt", async ({ context }) => {
  await mockBackendUnavailable(context);
  const page = await context.newPage();
  await page.goto("/chatgpt-fixture.html");

  await page.evaluate((text) => (window as any).__fvAddCompleteReply(text), "Quarterly revenue was $12.4 billion.");

  const badge = page.locator("[data-finverify-badge] button");
  await expect(badge).toBeVisible({ timeout: 5000 });
  await expect(badge).toHaveText(/UNAVAILABLE/i, { timeout: 8000 });
  await badge.click();
  await expect(page.getByText("VERIFICATION UNAVAILABLE", { exact: true })).toBeVisible({ timeout: 5000 });
  await expect(page.getByText(/try again/i)).toBeVisible();
});

test("multiple claims: each gets an independent finding and the card shows a compact spec-format summary", async ({ context }) => {
  let call = 0;
  await context.route(`${API_BASE}/**`, async (route: Route) => {
    const url = route.request().url();
    if (url.endsWith("/health")) {
      return route.fulfill({ json: { status: "ok", dvl: "online", llm: "online", model: "e2e-mock" } });
    }
    if (url.endsWith("/v1/verify")) {
      const body = route.request().postDataJSON();
      call += 1;
      // First claim verified, second contradicted, third unverified —
      // proves claims are never merged into one blended result.
      const overrides =
        call === 1
          ? { verification_status: "verified" as const }
          : call === 2
            ? { verification_status: "contradicted" as const, verified_value: body.raw_value * 1.2, delta_pct: -16.7 }
            : { verification_status: "unverified" as const };
      return route.fulfill({
        json: {
          question: body.question,
          raw_value: body.raw_value,
          verified_value: body.raw_value,
          correction_applied: null,
          trust_score: "HIGH",
          trust_color: "#00ff88",
          dvl_version: "e2e-mock",
          timestamp: new Date().toISOString(),
          ...overrides,
        },
      });
    }
    return route.continue();
  });

  const page = await context.newPage();
  await page.goto("/chatgpt-fixture.html");
  await page.evaluate(
    (text) => (window as any).__fvAddCompleteReply(text),
    "Revenue was $94.9 billion, net income was $23.6 billion, and operating margin was 22.1%.",
  );

  const badge = page.locator("[data-finverify-badge] button");
  await expect(badge).toBeVisible({ timeout: 5000 });
  await expect.poll(() => badge.textContent(), { timeout: 5000 }).toMatch(/VERIFIED.*·.*CONTRADICTED.*·.*UNVERIFIED/i);
});
