import { describe, it, expect } from "vitest";
import {
  claimSemanticState,
  summarizeSemanticStates,
  formatSemanticSummary,
  deriveSemanticOverall,
  semanticPalette,
  semanticIcon,
  semanticLabel,
  semanticExplanation,
} from "../src/semantic.js";
import type { VerifiedClaim, V1VerifyResponse } from "../src/types.js";

function claim(overrides: Partial<VerifiedClaim> & { id: string }): VerifiedClaim {
  return {
    domain: "finance",
    sentence: "Revenue was $94.9 billion.",
    raw_value: 94.9e9,
    claim_type: "currency",
    match: "$94.9 billion",
    offset: 0,
    status: "verified",
    ...overrides,
  };
}

function result(overrides: Partial<V1VerifyResponse> = {}): V1VerifyResponse {
  return {
    question: "What was revenue?",
    raw_value: 94.9e9,
    verified_value: 94.9e9,
    correction_applied: null,
    trust_score: "HIGH",
    trust_color: "#00ff88",
    verification_status: "verified",
    delta_pct: 0,
    dvl_version: "1.0.0",
    timestamp: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("claimSemanticState", () => {
  it("maps a verified result", () => {
    expect(claimSemanticState(claim({ id: "1", result: result() }))).toBe("verified");
  });

  it("maps a contradicted result", () => {
    expect(
      claimSemanticState(claim({ id: "2", result: result({ verification_status: "contradicted", trust_score: "LOW" }) })),
    ).toBe("contradicted");
  });

  it("maps an unverified result (no independent evidence, not an error)", () => {
    expect(
      claimSemanticState(claim({ id: "3", result: result({ verification_status: "unverified", trust_score: "MEDIUM" }) })),
    ).toBe("unverified");
  });

  it("maps a hard technical failure to unavailable, never to unverified", () => {
    expect(claimSemanticState(claim({ id: "4", status: "error", error: "network error" }))).toBe("unavailable");
  });

  it("maps a claim with no result at all to unavailable", () => {
    expect(claimSemanticState(claim({ id: "5", status: "verified", result: undefined }))).toBe("unavailable");
  });

  it("passes through pending and cancelled untouched", () => {
    expect(claimSemanticState(claim({ id: "6", status: "pending" }))).toBe("pending");
    expect(claimSemanticState(claim({ id: "7", status: "cancelled" }))).toBe("cancelled");
  });

  it("falls back to trust_score only when verification_status is missing (defensive, e.g. legacy fixture)", () => {
    const legacy = result({ trust_score: "HIGH" });
    // @ts-expect-error simulating a response shape without verification_status
    delete legacy.verification_status;
    expect(claimSemanticState(claim({ id: "8", result: legacy }))).toBe("verified");

    const legacyLow = result({ trust_score: "LOW" });
    // @ts-expect-error simulating a response shape without verification_status
    delete legacyLow.verification_status;
    // The fallback never invents "contradicted" from trust_score alone.
    expect(claimSemanticState(claim({ id: "9", result: legacyLow }))).toBe("unverified");
  });
});

describe("summarizeSemanticStates / formatSemanticSummary", () => {
  it("counts each bucket and formats the compact spec summary", () => {
    const claims = [
      claim({ id: "1", result: result() }),
      claim({ id: "2", result: result() }),
      claim({ id: "3", result: result() }),
      claim({ id: "4", result: result({ verification_status: "contradicted" }) }),
      claim({ id: "5", result: result({ verification_status: "unverified" }) }),
    ];
    const summary = summarizeSemanticStates(claims);
    expect(summary).toEqual({ total: 5, pending: 0, verified: 3, contradicted: 1, unverified: 1, unavailable: 0 });
    expect(formatSemanticSummary(summary)).toBe("3 VERIFIED · 1 CONTRADICTED · 1 UNVERIFIED");
  });

  it("omits zero-count buckets", () => {
    const summary = summarizeSemanticStates([claim({ id: "1", result: result() })]);
    expect(formatSemanticSummary(summary)).toBe("1 VERIFIED");
  });

  it("excludes cancelled claims from every bucket", () => {
    const summary = summarizeSemanticStates([claim({ id: "1", status: "cancelled" })]);
    expect(summary.total).toBe(1);
    expect(summary.verified + summary.contradicted + summary.unverified + summary.unavailable + summary.pending).toBe(0);
  });
});

describe("deriveSemanticOverall", () => {
  it("is empty for no claims", () => {
    expect(deriveSemanticOverall([]).kind).toBe("empty");
  });

  it("is pending while any claim is still resolving", () => {
    const overall = deriveSemanticOverall([claim({ id: "1", result: result() }), claim({ id: "2", status: "pending" })]);
    expect(overall.kind).toBe("pending");
  });

  it("is unavailable only when every claim technically failed", () => {
    const allFailed = deriveSemanticOverall([claim({ id: "1", status: "error" }), claim({ id: "2", status: "error" })]);
    expect(allFailed.kind).toBe("unavailable");
    expect(allFailed.headline).toBe("unavailable");

    const partialFailure = deriveSemanticOverall([claim({ id: "1", result: result() }), claim({ id: "2", status: "error" })]);
    expect(partialFailure.kind).toBe("resolved");
    expect(partialFailure.summary.unavailable).toBe(1);
  });

  it("a single contradiction wins the headline even when outnumbered by verified claims", () => {
    const overall = deriveSemanticOverall([
      claim({ id: "1", result: result() }),
      claim({ id: "2", result: result() }),
      claim({ id: "3", result: result({ verification_status: "contradicted" }) }),
    ]);
    expect(overall.headline).toBe("contradicted");
  });

  it("unverified wins over verified when there's no contradiction", () => {
    const overall = deriveSemanticOverall([
      claim({ id: "1", result: result() }),
      claim({ id: "2", result: result({ verification_status: "unverified" }) }),
    ]);
    expect(overall.headline).toBe("unverified");
  });
});

describe("semantic display helpers", () => {
  it("gives each resolved state a distinct color", () => {
    const colors = new Set(
      (["verified", "contradicted", "unverified", "unavailable"] as const).map((s) => semanticPalette(s).text),
    );
    expect(colors.size).toBe(4);
  });

  it("never uses the contradicted (red) color for unverified", () => {
    expect(semanticPalette("unverified").text).not.toBe(semanticPalette("contradicted").text);
  });

  it("labels match the spec's exact state names", () => {
    expect(semanticLabel("verified")).toBe("VERIFIED");
    expect(semanticLabel("contradicted")).toBe("CONTRADICTED");
    expect(semanticLabel("unverified")).toBe("UNVERIFIED");
    expect(semanticLabel("unavailable")).toBe("VERIFICATION UNAVAILABLE");
  });

  it("icons are distinct per state", () => {
    const icons = new Set((["verified", "contradicted", "unverified", "unavailable"] as const).map(semanticIcon));
    expect(icons.size).toBe(4);
  });

  it("explains UNVERIFIED as not-an-error and prompts a retry for VERIFICATION UNAVAILABLE", () => {
    expect(semanticExplanation("unverified")).toMatch(/no independent evidence/i);
    expect(semanticExplanation("unavailable")).toMatch(/try again/i);
    expect(semanticExplanation("verified")).toBeNull();
  });
});
