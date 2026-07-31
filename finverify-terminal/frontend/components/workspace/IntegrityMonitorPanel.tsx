"use client";

import React from "react";

/**
 * IntegrityMonitorPanel — Left column, bottom, 200px fixed.
 * Shows flagged claim counts per company, sorted descending.
 * Ships with mock data in Milestone 1 (labeled "DEMO DATA").
 * Per §5.3 of UI_IMPLEMENTATION_PLAN.md.
 */

interface FlaggedCompany {
  symbol: string;
  name: string;
  flagCount: number;
}

const DEMO_DATA: FlaggedCompany[] = [
  { symbol: "TSLA", name: "Tesla", flagCount: 3 },
  { symbol: "COIN", name: "Coinbase", flagCount: 2 },
  { symbol: "INTC", name: "Intel", flagCount: 4 },
  { symbol: "NVDA", name: "Nvidia", flagCount: 0 },
  { symbol: "AAPL", name: "Apple", flagCount: 0 },
];

interface IntegrityMonitorPanelProps {
  selectedSymbol: string | null;
  onSelectSymbol: (symbol: string) => void;
}

export default function IntegrityMonitorPanel({ selectedSymbol, onSelectSymbol }: IntegrityMonitorPanelProps) {
  const sorted = [...DEMO_DATA].sort((a, b) => b.flagCount - a.flagCount);

  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="panel-header">
        <span className="label text-t-amber">INTEGRITY MONITOR</span>
        <span className="text-[8px] text-t-amber font-mono border border-t-amber/20 bg-t-amber/[0.04] px-1 py-0.5 rounded">
          DEMO DATA
        </span>
      </div>

      <div className="flex-1 overflow-y-auto">
        {sorted.map((company) => {
          const hasFlagsClass = company.flagCount > 0;
          const isSelected = company.symbol === selectedSymbol;

          return (
            <button
              key={company.symbol}
              onClick={() => onSelectSymbol(company.symbol)}
              className={`
                w-full flex items-center justify-between px-2 py-1.5
                text-[10px] font-mono transition-all duration-150 border-l-2
                ${isSelected
                  ? "bg-white/[0.04] border-t-green"
                  : "border-transparent hover:bg-white/[0.02]"
                }
              `}
            >
              <div className="flex items-center gap-2">
                <span className={`font-bold ${hasFlagsClass ? "text-t-primary" : "text-t-muted"}`}>
                  {company.symbol}
                </span>
                <span className={`text-[9px] ${hasFlagsClass ? "text-t-secondary" : "text-t-muted/60"}`}>
                  {company.name}
                </span>
              </div>
              <span className={`
                font-bold tabular-nums px-1.5 py-0.5 rounded text-[9px]
                ${company.flagCount > 2
                  ? "text-t-red bg-t-red/[0.08]"
                  : company.flagCount > 0
                    ? "text-t-amber bg-t-amber/[0.08]"
                    : "text-t-muted/50"
                }
              `}>
                {company.flagCount > 0 ? `🚩 ${company.flagCount}` : "0"}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
