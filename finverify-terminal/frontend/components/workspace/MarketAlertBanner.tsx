"use client";

import React from "react";

/**
 * MarketAlertBanner — Full-width scrolling alert bar.
 * Enhanced per target: more alerts, VIEW ALL (8) button.
 */

const ALERTS = [
  { time: "16:35", text: "TSLA margin compression deepens – gross margin hits 17.4%" },
  { time: "16:30", text: "Fed holds rates steady – Powell signals September cut possible" },
  { time: "16:28", text: "Apple files 10-Q quarterly report" },
  { time: "16:25", text: "NVDA beats earnings estimates" },
  { time: "16:20", text: "JPM Q2 earnings exceed expectations" },
];

export default function MarketAlertBanner() {
  return (
    <div className="h-[28px] flex items-center bg-[#0c0908] border-b border-t-amber/10 overflow-hidden relative">
      {/* Tag */}
      <div className="flex items-center gap-1.5 pl-3 pr-3 border-r border-t-amber/20 shrink-0">
        <span className="text-[8px] font-mono font-bold text-t-amber bg-t-amber/10 px-1.5 py-0.5 rounded">
          ▶ MARKET ALERTS
        </span>
      </div>

      {/* Scrolling alerts */}
      <div className="flex-1 overflow-hidden relative ticker-viewport">
        <div className="ticker-scroll flex items-center gap-6 whitespace-nowrap px-4">
          {[...ALERTS, ...ALERTS].map((alert, i) => (
            <span key={i} className="flex items-center gap-2 text-[9px] font-mono">
              <span className="text-t-muted/60 tabular-nums">{alert.time}</span>
              <span className="text-t-amber">◆</span>
              <span className="text-t-secondary">{alert.text}</span>
            </span>
          ))}
        </div>
      </div>

      {/* View All */}
      <div className="shrink-0 pr-3 pl-2 border-l border-t-amber/20">
        <span className="text-[8px] font-mono text-t-amber hover:text-t-amber/80 cursor-pointer transition-colors">
          VIEW ALL (8) →
        </span>
      </div>
    </div>
  );
}
