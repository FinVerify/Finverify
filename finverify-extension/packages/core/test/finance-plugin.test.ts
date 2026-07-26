import { describe, it, expect } from "vitest";
import { financePlugin } from "../src/plugins/finance/index.js";

describe("financePlugin", () => {
  it("has the expected id/displayName", () => {
    expect(financePlugin.id).toBe("finance");
    expect(financePlugin.displayName).toBe("Finance");
  });

  it("detectClaims is wired to real finance detection", () => {
    const claims = financePlugin.detectClaims("Revenue of $5 million grew significantly across the business this year.");
    expect(claims.length).toBeGreaterThan(0);
  });

  it("buildQuestion is wired to real finance question-building", () => {
    expect(financePlugin.buildQuestion({ id: "1", domain: "finance", sentence: "s", raw_value: 1, claim_type: "eps", match: "1", offset: 0 })).toMatch(/earnings per share/i);
  });

  it("offlineFallback is wired to the real finance fallback heuristic", () => {
    expect(financePlugin.offlineFallback!("What was the margin value?", 4500).correction_applied).toBe("scale_div100");
  });
});
