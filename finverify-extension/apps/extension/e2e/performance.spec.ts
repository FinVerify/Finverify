import { test } from "./fixtures/test-base";

const API_BASE = "https://aadi2026-finverify-api.hf.space";

/**
 * Performance smoke tests — logged to stdout rather than asserted against
 * hard thresholds, since acceptable overhead is a product decision, not
 * something this file should silently gate CI on. Treat these numbers as
 * a trend to watch (compare a PR's output against main's), not a
 * pass/fail gate, until there's a deliberately-chosen budget to enforce.
 */
test("performance: badge-appearance latency and CDP memory/CPU overhead", async ({ context }) => {
  await context.route(`${API_BASE}/**`, async (route) => {
    const url = route.request().url();
    if (url.endsWith("/health")) return route.fulfill({ json: { status: "ok", dvl: "online", llm: "online", model: "perf" } });
    const body = route.request().postDataJSON();
    return route.fulfill({
      json: {
        question: body.question,
        raw_value: body.raw_value,
        verified_value: body.raw_value,
        correction_applied: null,
        trust_score: "HIGH",
        trust_color: "#0f8",
        delta_pct: 0,
        dvl_version: "perf",
        timestamp: new Date().toISOString(),
      },
    });
  });

  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  await cdp.send("Performance.enable");

  await page.goto("/chatgpt-fixture.html");
  const before = await cdp.send("Performance.getMetrics");

  // A conversation-sized page: 20 assistant messages, each with a few
  // financial claims — a reasonable stand-in for a long ChatGPT session
  // rather than a single short reply.
  const t0 = Date.now();
  for (let i = 0; i < 20; i++) {
    await page.evaluate(
      (n) => (window as any).__fvAddCompleteReply(`Message ${n}: revenue grew 12% to $${n}.5 million with EPS of $${(n % 9) + 1}.42.`),
      i,
    );
  }

  // Latency from "last message added" to "last badge visible" — a
  // practical proxy for end-to-end DOM-scan-to-render overhead, since the
  // orchestrator's internal scan function isn't exposed for isolated
  // in-page timing (it's bundled into the IIFE, not a testable unit on
  // its own — see e2e/README.md on what's real vs. fixture here).
  await page.locator("[data-finverify-badge]").last().locator("button").waitFor({ state: "visible", timeout: 5000 });
  const scanToRenderMs = Date.now() - t0;

  const after = await cdp.send("Performance.getMetrics");
  const metricDelta = (name: string) => {
    const b = before.metrics.find((m) => m.name === name)?.value ?? 0;
    const a = after.metrics.find((m) => m.name === name)?.value ?? 0;
    return a - b;
  };

  console.log("=== FinVerify E2E performance ===");
  console.log(`20-message conversation: last-message-added -> last-badge-visible: ${scanToRenderMs}ms`);
  console.log(`JSHeapUsedSize delta: ${(metricDelta("JSHeapUsedSize") / 1024 / 1024).toFixed(2)} MB`);
  console.log(`Nodes delta: ${metricDelta("Nodes")}`);
  console.log(`ScriptDuration delta: ${metricDelta("ScriptDuration").toFixed(3)}s`);
  console.log(`TaskDuration delta: ${metricDelta("TaskDuration").toFixed(3)}s`);
});
