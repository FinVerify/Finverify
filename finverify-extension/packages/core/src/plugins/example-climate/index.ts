import type { ExtractedClaim } from "../../types.js";
import type { VerifierPlugin } from "../types.js";

/**
 * EXAMPLE plugin — not a real, backend-supported domain today.
 *
 * This exists purely as a working demonstration that FinVerify's "add a
 * new domain verifier (Healthcare, Legal, Aerospace, Climate) without
 * modifying the engine" claim is actually true, not just asserted in
 * docs. It's deliberately excluded from `index.ts`'s public exports and
 * from the extension's `engineInstance.ts` — registering it is an
 * explicit opt-in (see the smoke test in this package), not something
 * that ships to users.
 *
 * A real climate plugin would send `buildQuestion`'s output to an actual
 * climate-claim verification backend; this one's `offlineFallback` is
 * the only thing that ever produces a value, since there's no real
 * transport-side support for a "climate" domain yet.
 */
function detectClimateClaims(text: string): ExtractedClaim[] {
  const claims: ExtractedClaim[] = [];
  const regex = /([\d.]+)\s*(ppm|°C|degrees?\s*Celsius)/gi;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = regex.exec(text)) !== null) {
    const value = parseFloat(match[1]);
    if (Number.isNaN(value)) continue;
    claims.push({
      id: `climate-example:${match.index}:${i++}`,
      domain: "climate-example",
      sentence: text.slice(Math.max(0, match.index - 60), match.index + 60).trim(),
      raw_value: value,
      claim_type: match[2].toLowerCase().includes("ppm") ? "co2_ppm" : "temperature_delta",
      match: match[0],
      offset: match.index,
    });
  }
  return claims;
}

export const exampleClimatePlugin: VerifierPlugin = {
  id: "climate-example",
  displayName: "Climate (example)",
  detectClaims: detectClimateClaims,
  buildQuestion(claim) {
    return claim.claim_type === "co2_ppm" ? "What was the stated CO2 concentration in ppm?" : "What was the stated temperature change?";
  },
  offlineFallback(_question, rawValue) {
    // No real domain logic — this is a placeholder proving the seam
    // works, not a claim about climate-data correctness.
    return { verified_value: rawValue, correction_applied: null, trust_score: "MEDIUM" };
  },
};
