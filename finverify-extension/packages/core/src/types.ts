/**
 * Types mirroring the FinVerify backend contracts.
 *
 * Source of truth (do not drift from these without updating the backend too):
 *   - finverify-terminal/backend/app/models.py   → V1VerifyRequest / V1VerifyResponse
 *   - finverify-terminal/backend/ingestion/transcripts.py → claim dict shape
 *   - finverify-terminal/frontend/public/widget.js → trust color palette
 *
 * This module has zero DOM, zero chrome.*, zero React. Every client
 * (browser extension, VS Code, Desktop, Enterprise Dashboard, an agent
 * runtime) shares these exact shapes.
 */

/** Mirrors backend/app/models.py::V1VerifyRequest */
export interface V1VerifyRequest {
  question: string;
  raw_value: number;
  model_source?: string;
  /** Untrusted semantic hints used only to resolve independent evidence. */
  entity_hint?: string;
  metric_hint?: string;
  period_hint?: string;
  context_text?: string;
}

/** Mirrors backend/app/models.py::V1VerifyResponse */
export interface V1VerifyResponse {
  question: string;
  raw_value: number;
  verified_value: number;
  correction_applied: string | null;
  trust_score: TrustScore;
  trust_color: string;
  verification_status?: VerificationStatus;
  confidence?: number | null;
  reasons?: string[];
  delta_pct: number;
  dvl_version: string;
  timestamp: string;
}

export type TrustScore = "HIGH" | "MEDIUM" | "LOW" | "N/A";
export type VerificationStatus = "verified" | "contradicted" | "unverified" | "pending" | "error";

/** One numeric claim extracted from text, mirroring the dict shape
 *  produced by ingestion/transcripts.py::extract_claims(). The specific
 *  `claim_type` union below is the finance plugin's vocabulary — other
 *  domain plugins (healthcare, legal, aerospace, climate) define their
 *  own claim_type strings; this field is intentionally `string`, not a
 *  closed union, so the engine never needs to know every domain's
 *  vocabulary up front. See plugins/types.ts. */
export interface ExtractedClaim {
  /** Stable id for React keys / dedup, derived from sentence + match. */
  id: string;
  /** Which plugin produced this claim, e.g. "finance". Lets the engine
   *  and UI attribute/filter claims by domain without special-casing. */
  domain: string;
  /** Sentence the number was found in (truncated to 200 chars, matching backend). */
  sentence: string;
  /** The raw numeric value as parsed from the text. */
  raw_value: number;
  /** Domain-specific claim type, e.g. "currency" | "percentage" for
   *  finance. Not a closed union — see doc comment above. */
  claim_type: string;
  /** The exact substring matched (e.g. "$94.9 billion", "25.31%"). */
  match: string;
  /** Character offset of `match` within the full response text, for highlighting. */
  offset: number;
  /** Present only for claim_type === "bps"; the pre-conversion bps figure. */
  bps_original?: number;
  /** Present only for currency claims with a unit word (e.g. "billion"). */
  scale_label?: string;
  /** Optional semantic context inferred from the source sentence. */
  entity_hint?: string;
  metric_hint?: string;
  period_hint?: string;
}

/** A claim after it has been sent through /v1/verify. */
export interface VerifiedClaim extends ExtractedClaim {
  status: "pending" | "verified" | "error" | "cancelled";
  result?: V1VerifyResponse;
  error?: string;
}

/** Backend health check shape (GET /health). */
export interface HealthStatus {
  status: string;
  dvl: "online" | "offline";
  llm: "online" | "offline";
  model: string;
}
