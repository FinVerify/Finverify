"use client";

import React from "react";

/**
 * IntegrityMonitorPanel — Stat-based layout per target screenshot.
 * Shows: Claims Monitored, Numerical Anomalies, High Severity, Data Sources Active.
 * Plus VIEW INTEGRITY DASHBOARD link.
 */

interface IntegrityMonitorPanelProps {
  selectedSymbol: string | null;
  onSelectSymbol: (symbol: string) => void;
}

interface IntegrityStat {
  label: string;
  value: string;
  change: string;
  changeColor: string;
}

const INTEGRITY_STATS: IntegrityStat[] = [
  { label: "Claims Monitored", value: "4,218", change: "▲ 12%", changeColor: "text-t-green" },
  { label: "Numerical Anomalies", value: "87", change: "▲ 4%", changeColor: "text-t-amber" },
  { label: "High Severity", value: "11", change: "▲ 2%", changeColor: "text-t-red" },
  { label: "Data Sources Active", value: "28", change: "", changeColor: "" },
];

export default function IntegrityMonitorPanel({ selectedSymbol: _selectedSymbol, onSelectSymbol: _onSelectSymbol }: IntegrityMonitorPanelProps) {
  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-t-border/50">
        <div className="flex items-center gap-1.5">
          <span className="text-t-amber text-[9px]">◆</span>
          <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
            INTEGRITY MONITOR
          </span>
        </div>
        <span className="text-[8px] text-t-amber font-mono border border-t-amber/20 bg-t-amber/[0.04] px-1 py-0.5 rounded">
          DEMO
        </span>
      </div>

      {/* Stats grid */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-2.5">
        {INTEGRITY_STATS.map((stat) => (
          <div key={stat.label} className="flex items-center justify-between">
            <span className="text-[9px] font-mono text-t-muted">{stat.label}</span>
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono font-bold text-t-primary tabular-nums">{stat.value}</span>
              {stat.change && (
                <span className={`text-[8px] font-mono font-semibold tabular-nums ${stat.changeColor}`}>
                  {stat.change}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* View Integrity Dashboard link */}
      <div className="px-2 py-1.5 border-t border-t-border/50 text-center">
        <span className="text-[8px] font-mono text-t-muted hover:text-t-secondary cursor-pointer transition-colors">
          VIEW INTEGRITY DASHBOARD →
        </span>
      </div>
    </div>
  );
}
