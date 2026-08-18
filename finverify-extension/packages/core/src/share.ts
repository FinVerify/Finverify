/**
 * Plain-text share/export formatting for a single verified claim.
 *
 * Deliberately renders ONLY fields the backend actually returns
 * (V1VerifyResponse — see types.ts). The productization spec's example
 * share format includes a "Source: SEC EDGAR" line and page/accession
 * references; the current /v1/verify contract does not return structured
 * source/evidence data (no Source/Evidence/Entity/Metric objects — only
 * scalar question/raw_value/verified_value/trust_score/verification_status/
 * confidence/reasons/dvl_version/timestamp). Rather than fabricate a
 * source that was never independently confirmed, this formatter surfaces
 * only what was actually returned. See the productization report for the
 * backend schema change that would be needed to show real source/filing
 * provenance.
 */
import { claimSemanticState, semanticLabel, type ResolvedSemanticState } from "./semantic.js";
import { formatValue } from "./trust.js";
import type { VerifiedClaim } from "./types.js";

/** Plain-text export for one resolved claim, in the spirit of the spec's
 *  example format but using only real fields. Returns null for claims
 *  that aren't resolved yet (pending/cancelled) — nothing coherent to share. */
export function formatClaimShareText(claim: VerifiedClaim): string | null {
  const state = claimSemanticState(claim);
  if (state === "pending" || state === "cancelled") return null;

  const lines: string[] = ["FINVERIFY VERIFICATION", "", claim.match, semanticLabel(state as ResolvedSemanticState), ""];

  if (state === "unavailable" || !claim.result) {
    lines.push("Verification unavailable — the backend could not be reached for this claim.");
    if (claim.error) lines.push(`Detail: ${claim.error}`);
    return lines.join("\n");
  }

  const result = claim.result;
  lines.push(`AI claim: ${formatValue(result.raw_value, result.question)}`);
  // CONTRADICTED must show what the independent evidence actually said
  // (evidence_value) rather than `verified_value`, which still echoes the
  // claim on a contradiction. UNVERIFIED never had independent evidence to
  // report at all. Never fabricate a value the backend didn't return.
  if (state === "contradicted") {
    lines.push(
      result.evidence_value != null
        ? `Primary-source evidence: ${formatValue(result.evidence_value, result.question)}`
        : "Primary-source evidence: contradicted by independent evidence (exact value unavailable).",
    );
  } else if (state === "unverified") {
    lines.push("No independent evidence available");
  } else {
    lines.push(`Verified value: ${formatValue(result.verified_value, result.question)}`);
  }
  if (Math.abs(result.delta_pct) > 0.05) {
    lines.push(`Difference: ${result.delta_pct > 0 ? "+" : ""}${result.delta_pct.toFixed(2)}%`);
  }
  if (result.correction_applied) lines.push(`Correction: ${result.correction_applied}`);
  lines.push("");
  lines.push(`Method: Deterministic verification (FinVerify DVL v${result.dvl_version})`);
  if (result.reasons && result.reasons.length > 0) lines.push(`Notes: ${result.reasons.join("; ")}`);
  lines.push("");
  lines.push("Verified independently by FinVerify.");
  return lines.join("\n");
}

/** Compact multi-claim plain-text export — one block per claim, in
 *  document order, separated by a divider. Skips claims with nothing to
 *  share yet (pending/cancelled). */
export function formatClaimSetShareText(claims: VerifiedClaim[]): string {
  const blocks = claims.map(formatClaimShareText).filter((b): b is string => b !== null);
  return blocks.join("\n\n---\n\n");
}
