import { describe, it, expect } from "vitest";
import { formatClaimShareText, formatClaimSetShareText } from "../src/share.js";
import type { VerifiedClaim, V1VerifyResponse } from "../src/types.js";

function claim(overrides: Partial<VerifiedClaim> & { id: string }): VerifiedClaim {
  return {
    domain: "finance",
    sentence: "Apple's revenue for fiscal year 2025 was $94.04 billion.",
    raw_value: 94.04e9,
    claim_type: "currency",
    match: "$94.04 billion",
    offset: 0,
    status: "verified",
    ...overrides,
  };
}

function result(overrides: Partial<V1VerifyResponse> = {}): V1VerifyResponse {
  return {
    question: "What was Apple's revenue?",
    raw_value: 94.04e9,
    verified_value: 109.42e9,
    correction_applied: null,
    trust_score: "LOW",
    trust_color: "#f87171",
    verification_status: "contradicted",
    delta_pct: -16.36,
    dvl_version: "1.0.0",
    reasons: ["Evidence tier: filing", "Corrections: none"],
    timestamp: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("formatClaimShareText", () => {
  it("returns null for claims with nothing to share yet", () => {
    expect(formatClaimShareText(claim({ id: "1", status: "pending" }))).toBeNull();
    expect(formatClaimShareText(claim({ id: "2", status: "cancelled" }))).toBeNull();
  });

  it("formats a contradicted claim with claimed value, evidence value, and difference", () => {
    const text = formatClaimShareText(claim({ id: "1", result: result({ evidence_value: 109.42e9 }) }))!;
    expect(text).toContain("FINVERIFY VERIFICATION");
    expect(text).toContain("CONTRADICTED");
    expect(text).toContain("$94.04 billion");
    expect(text).toContain("AI claim: $94.04B");
    expect(text).toContain("Primary-source evidence: $109.42B");
    expect(text).toContain("Difference: -16.36%");
    expect(text).toContain("Verified independently by FinVerify.");
  });

  it("does not fabricate an evidence value for a contradiction the backend didn't attach one to", () => {
    const text = formatClaimShareText(claim({ id: "1", result: result({ evidence_value: null }) }))!;
    expect(text).toContain("AI claim: $94.04B");
    expect(text).toContain("Primary-source evidence: contradicted by independent evidence (exact value unavailable).");
    expect(text).not.toContain("Verified value:");
    expect(text).not.toContain("$109.42B");
  });

  it("formats an unverified claim without an invented value comparison", () => {
    const text = formatClaimShareText(
      claim({
        id: "1",
        result: result({ verification_status: "unverified", trust_score: "N/A", evidence_value: null, delta_pct: 0 }),
      }),
    )!;
    expect(text).toContain("AI claim: $94.04B");
    expect(text).toContain("No independent evidence available");
    expect(text).not.toContain("Verified value:");
  });

  it("never fabricates a source/filing line the backend didn't return", () => {
    const text = formatClaimShareText(claim({ id: "1", result: result() }))!;
    expect(text).not.toMatch(/SEC EDGAR|10-K|accession/i);
  });

  it("surfaces real reasons as notes when present", () => {
    const text = formatClaimShareText(claim({ id: "1", result: result() }))!;
    expect(text).toContain("Notes: Evidence tier: filing; Corrections: none");
  });

  it("formats a technical failure distinctly, without a fabricated value comparison", () => {
    const text = formatClaimShareText(claim({ id: "1", status: "error", error: "HTTP 503" }))!;
    expect(text).toContain("VERIFICATION UNAVAILABLE");
    expect(text).toContain("could not be reached");
    expect(text).toContain("Detail: HTTP 503");
    expect(text).not.toContain("AI claim:");
  });

  it("formats a verified claim without a difference line when the delta is negligible", () => {
    const text = formatClaimShareText(
      claim({ id: "1", result: result({ verification_status: "verified", verified_value: 94.04e9, delta_pct: 0, trust_score: "HIGH" }) }),
    )!;
    expect(text).not.toContain("Difference:");
  });
});

describe("formatClaimSetShareText", () => {
  it("joins multiple resolved claims with a divider and skips unresolved ones", () => {
    const text = formatClaimSetShareText([
      claim({ id: "1", result: result({ verification_status: "verified", delta_pct: 0 }) }),
      claim({ id: "2", status: "pending" }),
      claim({ id: "3", result: result({ verification_status: "contradicted" }) }),
    ]);
    expect(text.split("\n\n---\n\n")).toHaveLength(2);
  });
});
