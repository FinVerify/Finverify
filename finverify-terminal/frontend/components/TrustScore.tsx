"use client";
import React, { useState } from "react";
import type { BatchVerificationResult } from "@/lib/api";

interface Props {
  result: BatchVerificationResult | null;
}

export default function TrustScore({ result }: Props) {
  const [showDetails, setShowDetails] = useState(false);

  if (!result) {
    return null;
  }

  const ts = result.trust_score;
  const trustColor = ts.color || "#888888";
  const trustLabel = ts.label || "N/A";
  const hasCorrections = result.correction_log.length > 0;
  const evidence = result.evidence;

  // Parse trust findings from reasons array
  // Backend serializes findings as strings like "Evidence tier: primary", "Corrections: none", etc.
  const findings: { label: string; value: string; color: string }[] = [];
  for (const reason of ts.reasons) {
    const parts = reason.split(": ");
    if (parts.length === 2) {
      const label = parts[0].trim();
      const val = parts[1].trim();
      let color = "#e0e0e0";
      // Color code based on value
      if (/primary|none|low|pass/i.test(val)) color = "#00ff88";
      else if (/secondary|scale|medium|partial|single/i.test(val)) color = "#fbbf24";
      else if (/model|user|high|fail|multiple|conflicting/i.test(val)) color = "#f87171";
      findings.push({ label, value: val.toUpperCase(), color });
    }
  }

  // SEC Evidence details for the evidence panel
  const secEvidence = evidence.filter((e) => e.source.kind === "primary_filing" || e.source.kind === "secondary");
  const primaryEvidence = secEvidence[0] || evidence[0];

  return (
    <div className="space-y-2">
      {/* Verification Summary — Evidence */}
      {primaryEvidence && (
        <div className="panel">
          <div className="panel-header">
            <span className="label text-t-cyan">EVIDENCE</span>
          </div>
          <div className="px-3 py-2">
            <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[10px] font-mono">
              <span className="text-t-muted">Primary Source</span>
              <span className="text-t-primary">{primaryEvidence.source.name}</span>
              {primaryEvidence.source.retrieved_at && (
                <>
                  <span className="text-t-muted">Filing Date</span>
                  <span className="text-t-secondary">
                    {new Date(primaryEvidence.source.retrieved_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                </>
              )}
              {primaryEvidence.period && (
                <>
                  <span className="text-t-muted">Period</span>
                  <span className="text-t-secondary">{primaryEvidence.period}</span>
                </>
              )}
              {primaryEvidence.locator && (
                <>
                  <span className="text-t-muted">Section</span>
                  <span className="text-t-secondary">{primaryEvidence.locator.replace(/_/g, " ")}</span>
                </>
              )}
              {primaryEvidence.entity && (
                <>
                  <span className="text-t-muted">Entity / Line</span>
                  <span className="text-t-secondary">{primaryEvidence.entity}</span>
                </>
              )}
              {primaryEvidence.source.url && (
                <>
                  <span className="text-t-muted">Source</span>
                  <a
                    href={primaryEvidence.source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-t-cyan hover:underline truncate"
                  >
                    VIEW DOCUMENT →
                  </a>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Correction Log */}
      {hasCorrections && (
        <div className="panel">
          <div className="panel-header">
            <span className="label text-t-amber">CORRECTION LOG</span>
            <span className="text-[9px] font-mono text-t-amber">
              {result.correction_log.length} CORRECTION{result.correction_log.length > 1 ? "S" : ""}
            </span>
          </div>
          <div className="px-3 py-2 space-y-2">
            {result.correction_log.map((c, i) => (
              <div key={i} className="space-y-1">
                <div className="flex items-center gap-2 text-[10px] font-mono">
                  <span className="text-t-muted">Original Claim</span>
                  <span className="text-t-primary">{c.before}</span>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-mono">
                  <span className="text-t-muted">Issue</span>
                  <span className="text-t-secondary">{c.description || c.rule}</span>
                </div>
                <div className="flex items-center gap-2 text-[10px] font-mono">
                  <span className="text-t-muted">Corrected Value</span>
                  <span className="text-t-green font-bold">{formatNum(c.after)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trust & Provenance */}
      <div className="panel">
        <div className="panel-header">
          <span className="label">TRUST & PROVENANCE</span>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-[9px] font-mono text-t-cyan hover:underline cursor-pointer"
          >
            {showDetails ? "HIDE DETAILS" : "HOW TRUST IS CALCULATED →"}
          </button>
        </div>
        <div className="px-3 py-2">
          {/* Trust score and label */}
          <div className="flex items-center gap-4 mb-2">
            <div>
              <div className="text-[9px] font-mono text-t-muted uppercase tracking-wider mb-1">Trust Score</div>
              <div
                className="text-[28px] font-mono font-bold leading-none"
                style={{ color: trustColor }}
              >
                {ts.score !== null ? ts.score.toFixed(2) : "—"}
              </div>
            </div>
            <div
              className="trust-badge"
              style={{
                background: `${trustColor}12`,
                color: trustColor,
                border: `1px solid ${trustColor}30`,
              }}
            >
              {trustLabel}
            </div>
          </div>

          {/* Trust findings — categorical, from reasons */}
          {findings.length > 0 && (
            <div className="space-y-1 pt-2 border-t border-t-border/30">
              {findings.map((f, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                  <span className="text-t-muted w-[140px] shrink-0">{f.label}</span>
                  <span style={{ color: f.color }} className="font-bold">{f.value}</span>
                </div>
              ))}
            </div>
          )}

          {/* Non-parsed reasons */}
          {ts.reasons.length > 0 && findings.length === 0 && (
            <div className="space-y-1 pt-2 border-t border-t-border/30">
              {ts.reasons.map((r, i) => (
                <div key={i} className="text-[10px] font-mono text-t-secondary">
                  • {r}
                </div>
              ))}
            </div>
          )}

          {/* Expanded details */}
          {showDetails && (
            <div className="mt-2 pt-2 border-t border-t-border/30 text-[9px] font-mono text-t-muted leading-relaxed">
              Trust scoring is computed by the backend verification engine based on evidence
              tier (PRIMARY/SECONDARY/MODEL), correction severity, claim ambiguity,
              cross-source consistency, and rule evidence agreement. These are categorical
              assessments — not independent numeric sub-scores.
            </div>
          )}
        </div>
      </div>

      {/* Limitations */}
      <div className="panel">
        <div className="panel-header">
          <span className="label text-t-muted">LIMITATIONS</span>
        </div>
        <div className="px-3 py-2 space-y-1 text-[10px] font-mono text-t-secondary">
          <div>• Based on reported numbers in 10-Q.</div>
          <div>• Does not account for non-GAAP adjustments.</div>
        </div>
      </div>
    </div>
  );
}

function formatNum(v: number): string {
  if (Math.abs(v) >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  return String(Math.round(v * 10000) / 10000);
}
