/**
 * The minimum code a new Node-based FinVerify client needs: an engine,
 * the built-in HTTP transport (real fetch, real retry/backoff — no
 * chrome.runtime messaging involved, since this isn't a browser
 * extension), and the finance plugin.
 *
 * Run: node examples/node-basic-usage/index.mjs
 * (requires `npm run build:core` first — this imports the real built package)
 */
import { VerificationEngine, createHttpTransport, financePlugin } from "@finverify/core";

const engine = new VerificationEngine({
  transport: createHttpTransport(), // hits the real FinVerify backend
  plugins: [financePlugin],
});

// Every event from every session this engine creates flows through here.
// A CLI might print them; a Desktop app might update a UI; an agent
// framework might feed them back into a tool-call result.
engine.on((event) => {
  if (event.type === "claims:detected") {
    console.log(`[${event.sessionId}] detected ${event.claims.length} claim(s)`);
  }
  if (event.type === "claim:updated" && event.claim.status === "verified") {
    const { match, result } = event.claim;
    console.log(`  ${match} -> ${result.trust_score} (raw ${result.raw_value} -> verified ${result.verified_value})`);
  }
  if (event.type === "session:completed") {
    console.log(`[${event.sessionId}] done`);
  }
});

const text = "Q3 revenue grew 12.5% to $94.9 billion, with EPS of $1.42 beating estimates.";
const claims = engine.detectClaims(text);

const session = engine.createSession();
await session.verify(claims);
