"use client";
import React from "react";
import type { BatchVerificationResult } from "@/lib/api";

interface Props {
  result: BatchVerificationResult | null;
  latencyMs: number | null;
  isLoading: boolean;
  isDegraded?: boolean;
}

/**
 * Verification Result Card — Stage 6 of the pipeline.
 * Shows the final verification outcome with claimed vs verified value,
 * difference/delta, trust label, and correction summary.
 */
export default function TerminalPanel({ result, latencyMs, isLoading, isDegraded }: Props) {
  if (isLoading) {
    return (
      <div className="panel glow-amber" style={{ borderLeft: "3px solid #fbbf24" }}>
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <span className="text-t-amber text-[10px] font-bold">⑥</span>
            <span className="label text-t-amber">VERIFICATION RESULT</span>
          </div>
          <span className="status-dot amber" />
        </div>
        <div className="px-4 py-6 flex flex-col items-center justify-center gap-2">
          <div className="text-t-amber text-[12px] font-mono font-bold animate-pulse">
            VERIFICATION IN PROGRESS
          </div>
          <div className="text-t-muted text-[10px] font-mono">
            Querying verification engine...
          </div>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="panel">
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <span className="text-t-muted text-[10px] font-bold">⑥</span>
            <span className="label">VERIFICATION RESULT</span>
          </div>
        </div>
        <div className="p-4 text-center text-t-muted text-[10px] font-mono">
          Execute a query to see verified output
        </div>
      </div>
    );
  }

  const ts = result.trust_score;
  const claim = result.claim;
  const rawValue = claim.raw_value;
  const verifiedValue = result.verified_value;
  const hasCorrections = result.correction_log.length > 0;

  // Calculate difference
  let diffStr = "—";
  let diffPctStr = "—";
  if (rawValue !== null && verifiedValue !== null) {
    const diff = verifiedValue - rawValue;
    const diffPct = rawValue !== 0 ? ((diff / Math.abs(rawValue)) * 100) : 0;
    diffStr = diff >= 0 ? `+${formatDisplay(diff)}` : formatDisplay(diff);
    diffPctStr = `(${diffPct >= 0 ? "+" : ""}${diffPct.toFixed(1)}%)`;
  }

  // Verification status mapping
  const statusLabel = ts.status === "verified" ? "VERIFIED"
    : ts.status === "contradicted" ? "CONTRADICTED"
      : ts.status === "unverified" ? "UNVERIFIED"
        : ts.status === "error" ? "ERROR"
          : "PENDING";

  const statusColor = ts.status === "verified" ? "#00ff88"
    : ts.status === "contradicted" ? "#f87171"
      : ts.status === "unverified" ? "#888888"
        : ts.status === "error" ? "#f87171"
          : "#fbbf24";

  // Trust color from backend (or derive from label)
  const trustColor = ts.color || "#888888";
  const trustLabel = ts.label || "N/A";
  const trustScore = ts.score;

  const isIncorrect = hasCorrections || ts.status === "contradicted";

  return (
    <div
      className="panel"
      style={{
        borderLeft: `3px solid ${statusColor}`,
        boxShadow: `0 0 20px ${statusColor}15`,
      }}
    >
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <span style={{ color: statusColor }} className="text-[10px] font-bold">⑥</span>
          <span className="label" style={{ color: statusColor }}>VERIFICATION RESULT</span>
        </div>
        <div className="flex items-center gap-2">
          {latencyMs !== null && (
            <span className="text-[9px] font-mono text-t-muted">
              COMPLETED IN {(latencyMs / 1000).toFixed(2)}s
            </span>
          )}
        </div>
      </div>
      <div className="px-4 py-3">
        {isDegraded && (
          <div className="text-[9px] font-mono text-t-amber mb-2 px-2 py-1 bg-t-amber/5 border border-t-amber/15 rounded">
            ⚠ DEGRADED MODE — client-side DVL only, limited pipeline coverage
          </div>
        )}

        {/* Main result: Claimed vs Verified */}
        <div className="flex items-start gap-6">
          {/* Claimed & Verified values */}
          <div className="flex-1">
            <div className="flex items-end gap-4 mb-2">
              {/* Claimed */}
              <div>
                <div className="text-[9px] font-mono text-t-muted uppercase tracking-wider mb-1">Claimed</div>
                <div className="text-[24px] font-mono font-bold text-t-primary leading-none">
                  {rawValue !== null ? formatDisplay(rawValue) : "—"}
                  {claim.metric?.name && /margin|ratio|rate|percent|growth|yield|return/i.test(claim.metric.name) ? "%" : ""}
                </div>
              </div>

              {/* Arrow */}
              <div className="text-[20px] text-t-muted mb-1">→</div>

              {/* Verified */}
              <div>
                <div className="text-[9px] font-mono text-t-muted uppercase tracking-wider mb-1">Verified</div>
                <div
                  className="text-[24px] font-mono font-bold leading-none verified-flash"
                  style={{ color: trustColor }}
                >
                  {verifiedValue !== null ? formatDisplay(verifiedValue) : "—"}
                  {claim.metric?.name && /margin|ratio|rate|percent|growth|yield|return/i.test(claim.metric.name) ? "%" : ""}
                </div>
              </div>
            </div>

            {/* Difference */}
            <div className="text-[10px] font-mono text-t-secondary">
              Difference: <span className={isIncorrect ? "text-t-red" : "text-t-green"}>
                {diffStr}{isPercentageMetric(claim.metric?.name) ? "pp" : ""} {diffPctStr}
              </span>
            </div>
          </div>

          {/* Trust Score */}
          <div className="flex flex-col items-center shrink-0">
            <div className="text-[9px] font-mono text-t-muted uppercase tracking-wider mb-1">
              CONFIDENCE / TRUST
            </div>
            <div
              className="text-[28px] font-mono font-bold leading-none"
              style={{ color: trustColor, textShadow: `0 0 20px ${trustColor}33` }}
            >
              {trustScore !== null ? trustScore.toFixed(2) : "—"}
            </div>
            <div
              className="trust-badge mt-1"
              style={{
                background: `${trustColor}12`,
                color: trustColor,
                border: `1px solid ${trustColor}30`,
              }}
            >
              {trustLabel}
            </div>
          </div>
        </div>

        {/* Status bar */}
        <div className="flex items-center gap-3 mt-3 pt-2 border-t border-t-border text-[9px] font-mono">
          <span className="flex items-center gap-1.5">
            <span className="w-[6px] h-[6px] rounded-full" style={{ background: statusColor }} />
            <span style={{ color: statusColor }} className="font-bold">{statusLabel}</span>
          </span>
          {hasCorrections && (
            <span className="text-t-amber">
              {result.correction_log.length} CORRECTION{result.correction_log.length > 1 ? "S" : ""} APPLIED
            </span>
          )}
          <span className="text-t-muted ml-auto">
            mode: {result.mode}
          </span>
        </div>
      </div>
    </div>
  );
}

function formatDisplay(v: number): string {
  if (Math.abs(v) >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3) return v.toLocaleString(undefined, { maximumFractionDigits: 2 });
  if (Number.isInteger(v)) return String(v);
  // For small numbers, show appropriate precision
  const absV = Math.abs(v);
  if (absV < 0.01) return v.toFixed(4);
  if (absV < 1) return v.toFixed(4);
  return v.toFixed(2);
}

function isPercentageMetric(name?: string | null): boolean {
  if (!name) return false;
  return /margin|ratio|rate|percent|growth|yield|return/i.test(name);
}
