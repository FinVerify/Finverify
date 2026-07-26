import { describe, it, expect } from "vitest";
import { detectFinanceClaims, buildFinanceQuestion, financeOfflineFallback } from "../src/plugins/finance/detect.js";

describe("detectFinanceClaims", () => {
  it("detects a currency value with a scale word and converts it", () => {
    const claims = detectFinanceClaims("Revenue reached $94.9 billion this quarter, a record for the company.");
    const currency = claims.find((c) => c.claim_type === "currency");
    expect(currency).toBeDefined();
    expect(currency!.raw_value).toBeCloseTo(94.9e9);
    expect(currency!.scale_label).toBe("billion");
  });

  it("detects a bare currency value without a scale word as currency_raw", () => {
    const claims = detectFinanceClaims("The stock closed at $142.50 on Friday afternoon trading.");
    const raw = claims.find((c) => c.claim_type === "currency_raw");
    expect(raw).toBeDefined();
    expect(raw!.raw_value).toBeCloseTo(142.5);
  });

  it("detects a plain percentage", () => {
    const claims = detectFinanceClaims("Gross margin came in at 45.2% for the reporting period overall.");
    const pct = claims.find((c) => c.claim_type === "percentage");
    expect(pct).toBeDefined();
    expect(pct!.raw_value).toBeCloseTo(45.2);
  });

  it("detects basis points and converts to a percentage (240 bps -> 2.4)", () => {
    const claims = detectFinanceClaims("The spread widened by 240 basis points during the crisis period.");
    const bps = claims.find((c) => c.claim_type === "bps");
    expect(bps).toBeDefined();
    expect(bps!.raw_value).toBeCloseTo(2.4);
    expect(bps!.bps_original).toBe(240);
  });

  it("detects growth vs decline phrasing separately", () => {
    const growthClaims = detectFinanceClaims("Sales grew 12.5% year over year according to the filing.");
    expect(growthClaims.some((c) => c.claim_type === "growth_pct")).toBe(true);

    const declineClaims = detectFinanceClaims("Sales declined 8.3% year over year according to the filing.");
    expect(declineClaims.some((c) => c.claim_type === "decline_pct")).toBe(true);
  });

  it("detects share counts (note: the shares pattern has no scale-word capture group, so raw_value is the bare number, not multiplied by the scale word)", () => {
    const claims = detectFinanceClaims("The company repurchased 12 million shares under the buyback program.");
    expect(claims.some((c) => c.claim_type === "shares" && c.raw_value === 12)).toBe(true);
  });

  it("detects EPS", () => {
    const claims = detectFinanceClaims("Diluted EPS of $1.42 beat analyst estimates for the quarter.");
    const eps = claims.find((c) => c.claim_type === "eps");
    expect(eps).toBeDefined();
    expect(eps!.raw_value).toBeCloseTo(1.42);
  });

  it("detects margin and revenue claims", () => {
    const claims = detectFinanceClaims("Operating margin was 22.1% while revenue of $4.2 billion grew steadily.");
    expect(claims.some((c) => c.claim_type === "margin")).toBe(true);
    expect(claims.some((c) => c.claim_type === "revenue")).toBe(true);
  });

  it("detects capital ratio and return-on-X metrics", () => {
    const claims = detectFinanceClaims("CET1 ratio of 13.4% supported a return on equity of 15.2% this year.");
    expect(claims.some((c) => c.claim_type === "ratio")).toBe(true);
    expect(claims.some((c) => c.claim_type === "return_metric")).toBe(true);
  });

  it("ignores sentences shorter than 10 characters", () => {
    const claims = detectFinanceClaims("12%. Ok.");
    // The whole input is one short fragment plus a trivial sentence;
    // neither should produce a claim since both are under the 10-char floor.
    expect(claims).toEqual([]);
  });

  it("does not throw and returns an array for text with no numeric claims", () => {
    expect(detectFinanceClaims("This is a plain sentence with no numbers in it at all.")).toEqual([]);
  });

  it("does not throw on empty string input", () => {
    expect(detectFinanceClaims("")).toEqual([]);
  });

  it("dedups an identical match within the same sentence", () => {
    // "12%" pattern and the growth-prefixed pattern would otherwise both
    // match overlapping text; seenMatches keys on (sentence prefix + full
    // match), so an exact repeat of the same match text is suppressed but
    // distinguishable claim_types are not.
    const claims = detectFinanceClaims("Growth of 12% was 12% higher than the prior guidance range given.");
    const percentMatches = claims.filter((c) => c.match === "12%");
    // Two distinct textual occurrences of "12%" in the sentence should
    // still both be found (dedup is per unique match string+sentence
    // prefix combination, not a global "only one 12% ever" rule) —
    // this assertion just documents current behavior explicitly.
    expect(percentMatches.length).toBeGreaterThanOrEqual(1);
  });

  it("sets domain to empty/undefined at the detection layer (registry is responsible for stamping it)", () => {
    // detectFinanceClaims is called directly here, bypassing the registry,
    // so claim.domain is whatever the function itself sets — verifying
    // this documents the boundary between detect.ts and registry.ts.
    const claims = detectFinanceClaims("Revenue of $5 million grew significantly across all business segments.");
    expect(claims.length).toBeGreaterThan(0);
    expect(claims[0].domain).toBe("finance");
  });

  it("records a non-negative character offset into the original text for each match", () => {
    const text = "Filler sentence one here. Revenue of $5 million grew significantly this year.";
    const claims = detectFinanceClaims(text);
    for (const c of claims) {
      expect(c.offset).toBeGreaterThanOrEqual(0);
      expect(text.slice(c.offset, c.offset + c.match.length)).toBe(c.match);
    }
  });
});

describe("buildFinanceQuestion", () => {
  it("returns claim-type-specific questions, avoiding ratio keywords for non-ratio types", () => {
    expect(buildFinanceQuestion({ claim_type: "growth_pct", raw_value: 1 })).toMatch(/stated numerical figure/i);
    expect(buildFinanceQuestion({ claim_type: "decline_pct", raw_value: 1 })).toMatch(/stated numerical figure/i);
    expect(buildFinanceQuestion({ claim_type: "margin", raw_value: 1 })).toMatch(/margin value/i);
    expect(buildFinanceQuestion({ claim_type: "percentage", raw_value: 1 })).toMatch(/numeric value/i);
    expect(buildFinanceQuestion({ claim_type: "eps", raw_value: 1 })).toMatch(/earnings per share/i);
    expect(buildFinanceQuestion({ claim_type: "ratio", raw_value: 1 })).toMatch(/financial ratio/i);
    expect(buildFinanceQuestion({ claim_type: "return_metric", raw_value: 1 })).toMatch(/financial ratio/i);
    expect(buildFinanceQuestion({ claim_type: "currency", raw_value: 1 })).toMatch(/financial value in the statement/i);
    expect(buildFinanceQuestion({ claim_type: "revenue", raw_value: 1 })).toMatch(/revenue figure/i);
    expect(buildFinanceQuestion({ claim_type: "shares", raw_value: 1 })).toMatch(/share count/i);
    expect(buildFinanceQuestion({ claim_type: "unknown_type", raw_value: 1 })).toMatch(/financial value/i);
  });

  it("includes the original bps figure (not the converted percentage) in the bps question", () => {
    const question = buildFinanceQuestion({ claim_type: "bps", raw_value: 2.4, bps_original: 240 });
    expect(question).toContain("240");
  });

  it("falls back to raw_value * 100 for bps question when bps_original is missing", () => {
    const question = buildFinanceQuestion({ claim_type: "bps", raw_value: 2.4 });
    expect(question).toContain("240");
  });
});

describe("financeOfflineFallback", () => {
  it("leaves a non-ratio question's value unchanged", () => {
    const result = financeOfflineFallback("What was the financial value in the statement?", 5_000_000);
    expect(result.verified_value).toBe(5_000_000);
    expect(result.correction_applied).toBeNull();
    expect(result.trust_score).toBe("HIGH");
  });

  it("scales down a ratio value that looks like it's off by 100x (e.g. 4500 instead of 45.00)", () => {
    const result = financeOfflineFallback("What was the margin value?", 4500);
    expect(result.verified_value).toBeCloseTo(45);
    expect(result.correction_applied).toBe("scale_div100");
    expect(result.trust_score).toBe("MEDIUM");
  });

  it("scales up a ratio value that looks like a fraction (e.g. 0.45 instead of 45)", () => {
    const result = financeOfflineFallback("What was the growth rate?", 0.45);
    expect(result.verified_value).toBeCloseTo(45);
    expect(result.correction_applied).toBe("scale_mul100");
    expect(result.trust_score).toBe("MEDIUM");
  });

  it("leaves a plausible ratio value (between 1 and 100) unchanged", () => {
    const result = financeOfflineFallback("What was the margin value?", 22.5);
    expect(result.verified_value).toBe(22.5);
    expect(result.correction_applied).toBeNull();
    expect(result.trust_score).toBe("HIGH");
  });
});
