/**
 * Ported from finverify-terminal/frontend/public/widget.js (TC palette,
 * fmt()). Kept 1:1 so a value verified via any FinVerify client renders
 * with the same visual vocabulary as the embeddable widget.
 */
import type { TrustScore } from "./types.js";

export const TRUST_COLORS: Record<Exclude<TrustScore, "N/A">, { bg: string; border: string; text: string }> = {
  HIGH: { bg: "rgba(0,255,136,0.1)", border: "#00ff88", text: "#00ff88" },
  MEDIUM: { bg: "rgba(251,191,36,0.1)", border: "#fbbf24", text: "#fbbf24" },
  LOW: { bg: "rgba(248,113,113,0.1)", border: "#f87171", text: "#f87171" },
};

export function trustPalette(score: TrustScore): { bg: string; border: string; text: string } {
  if (score === "N/A") return { bg: "rgba(136,136,136,0.1)", border: "#888888", text: "#888888" };
  return TRUST_COLORS[score];
}

export function trustIcon(score: TrustScore): string {
  return score === "HIGH" ? "✓" : score === "MEDIUM" ? "⚠" : score === "LOW" ? "✗" : "•";
}

export function trustLabel(score: TrustScore): string {
  return score === "HIGH" ? "VERIFIED" : score === "MEDIUM" ? "FLAGGED" : score === "LOW" ? "WARNING" : "UNVERIFIED";
}

/** Mirrors widget.js::fmt(v, q). Ratio-keyword detection here is
 *  intentionally the same generic heuristic the finance plugin's offline
 *  fallback uses — formatting is a presentation concern shared across
 *  domains, distinct from the finance plugin's *verification* logic. */
export function formatValue(value: number | null | undefined, question: string): string {
  if (value == null) return "—";
  const isRatio = ["margin", "ratio", "growth", "percent", "rate", "return"].some((k) =>
    question.toLowerCase().includes(k),
  );
  if (isRatio) return `${value.toFixed(2)}%`;
  if (Math.abs(value) >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
  if (Math.abs(value) >= 1e6) return `$${(value / 1e6).toFixed(1)}M`;
  if (Math.abs(value) >= 100) return `$${value.toFixed(2)}`;
  return value.toFixed(4);
}
