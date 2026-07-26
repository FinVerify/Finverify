import type { ExtractedClaim, TrustScore } from "../types.js";

/**
 * A domain verifier plugin.
 *
 * The engine (`engine.ts`) knows nothing about finance, healthcare, legal,
 * aerospace, or climate specifically — it only knows "some plugins can
 * find claims in text, and every claim needs a question sent to the
 * verification transport." Adding FinVerify's next domain (say,
 * healthcare dosage verification) means writing one plugin here, never
 * touching `engine.ts` or `session.ts`.
 *
 * A plugin is a pure function bundle: no network calls, no DOM, no
 * transport of its own. `detectClaims` reads plain text; `buildQuestion`
 * turns a claim into the natural-language question the *transport* sends
 * to the actual verification backend. Whatever backend answers that
 * question (finance DVL today; a future healthcare/legal/aerospace/
 * climate verification service) is the transport's concern, not the
 * plugin's.
 */
export interface VerifierPlugin {
  /** Stable identifier, e.g. "finance". Stamped onto every claim this
   *  plugin detects (`ExtractedClaim.domain`) and usable as a filter key
   *  by any consumer that only wants one domain's claims. */
  readonly id: string;
  readonly displayName: string;

  /** Finds this plugin's domain-specific claims in plain text. Must set
   *  `claim.domain = this.id` on every result — the engine enforces this
   *  defensively (see registry.ts) but plugins should do it themselves. */
  detectClaims(text: string): ExtractedClaim[];

  /** Builds the question sent to the verification transport for a given
   *  claim. Kept separate from `detectClaims` because question phrasing
   *  is often deliberately narrower than claim classification — e.g. the
   *  finance plugin avoids ratio-keywords in questions for non-ratio
   *  claim types to sidestep a DVL false-positive correction. */
  buildQuestion(claim: ExtractedClaim): string;

  /** Optional lightweight, dependency-free fallback used only when the
   *  transport is unreachable — exists so a sleeping/offline backend
   *  doesn't leave a claim with zero signal. Plugins without a
   *  meaningful offline heuristic can omit this; the engine treats a
   *  missing fallback as "no offline estimate available" rather than an
   *  error. */
  offlineFallback?(question: string, rawValue: number): OfflineFallbackResult;
}

export interface OfflineFallbackResult {
  verified_value: number;
  correction_applied: string | null;
  trust_score: TrustScore;
}
