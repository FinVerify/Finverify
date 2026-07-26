import { describe, it, expect } from "vitest";
import { trustPalette, trustIcon, trustLabel, formatValue, TRUST_COLORS } from "../src/trust.js";

describe("trustPalette", () => {
  it("returns the matching palette for HIGH/MEDIUM/LOW", () => {
    expect(trustPalette("HIGH")).toEqual(TRUST_COLORS.HIGH);
    expect(trustPalette("MEDIUM")).toEqual(TRUST_COLORS.MEDIUM);
    expect(trustPalette("LOW")).toEqual(TRUST_COLORS.LOW);
  });

  it("returns a distinct grey palette for N/A", () => {
    const palette = trustPalette("N/A");
    expect(palette.text).toBe("#888888");
  });
});

describe("trustIcon / trustLabel", () => {
  it("maps every trust score to a distinct icon and label", () => {
    expect(trustIcon("HIGH")).toBe("✓");
    expect(trustIcon("MEDIUM")).toBe("⚠");
    expect(trustIcon("LOW")).toBe("✗");
    expect(trustIcon("N/A")).toBe("•");

    expect(trustLabel("HIGH")).toBe("VERIFIED");
    expect(trustLabel("MEDIUM")).toBe("FLAGGED");
    expect(trustLabel("LOW")).toBe("WARNING");
    expect(trustLabel("N/A")).toBe("UNVERIFIED");
  });
});

describe("formatValue", () => {
  it("returns an em dash placeholder for null/undefined", () => {
    expect(formatValue(null, "q")).toBe("—");
    expect(formatValue(undefined, "q")).toBe("—");
  });

  it("formats a ratio-keyword question as a percentage", () => {
    expect(formatValue(45.678, "What was the margin value?")).toBe("45.68%");
    expect(formatValue(12, "What was the growth rate?")).toBe("12.00%");
  });

  it("formats large non-ratio values with $B/$M scaling", () => {
    expect(formatValue(94.9e9, "What was the revenue figure?")).toBe("$94.90B");
    expect(formatValue(5.2e6, "What was the revenue figure?")).toBe("$5.2M");
  });

  it("formats mid-size non-ratio values as plain dollars", () => {
    expect(formatValue(142.5, "What was the financial value in the statement?")).toBe("$142.50");
  });

  it("formats small non-ratio values with 4 decimal places", () => {
    expect(formatValue(1.42, "What was the earnings per share?")).toBe("1.4200");
  });
});
