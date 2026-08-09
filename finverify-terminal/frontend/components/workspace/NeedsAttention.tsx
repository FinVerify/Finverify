"use client";

import React from "react";

/**
 * NeedsAttention — Surfaces claims/items requiring review.
 * Per target screenshot — compact terminal-style list with severity indicators.
 */

interface AttentionItem {
  symbol: string;
  description: string;
  detail: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
}

const DEMO_ITEMS: AttentionItem[] = [
  { symbol: "TSLA", description: "TSLA Operating Margin (Q2 FY24)", detail: "Reported 17.4% vs Calculated 15.8%", severity: "HIGH" },
  { symbol: "INTC", description: "INTC Gross Margin (Q1 FY24)", detail: "Cross-source discrepancy detected", severity: "HIGH" },
  { symbol: "META", description: "META Reality Labs Expense (Q2 FY24)", detail: "Unusual classification pattern", severity: "MEDIUM" },
  { symbol: "SBUX", description: "SBUX Comparable Sales (Q2 FY24)", detail: "Regional vs global mismatch", severity: "LOW" },
];

function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === "HIGH"
      ? "bg-t-red/10 text-t-red border-t-red/20"
      : severity === "MEDIUM"
      ? "bg-t-amber/10 text-t-amber border-t-amber/20"
      : "bg-t-green/10 text-t-green border-t-green/20";
  return (
    <span className={`text-[7px] font-mono font-bold px-1 py-0.5 rounded border ${cls}`}>
      {severity}
    </span>
  );
}

export default function NeedsAttention() {
  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-t-border/50">
        <div className="flex items-center gap-1.5">
          <span className="text-t-red text-[9px]">⚠</span>
          <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
            NEEDS ATTENTION
          </span>
        </div>
        <span className="text-[7px] font-mono text-t-muted">5 ITEMS</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {DEMO_ITEMS.map((item, i) => (
          <div
            key={i}
            className="px-2 py-1.5 border-b border-t-border/20 last:border-b-0 hover:bg-white/[0.02] transition-colors text-[9px] font-mono"
          >
            <div className="flex items-center justify-between gap-1">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className={`text-[8px] ${item.severity === "HIGH" ? "text-t-red" : "text-t-amber"}`}>▶</span>
                <span className={`font-bold truncate ${
                  item.severity === "HIGH" ? "text-t-red" : 
                  item.severity === "MEDIUM" ? "text-t-amber" : "text-t-secondary"
                }`}>
                  {item.description}
                </span>
              </div>
              <SeverityBadge severity={item.severity} />
            </div>
            <div className="text-t-muted text-[8px] mt-0.5 ml-4 truncate">{item.detail}</div>
          </div>
        ))}
      </div>
      <div className="px-2 py-1 border-t border-t-border/50 text-center">
        <span className="text-[8px] font-mono text-t-muted hover:text-t-secondary cursor-pointer transition-colors">
          VIEW ALL ITEMS →
        </span>
      </div>
    </div>
  );
}
