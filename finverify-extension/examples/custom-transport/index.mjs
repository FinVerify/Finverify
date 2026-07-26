/**
 * Shows the actual seam a new client implements when it can't use
 * createHttpTransport() as-is — e.g. a browser extension's content
 * script (host-page CSP), a VS Code extension needing to route through
 * its own proxy, or (as here, for a runnable example with no external
 * dependencies) a fully offline mock for local development.
 *
 * This is a *simplified* stand-in for apps/extension/src/messaging/
 * chromeTransport.ts — the real one adds requestId tracking and
 * cross-context cancellation because it's crossing a chrome.runtime
 * messaging boundary; this one doesn't need that since it's all in one
 * process.
 *
 * Run: node examples/custom-transport/index.mjs
 * (requires `npm run build:core` first)
 */
import { VerificationEngine, financePlugin, TransportError } from "@finverify/core";

/** @type {import("@finverify/core").VerificationTransport} */
const offlineMockTransport = {
  async verify(request, options) {
    // A real implementation would call out somewhere (fetch, an RPC
    // client, chrome.runtime.sendMessage, whatever fits the client). This
    // one just fabricates a response after a short delay, and honors
    // cancellation the way any transport must — the engine relies on
    // this contract for cancel() to actually stop in-flight work.
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => resolve({
        question: request.question,
        raw_value: request.raw_value,
        verified_value: request.raw_value,
        correction_applied: null,
        trust_score: "HIGH",
        trust_color: "#00ff88",
        delta_pct: 0,
        dvl_version: "offline-mock-example",
        timestamp: new Date().toISOString(),
      }), 50);

      options?.signal?.addEventListener("abort", () => {
        clearTimeout(timer);
        reject(new TransportError("cancelled", false, true));
      });
    });
  },

  async checkHealth() {
    return { status: "ok", dvl: "online", llm: "online", model: "offline-mock" };
  },
};

const engine = new VerificationEngine({ transport: offlineMockTransport, plugins: [financePlugin] });

engine.on((event) => {
  if (event.type === "claim:updated" && event.claim.status === "verified") {
    console.log(`${event.claim.match} -> ${event.claim.result.trust_score}`);
  }
});

const session = engine.createSession();
await session.verify(engine.detectClaims("Operating margin was 22.1% on revenue of $4.2 billion."));

console.log("\nCancellation demo — starting a second session and cancelling it immediately:");
const session2 = engine.createSession();
const verifyPromise = session2.verify(engine.detectClaims("EPS of $1.42 beat estimates."));
session2.cancel();
await verifyPromise;
console.log("session2.isCancelled:", session2.isCancelled, "(no claim:updated events fired for it above — cancelled before the mock's 50ms delay elapsed)");
