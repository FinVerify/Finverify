"use client";

import React from "react";

/**
 * Right column panels for the Intelligence Workspace.
 * Enhanced per target screenshot — richer data, LIVE tags,
 * Sector Monitor with verification health column, VIEW ALL links.
 */

/* ── Shared: Radar item component ── */
function RadarItem({
  icon,
  title,
  detail,
  time,
  riskColor,
}: {
  icon?: string;
  title: string;
  detail: string;
  time: string;
  riskColor?: string;
}) {
  return (
    <div className="flex items-start gap-2 px-2 py-1.5 border-b border-t-border/30 last:border-b-0 hover:bg-white/[0.02] transition-colors text-[9px] font-mono">
      {icon && <span className="shrink-0 mt-0.5">{icon}</span>}
      <div className="flex-1 min-w-0">
        <div className={`font-bold truncate ${riskColor ?? "text-t-secondary"}`}>
          {title}
        </div>
        <div className="text-t-muted truncate">{detail}</div>
      </div>
      <span className="text-t-muted/60 shrink-0 tabular-nums">{time}</span>
    </div>
  );
}

/* ── News Radar ── */
export function NewsRadarPanel() {
  const items = [
    { icon: "🟢", title: "NVDA beats earnings estimates", detail: "Revenue up 122% YoY — data center segment drives growth", time: "3m", riskColor: "text-t-green" },
    { icon: "⚠", title: "TSLA margin compression deepens", detail: "Gross margin hits 17.4% — price cuts continue", time: "1h", riskColor: "text-t-amber" },
    { icon: "⚪", title: "Fed holds rates steady", detail: "Powell signals September cut possible", time: "1h" },
  ];

  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="panel-header">
        <span className="label text-t-blue">NEWS RADAR</span>
        <span className="flex items-center gap-1 text-[8px] font-mono text-t-green">
          <span className="w-[4px] h-[4px] rounded-full bg-t-green live-pulse" />
          LIVE
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {items.map((item, i) => (
          <RadarItem key={i} {...item} />
        ))}
      </div>
      <div className="px-2 py-1 border-t border-t-border/50 text-center">
        <span className="text-[8px] font-mono text-t-muted hover:text-t-secondary cursor-pointer transition-colors">
          VIEW ALL NEWS →
        </span>
      </div>
    </div>
  );
}

/* ── Filing Radar ── */
export function FilingRadarPanel() {
  const items = [
    { icon: "📋", title: "AAPL 10-Q Filed", detail: "Q3 FY2024 — Revenue $85.8B", time: "1d" },
    { icon: "🚩", title: "INTC 8-K Material Event", detail: "Workforce reduction — 15K layoffs announced", time: "2d", riskColor: "text-t-red" },
    { icon: "📋", title: "JPM 10-K Annual", detail: "FY2023 Annual Report Filed", time: "5d" },
  ];

  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="panel-header">
        <span className="label text-t-cyan">FILING RADAR</span>
        <span className="flex items-center gap-1 text-[8px] font-mono text-t-green">
          <span className="w-[4px] h-[4px] rounded-full bg-t-green live-pulse" />
          LIVE
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {items.map((item, i) => (
          <RadarItem key={i} {...item} />
        ))}
      </div>
      <div className="px-2 py-1 border-t border-t-border/50 text-center">
        <span className="text-[8px] font-mono text-t-muted hover:text-t-secondary cursor-pointer transition-colors">
          VIEW ALL FILINGS →
        </span>
      </div>
    </div>
  );
}

/* ── Earnings Calendar ── */
export function EarningsRadarPanel() {
  const items = [
    { icon: "🎙️", title: "MSFT Q4 Earnings", detail: "After-hours — Azure growth key focus", time: "TODAY", riskColor: "text-t-green" },
    { icon: "🎙️", title: "META Q2 Earnings", detail: "Ad revenue rebound expected", time: "TOMORROW" },
    { icon: "📊", title: "AMZN Q2 Earnings", detail: "AWS growth outlook", time: "AUG 1" },
  ];

  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="panel-header">
        <span className="label text-t-purple">EARNINGS CALENDAR</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {items.map((item, i) => (
          <RadarItem key={i} {...item} />
        ))}
      </div>
      <div className="px-2 py-1 border-t border-t-border/50 text-center">
        <span className="text-[8px] font-mono text-t-muted hover:text-t-secondary cursor-pointer transition-colors">
          VIEW CALENDAR →
        </span>
      </div>
    </div>
  );
}

/* ── Sector Monitor — Enhanced with verification health and time period tabs ── */
interface SectorData {
  name: string;
  change: number;
  verifHealth: number;
}

const SECTORS: SectorData[] = [
  { name: "Financials", change: 0.82, verifHealth: 0.95 },
  { name: "Technology", change: 0.62, verifHealth: 0.95 },
  { name: "Communication Services", change: 0.43, verifHealth: 0.93 },
  { name: "Consumer Cyclical", change: -0.03, verifHealth: 0.89 },
  { name: "Industrials", change: 0.21, verifHealth: 0.91 },
  { name: "Healthcare", change: -0.31, verifHealth: 0.91 },
  { name: "Energy", change: -0.47, verifHealth: 0.88 },
  { name: "Utilities", change: -0.62, verifHealth: 0.85 },
  { name: "Real Estate", change: -0.71, verifHealth: 0.84 },
];

export function SectorMonitorPanel() {
  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="panel-header">
        <span className="label text-t-amber">SECTOR MONITOR</span>
        <div className="flex items-center gap-1">
          {["1D", "1W", "1M"].map((tf) => (
            <button
              key={tf}
              className={`text-[7px] font-mono px-1 py-0.5 rounded transition-colors ${
                tf === "1D" ? "bg-t-green/15 text-t-green" : "text-t-muted hover:text-t-secondary"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-[1fr_48px_70px] gap-1 px-2 py-0.5 text-[7px] font-mono text-t-muted uppercase tracking-wider border-b border-t-border/30">
        <span>SECTOR</span>
        <span className="text-right">% CHANGE</span>
        <span className="text-right">▼ VERIFICATION HEALTH</span>
      </div>

      <div className="flex-1 overflow-y-auto p-1">
        {SECTORS.map((sector) => {
          const isUp = sector.change >= 0;
          const color = isUp ? "text-t-green" : "text-t-red";
          const healthColor = sector.verifHealth >= 0.92 ? "text-t-green" : sector.verifHealth >= 0.88 ? "text-t-amber" : "text-t-red";

          return (
            <div
              key={sector.name}
              className="grid grid-cols-[1fr_48px_70px] gap-1 items-center px-1.5 py-1 text-[9px] font-mono hover:bg-white/[0.02] transition-colors"
            >
              <span className="text-t-secondary truncate">
                {sector.name}
              </span>
              <span className={`tabular-nums font-semibold text-right ${color}`}>
                {isUp ? "+" : ""}{sector.change.toFixed(2)}%
              </span>
              <span className={`tabular-nums font-semibold text-right ${healthColor}`}>
                {(sector.verifHealth * 100).toFixed(1)}
              </span>
            </div>
          );
        })}
      </div>

      <div className="px-2 py-1 border-t border-t-border/50 text-center">
        <span className="text-[8px] font-mono text-t-muted hover:text-t-secondary cursor-pointer transition-colors">
          VIEW SECTOR ANALYSIS →
        </span>
      </div>
    </div>
  );
}
