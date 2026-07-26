/**
 * Worked example: adding a brand-new domain verifier plugin without
 * touching @finverify/core's engine/session/registry code at all.
 *
 * This builds a tiny "legal citation" plugin from scratch, right here in
 * userland — not inside packages/core/src/plugins/ — to prove the point:
 * a plugin doesn't need to live inside the core package to work with it.
 * (FinVerify's own shipped domains, like finance, happen to live inside
 * core for distribution convenience, but the interface doesn't require
 * that.)
 *
 * Run: node examples/custom-plugin/index.mjs
 * (requires `npm run build:core` first)
 */
import { VerificationEngine, financePlugin } from "@finverify/core";

// Step 1: detect domain-specific claims in plain text.
// This one looks for U.S. Code citations like "17 U.S.C. § 512" and
// treats the section number as the "value" to verify.
function detectLegalClaims(text) {
  const regex = /(\d+)\s*U\.?S\.?C\.?\s*§\s*(\d+)/gi;
  const claims = [];
  let match;
  let i = 0;
  while ((match = regex.exec(text)) !== null) {
    claims.push({
      id: `legal:${match.index}:${i++}`,
      domain: "legal", // the registry re-stamps this anyway, but good practice to set it correctly
      sentence: text.slice(Math.max(0, match.index - 40), match.index + 40).trim(),
      raw_value: parseInt(match[2], 10),
      claim_type: "usc_section",
      match: match[0],
      offset: match.index,
    });
  }
  return claims;
}

// Step 2: build the question a verification backend should answer for
// each claim. (A real legal-verification backend doesn't exist yet —
// this example uses offlineFallback exclusively, see Step 3 and the
// mock transport below.)
function buildLegalQuestion(claim) {
  return `Does U.S.C. section ${claim.raw_value} exist and match the cited title?`;
}

// Step 3 (optional): an offline fallback for when the transport can't
// reach a real backend. Real domains would normally rely on Step 4's
// transport instead — this is here so the example runs with zero
// external dependencies.
function legalOfflineFallback(_question, rawValue) {
  return { verified_value: rawValue, correction_applied: null, trust_score: "MEDIUM" };
}

const legalPlugin = {
  id: "legal",
  displayName: "Legal (example)",
  detectClaims: detectLegalClaims,
  buildQuestion: buildLegalQuestion,
  offlineFallback: legalOfflineFallback,
};

// Step 4: register it alongside financePlugin. No changes to
// @finverify/core needed anywhere below this line.
const mockTransport = {
  async verify() {
    throw new Error("no real backend for this example — forces every claim through offlineFallback, on purpose");
  },
};

const engine = new VerificationEngine({ transport: mockTransport, plugins: [financePlugin, legalPlugin] });

const text =
  "The DMCA safe harbor under 17 U.S.C. § 512 protects platforms, while the company's revenue grew 12% to $50 million.";

const claims = engine.detectClaims(text);
console.log(
  "Mixed-domain claims (finance + legal) detected in one pass:",
  claims.map((c) => `[${c.domain}] ${c.match}`),
);

engine.on((event) => {
  if (event.type === "claim:updated" && event.claim.status === "verified") {
    console.log(`[${event.claim.domain}] ${event.claim.match} -> ${event.claim.result.trust_score} (${event.claim.result.dvl_version})`);
  }
});

const session = engine.createSession();
await session.verify(claims);
