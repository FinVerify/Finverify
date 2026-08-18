"use client";
import React from "react";
import type { BatchCalculation, BatchCorrectionEntry } from "@/lib/api";

interface Props {
  calculations: BatchCalculation[];
  correctionLog: BatchCorrectionEntry[];
  isDegraded?: boolean;
}

export default function CalculationPanel({ calculations, correctionLog, isDegraded }: Props) {
  const hasCorrections = correctionLog.length > 0;
  const calc = calculations[0]; // Primary calculation

  return (
    <div className="panel" style={{ borderLeft: `3px solid ${hasCorrections ? "#fbbf24" : "#00ff88"}` }}>
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <span className={`${hasCorrections ? "text-t-amber" : "text-t-green"} text-[10px] font-bold`}>④</span>
          <span className={`label ${hasCorrections ? "text-t-amber" : "text-t-green"}`}>CALCULATION RECONSTRUCTED</span>
        </div>
        <span className={`text-[9px] font-mono ${hasCorrections ? "text-t-amber" : "text-t-green"}`}>
          {hasCorrections ? `${correctionLog.length} CORRECTION${correctionLog.length > 1 ? "S" : ""}` : "CLEAN ✓"}
        </span>
      </div>
      <div className="px-3 py-2 space-y-2">
        {isDegraded && (
          <div className="text-[9px] font-mono text-t-amber mb-1">
            ⚠ DEGRADED — client-side DVL only
          </div>
        )}

        {calc && (
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[10px] font-mono">
            {/* Inputs */}
            {Object.entries(calc.inputs).map(([key, val]) => (
              <React.Fragment key={key}>
                <span className="text-t-muted capitalize">{key.replace(/_/g, " ")}</span>
                <span className="text-t-primary">
                  {typeof val === "number" ? formatNum(val) : String(val)}
                </span>
              </React.Fragment>
            ))}
            {/* Output */}
            {calc.output !== null && (
              <>
                <span className="text-t-muted">Output</span>
                <span className="text-t-green font-bold">{formatNum(calc.output)}</span>
              </>
            )}
            {/* Method */}
            <span className="text-t-muted">Method</span>
            <span className="text-t-secondary">{calc.name.replace(/_/g, " ")}</span>
          </div>
        )}

        {/* Correction log */}
        {hasCorrections && (
          <div className="pt-2 border-t border-t-border/30 space-y-1">
            <div className="text-[9px] font-mono text-t-muted uppercase tracking-wider">CORRECTION LOG</div>
            {correctionLog.map((c, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                <span className="text-t-amber font-bold">{c.rule}</span>
                <span className="text-t-muted">→</span>
                <span className="text-t-secondary">{formatNum(c.before)}</span>
                <span className="text-t-green">→</span>
                <span className="text-t-green font-bold">{formatNum(c.after)}</span>
                {c.description && (
                  <span className="text-t-muted text-[9px] truncate">({c.description})</span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function formatNum(v: number): string {
  if (Math.abs(v) >= 1e9) return `$ ${(v / 1e9).toFixed(2)}B`;
  if (Math.abs(v) >= 1e6) return `$ ${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3 && Math.abs(v) < 1e6) return v.toLocaleString();
  return String(Math.round(v * 10000) / 10000);
}
