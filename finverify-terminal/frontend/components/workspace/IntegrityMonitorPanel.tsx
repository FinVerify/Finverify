"use client";

import React from "react";

/**
 * IntegrityMonitorPanel — Polished per visual parity spec §5.
 * Diamond bullets, colored severity bars, VIEW ALL COMPANIES link.
 */

interface FlaggedCompany {
  symbol: string;
  name: string;
  flagCount: number;
}

const DEMO_DATA: FlaggedCompany[] = [
  { symbol: "INTC", name: "Intel", flagCount: 4 },
  { symbol: "TSLA", name: "Tesla", flagCount: 3 },
  { symbol: "COIN", name: "Coinbase", flagCount: 2 },
  { symbol: "NVDA", name: "Nvidia", flagCount: 1 },
  { symbol: "AAPL", name: "Apple", flagCount: 0 },
];

interface IntegrityMonitorPanelProps {
  selectedSymbol: string | null;
  onSelectSymbol: (symbol: string) => void;
}

export default function IntegrityMonitorPanel({ selectedSymbol, onSelectSymbol }: IntegrityMonitorPanelProps) {
  const maxFlags = Math.max(...DEMO_DATA.map((c) => c.flagCount), 1);

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

      <div className="flex-1 overflow-y-auto">
        {DEMO_DATA.map((company) => {
          const isSelected = company.symbol === selectedSymbol;
          const barWidth = company.flagCount > 0 ? (company.flagCount / maxFlags) * 100 : 0;
          const barColor = company.flagCount > 2 ? "bg-t-red" : company.flagCount > 0 ? "bg-t-amber" : "bg-t-muted/20";

          return (
            <button
              key={company.symbol}
              onClick={() => onSelectSymbol(company.symbol)}
              className={`
                w-full flex items-center justify-between px-2 py-2
                text-[10px] font-mono transition-all duration-150 border-l-2
                ${isSelected
                  ? "bg-white/[0.04] border-t-green"
                  : "border-transparent hover:bg-white/[0.02]"
                }
              `}
            >
              <div className="flex items-center gap-2 w-[90px]">
                <span className={`font-bold ${company.flagCount > 0 ? "text-t-primary" : "text-t-muted"}`}>
                  {company.symbol}
                </span>
                <span className={`text-[9px] ${company.flagCount > 0 ? "text-t-secondary" : "text-t-muted/60"}`}>
                  {company.name}
                </span>
              </div>

              {/* Severity bar */}
              <div className="flex-1 mx-2 h-[6px] bg-t-border/30 rounded-full overflow-hidden">
                {barWidth > 0 && (
                  <div
                    className={`h-full rounded-full ${barColor} transition-all duration-300`}
                    style={{ width: `${barWidth}%` }}
                  />
                )}
              </div>

              {/* Flag count with diamond */}
              <span className={`
                font-bold tabular-nums text-[9px] flex items-center gap-1
                ${company.flagCount > 2
                  ? "text-t-red"
                  : company.flagCount > 0
                    ? "text-t-amber"
                    : "text-t-muted/50"
                }
              `}>
                {company.flagCount > 0 && <span>◆</span>}
                {company.flagCount}
              </span>
            </button>
          );
        })}
      </div>

      {/* VIEW ALL link */}
      <div className="px-2 py-1.5 border-t border-t-border/50 text-center">
        <span className="text-[8px] font-mono text-t-muted hover:text-t-secondary cursor-pointer transition-colors">
          VIEW ALL COMPANIES →
        </span>
      </div>
    </div>
  );
}
