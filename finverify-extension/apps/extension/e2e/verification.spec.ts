import { test, expect } from "./fixtures/test-base";
import type { BrowserContext, Route } from "@playwright/test";

const API_BASE = "https://aadi2026-finverify-api.hf.space";

/** Mocks the real FinVerify backend at the network level. This is
 *  deliberately the *only* thing that differs from production: the exact
 *  same built extension code (adapter, engine, transport, UI) runs
 *  unmodified — only the bytes coming back from `/v1/verify` and
 *  `/health` are faked, so these tests don't depend on a live backend,
 *  rate limits, or network flakiness. */
async function mockBackend(context: BrowserContext, calls: any[]) {
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
          delta_pct: 0,
          dvl_version: "e2e-mock",
          timestamp: new Date().toISOString(),
        },
      });
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
