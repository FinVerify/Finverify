/**
 * Semantic verification states for the productization UX.
 *
 * The backend's V1VerifyResponse carries two different axes of
 * information that this module deliberately keeps distinct:
 *
 *   - `trust_score` (HIGH/MEDIUM/LOW/N/A) — a confidence GRADE. See
 *     trust.ts. This is presentation detail, not the headline.
 *   - `verification_status` (verified/contradicted/unverified/pending/
 *     error) — the actual evidentiary finding: did independent evidence
 *     match the claim, contradict it, or simply not exist? This is what
 *     the product spec's three semantic states map to 1:1, plus a
 *     fourth state this module adds — "unavailable" — for the *technical*
 *     failure case (no result at all), which must never be presented as
 *     if it were the same thing as "unverified" (no evidence found, but
 *     the check itself succeeded).
 *
 * Zero DOM, zero chrome.*, zero React — same ground rules as the rest of
 * this package (see types.ts's header comment), so every client (the
 * extension today, anything else tomorrow) derives identical states from
 * identical data and this logic is unit-testable without a browser.
 */
import type { VerifiedClaim } from "./types.js";

/** The four states surfaced to a person, plus the two claim-status values
 *  ("pending"/"cancelled") that aren't a *finding* yet. */
export type SemanticState = "pending" | "cancelled" | "verified" | "contradicted" | "unverified" | "unavailable";

/** Only the four finding-level states carry a color/icon/label — pending
 *  and cancelled are transient UI states, not verification outcomes. */
export type ResolvedSemanticState = "verified" | "contradicted" | "unverified" | "unavailable";

const SEMANTIC_COLORS: Record<ResolvedSemanticState, { bg: string; border: string; text: string }> = {
  // Same green as trust.ts's HIGH — one visual vocabulary for "good" across the extension.
  verified: { bg: "rgba(0,255,136,0.1)", border: "#00ff88", text: "#00ff88" },
  // Same red as trust.ts's LOW — reserved for an actual contradiction, never for "no evidence found".
  contradicted: { bg: "rgba(248,113,113,0.1)", border: "#f87171", text: "#f87171" },
  // Amber, not red — the spec is explicit that "no independent evidence found" is not an error.
  unverified: { bg: "rgba(251,191,36,0.1)", border: "#fbbf24", text: "#fbbf24" },
  // A fourth color, distinct from all three above (and from trust.ts's grey N/A) so a technical
  // failure is never visually confusable with any semantic finding, including "unverified".
  unavailable: { bg: "rgba(167,139,250,0.1)", border: "#a78bfa", text: "#a78bfa" },
};

export function semanticPalette(state: ResolvedSemanticState): { bg: string; border: string; text: string } {
  return SEMANTIC_COLORS[state];
}

export function semanticIcon(state: ResolvedSemanticState): string {
  return state === "verified" ? "✓" : state === "contradicted" ? "✕" : state === "unverified" ? "?" : "!";
}

export function semanticLabel(state: ResolvedSemanticState): string {
  return state === "verified"
    ? "VERIFIED"
    : state === "contradicted"
      ? "CONTRADICTED"
      : state === "unverified"
        ? "UNVERIFIED"
        : "VERIFICATION UNAVAILABLE";
}

/** Short, human copy for the non-error explanation the spec requires
 *  under the UNVERIFIED state ("This is NOT an error.") and the retry
 *  prompt required under VERIFICATION UNAVAILABLE. */
export function semanticExplanation(state: ResolvedSemanticState): string | null {
  if (state === "unverified") return "No independent evidence found.";
  if (state === "unavailable") return "The verification backend could not be reached. Try again.";
  return null;
}

/**
 * Per-claim semantic state. Prefers the backend's own `verification_status`
 * over `trust_score` (see module doc comment above). The trust_score
 * fallback only covers claims built without `verification_status` set
 * (e.g. a hand-built fixture, or an older cached response) — the live
 * /v1/verify contract always sets it (it's a required field on the
 * backend's V1VerifyResponse). The fallback never invents "contradicted"
 * (that's too strong a claim to derive from a confidence grade alone).
 */
export function claimSemanticState(claim: VerifiedClaim): SemanticState {
  if (claim.status === "pending") return "pending";
  if (claim.status === "cancelled") return "cancelled";
  if (claim.status === "error" || !claim.result) return "unavailable";

  const status = claim.result.verification_status;
  if (status === "verified" || status === "contradicted" || status === "unverified") return status;

  // Defensive fallback — see doc comment above.
  return claim.result.trust_score === "HIGH" ? "verified" : "unverified";
}

export interface SemanticSummary {
  total: number;
  pending: number;
  verified: number;
  contradicted: number;
  unverified: number;
  unavailable: number;
}

export function summarizeSemanticStates(claims: VerifiedClaim[]): SemanticSummary {
  const summary: SemanticSummary = { total: claims.length, pending: 0, verified: 0, contradicted: 0, unverified: 0, unavailable: 0 };
  for (const claim of claims) {
    const state = claimSemanticState(claim);
    if (state === "cancelled") continue; // not counted in any bucket — the claim set moved on
    summary[state] += 1;
  }
  return summary;
}

/** Compact multi-claim summary string, e.g. "3 VERIFIED · 1 CONTRADICTED ·
 *  1 UNVERIFIED" — the exact format called for by the productization spec.
 *  Zero-count buckets are omitted; empty only when there's nothing resolved yet. */
export function formatSemanticSummary(summary: SemanticSummary): string {
  const parts: string[] = [];
  if (summary.verified > 0) parts.push(`${summary.verified} VERIFIED`);
  if (summary.contradicted > 0) parts.push(`${summary.contradicted} CONTRADICTED`);
  if (summary.unverified > 0) parts.push(`${summary.unverified} UNVERIFIED`);
  if (summary.unavailable > 0) parts.push(`${summary.unavailable} UNAVAILABLE`);
  return parts.join(" · ");
}

export interface SemanticOverall {
  kind: "empty" | "pending" | "unavailable" | "resolved";
  summary: SemanticSummary;
  /** Meaningful only when kind === "resolved". Contradicted claims are
   *  the most consequential finding and always win the headline, even if
   *  outnumbered by verified ones — a single contradiction is what a
   *  reader most needs to know about. "unavailable" only becomes the
   *  overall `kind` (not just a summary bucket) when literally every
   *  claim in the set failed technically — a single unavailable claim
   *  alongside otherwise-resolved ones stays a summary-line footnote, not
   *  the headline, matching how the existing card treats partial errors. */
  headline: ResolvedSemanticState | null;
}

export function deriveSemanticOverall(claims: VerifiedClaim[]): SemanticOverall {
  const summary = summarizeSemanticStates(claims);
  if (summary.total === 0) return { kind: "empty", summary, headline: null };
  if (summary.pending > 0) return { kind: "pending", summary, headline: null };
  if (summary.unavailable === summary.total) return { kind: "unavailable", summary, headline: "unavailable" };

  const headline: ResolvedSemanticState = summary.contradicted > 0 ? "contradicted" : summary.unverified > 0 ? "unverified" : "verified";
  return { kind: "resolved", summary, headline };
}
