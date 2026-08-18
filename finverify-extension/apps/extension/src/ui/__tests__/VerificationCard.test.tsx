import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type { VerifiedClaim, V1VerifyResponse } from "@finverify/core";
import { deriveAnalystSummary, VerificationCard } from "../VerificationCard";

function claim(
  id: string,
  verification_status: V1VerifyResponse["verification_status"] = "unverified",
  trust_score: V1VerifyResponse["trust_score"] = "N/A",
): VerifiedClaim {
  const result: V1VerifyResponse = {
    question: "What was revenue?",
    raw_value: 42,
    verified_value: 42,
    correction_applied: null,
    verification_status,
    trust_score,
    confidence: verification_status === "unverified" ? null : 0.9,
    reasons: [],
    trust_color: "#888888",
    delta_pct: 0,
    dvl_version: "1.0.0",
    timestamp: "2026-01-01T00:00:00Z",
  };
  return {
    id,
    domain: "finance",
    sentence: "Revenue was 42.",
    raw_value: 42,
    claim_type: "currency",
    match: "$42",
    offset: 0,
    status: "verified",
    result,
  };
}

describe("VerificationCard verification coverage", () => {
  it("does not turn 17 exact matches with no evidence into 20% confidence", () => {
    const claims = Array.from({ length: 17 }, (_, index) => claim(String(index)));
    const summary = deriveAnalystSummary(claims);
    expect(summary.corroborated).toHaveLength(0);
    expect(summary.uncorroboratedCount).toBe(17);
    expect(renderToStaticMarkup(<VerificationCard claims={claims} />)).not.toContain("20%");
  });

  it("reports verified, contradicted, and unverified claims separately", () => {
    const claims = [
      ...Array.from({ length: 12 }, (_, index) => claim(`verified-${index}`, "verified", "HIGH")),
      ...Array.from({ length: 2 }, (_, index) => claim(`contradicted-${index}`, "contradicted", "LOW")),
      ...Array.from({ length: 3 }, (_, index) => claim(`unverified-${index}`)),
    ];
    const summary = deriveAnalystSummary(claims);
    expect(summary.corroborated).toHaveLength(14);
    expect(summary.contradictedCount).toBe(2);
    expect(summary.uncorroboratedCount).toBe(3);
    const markup = renderToStaticMarkup(<VerificationCard claims={claims} />);
    expect(markup).toContain("contradicted");
    expect(markup).toContain("unverified");
    expect(markup).not.toContain("20% confidence");
  });

  it("retains a real HIGH evidence-backed confidence meter", () => {
    const markup = renderToStaticMarkup(<VerificationCard claims={[claim("high", "verified", "HIGH")]} />);
    expect(markup).toContain(">90<");
    expect(markup).toContain(">%</span>");
  });
});
