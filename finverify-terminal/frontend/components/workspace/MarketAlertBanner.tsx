"use client";

import React from "react";

/**
 * MarketAlertBanner — Full-width scrolling alert bar under the ticker.
 * ~32px tall, amber-accented, same marquee mechanics as TickerBar.
 */

const ALERTS = [
  { time: "16:35", text: "NVIDIA beats earnings estimates: Revenue up 122% YoY" },
  { time: "16:32", text: "TSLA margin compression deepens – gross margin hits 17.4%" },
  { time: "16:30", text: "Fed holds rates steady – Powell signals September cut possible" },
  { time: "16:28", text: "Apple files 10-Q quarterly report with SEC" },
  { time: "16:25", text: "Coinbase faces renewed SEC scrutiny on staking services" },
];

export default function MarketAlertBanner() {
  return (
    <div className="h-[32px] flex items-center bg-[#0c0908] border-b border-t-amber/10 overflow-hidden relative">
      {/* Tag */}
      <div className="flex items-center gap-1.5 pl-3 pr-3 border-r border-t-amber/20 shrink-0">
        <span className="text-[8px] font-mono font-bold text-t-amber bg-t-amber/10 px-1.5 py-0.5 rounded">
          ▶ MARKET ALERT
        </span>
      </div>

      {/* Scrolling alerts */}
      <div className="flex-1 overflow-hidden relative ticker-viewport">
        <div className="ticker-scroll flex items-center gap-6 whitespace-nowrap px-4">
          {[...ALERTS, ...ALERTS].map((alert, i) => (
            <span key={i} className="flex items-center gap-2 text-[10px] font-mono">
              <span className="text-t-muted/60">{alert.time}</span>
              <span className="text-t-amber">◆</span>
              <span className="text-t-secondary">{alert.text}</span>
            </span>
          ))}
        </div>
      </div>

      {/* View All */}
      <div className="shrink-0 pr-3 pl-2 border-l border-t-amber/20">
        <span className="text-[8px] font-mono text-t-amber hover:text-t-amber/80 cursor-pointer transition-colors">
          VIEW ALL →
        </span>
      </div>
    </div>
  );
}
