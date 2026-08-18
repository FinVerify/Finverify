"use client";
import React from "react";
import type { BatchConstraintResult } from "@/lib/api";

interface Props {
  constraintResult: BatchConstraintResult | null;
  batchConstraintResult: BatchConstraintResult | null;
  isDegraded?: boolean;
}

export default function ConstraintsPanel({ constraintResult, batchConstraintResult, isDegraded }: Props) {
  // Use per-result constraint_result first, fall back to batch-level
  const cr = constraintResult || batchConstraintResult;

  if (isDegraded) {
    return (
      <div className="panel" style={{ borderLeft: "3px solid #888" }}>
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <span className="text-t-muted text-[10px] font-bold">⑤</span>
            <span className="label text-t-muted">CONSTRAINTS CHECK</span>
          </div>
          <span className="text-[9px] font-mono text-t-muted">NOT PERFORMED</span>
        </div>
        <div className="px-3 py-2">
          <div className="text-[10px] font-mono text-t-muted">
            Constraint verification not available in degraded mode.
          </div>
        </div>
      </div>
    );
  }

  // null constraint_result — legitimate for single-claim requests
  if (!cr) {
    return (
      <div className="panel" style={{ borderLeft: "3px solid #888" }}>
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <span className="text-t-muted text-[10px] font-bold">⑤</span>
            <span className="label text-t-muted">CONSTRAINTS CHECK</span>
          </div>
          <span className="text-[9px] font-mono text-t-muted">NOT APPLICABLE</span>
        </div>
        <div className="px-3 py-2">
          <div className="text-[10px] font-mono text-t-muted leading-relaxed">
            This claim did not have enough related, resolved metrics for constraint
            verification to run. This is expected behavior for single-claim requests.
          </div>
        </div>
      </div>
    );
  }

  // Constraints ran — render real equation outcomes
  const statusColor = cr.status === "consistent" ? "#00ff88"
    : cr.status === "inconsistent" ? "#f87171"
      : cr.status === "indeterminate" ? "#fbbf24"
        : "#888";

  const statusLabel = cr.status === "consistent" ? "PASSED"
    : cr.status === "inconsistent" ? "VIOLATIONS FOUND"
      : cr.status === "indeterminate" ? "INDETERMINATE"
        : "NOT EVALUATED";

  const cov = cr.coverage;

  return (
    <div className="panel" style={{ borderLeft: `3px solid ${statusColor}` }}>
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <span style={{ color: statusColor }} className="text-[10px] font-bold">⑤</span>
          <span className="label" style={{ color: statusColor }}>CONSTRAINTS CHECK</span>
        </div>
        <span className="text-[9px] font-mono" style={{ color: statusColor }}>
          {statusLabel} ({cov.verified + cov.violated}/{cov.loaded})
        </span>
      </div>
      <div className="px-3 py-2 space-y-2">
        {/* Coverage summary */}
        <div className="flex flex-wrap gap-3 text-[9px] font-mono">
          {cov.verified > 0 && (
            <span className="text-t-green">✓ {cov.verified} verified</span>
          )}
          {cov.violated > 0 && (
            <span className="text-t-red">✗ {cov.violated} violated</span>
          )}
          {cov.indeterminate > 0 && (
            <span className="text-t-amber">? {cov.indeterminate} indeterminate</span>
          )}
          {cov.derivable > 0 && (
            <span className="text-t-cyan">↻ {cov.derivable} derivable</span>
          )}
        </div>

        {/* Equation outcomes */}
        {cr.outcomes.length > 0 && (
          <div className="space-y-1 pt-1 border-t border-t-border/30">
            {cr.outcomes.slice(0, 8).map((outcome, i) => {
              const oColor =
                outcome.status === "verified" ? "text-t-green"
                  : outcome.status === "violation" ? "text-t-red"
                    : outcome.status === "indeterminate" ? "text-t-amber"
                      : "text-t-muted";
              const oIcon =
                outcome.status === "verified" ? "✓"
                  : outcome.status === "violation" ? "✗"
                    : outcome.status === "indeterminate" ? "?"
                      : "—";

              return (
                <div key={i} className="flex items-start gap-2 text-[10px] font-mono">
                  <span className={`${oColor} shrink-0`}>{oIcon}</span>
                  <span className="text-t-primary shrink-0">{outcome.target}</span>
                  <span className="text-t-muted">=</span>
                  <span className="text-t-secondary truncate">{outcome.formula}</span>
                  <span className={oColor}>{outcome.status.toUpperCase()}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Violations detail */}
        {cr.violations.length > 0 && (
          <div className="pt-1 border-t border-t-border/30 space-y-1">
            <div className="text-[9px] font-mono text-t-red uppercase tracking-wider">VIOLATIONS</div>
            {cr.violations.map((v, i) => (
              <div key={i} className="text-[10px] font-mono text-t-secondary">
                <span className="text-t-red">{v.metric}:</span>{" "}
                expected {v.expected.toFixed(4)}, got {v.actual.toFixed(4)}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
