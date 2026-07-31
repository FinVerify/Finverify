"use client";

import React from "react";

/**
 * Right column panels for the Intelligence Workspace.
 * Restyled per visual parity spec §7 — per-row type icons, LIVE tags,
 * VIEW ALL links, Earnings Radar → Earnings Calendar rename.
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

/* ── News Radar (§7) ── */
export function NewsRadarPanel() {
  const items = [
    { icon: "🟢", title: "NVDA beats earnings estimates", detail: "Revenue up 122% YoY — data center segment drives growth", time: "2m", riskColor: "text-t-green" },
    { icon: "⚠", title: "TSLA margin compression deepens", detail: "Gross margin hits 17.4% — price cuts continue to weigh", time: "14m", riskColor: "text-t-amber" },
    { icon: "⚪", title: "Fed holds rates steady", detail: "Powell signals September cut possible pending data", time: "1h" },
    { icon: "🔴", title: "COIN faces SEC scrutiny", detail: "Staking services classification challenged in court", time: "3h", riskColor: "text-t-red" },
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

/* ── Filing Radar (§7) ── */
export function FilingRadarPanel() {
  const items = [
    { icon: "📋", title: "AAPL 10-Q Filed", detail: "Q3 FY2024 — Revenue $85.8B", time: "1d" },
    { icon: "🚩", title: "INTC 8-K Material Event", detail: "Workforce reduction — 15K layoffs announced", time: "2d", riskColor: "text-t-red" },
    { icon: "📋", title: "JPM 10-K Annual", detail: "FY2023 — Record net income $49.6B", time: "5d" },
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

/* ── Earnings Calendar (§7 — renamed from Earnings Radar) ── */
export function EarningsRadarPanel() {
  const items = [
    { icon: "🎙️", title: "MSFT Q4 Earnings", detail: "After-hours — Azure growth key focus", time: "TODAY", riskColor: "text-t-green" },
    { icon: "🎙️", title: "META Q2 Earnings", detail: "Ad revenue rebound expected", time: "TOMORROW" },
    { icon: "📊", title: "AMZN Q2 Earnings", detail: "AWS margins — consensus $0.83 EPS", time: "AUG 1" },
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

/* ── Sector Monitor (kept below the fold, unchanged structure) ── */
const SECTORS = [
  { name: "Financials", change: 1.2 },
  { name: "Technology", change: 0.8 },
  { name: "Healthcare", change: -0.3 },
  { name: "Energy", change: 0.5 },
  { name: "Consumer", change: 0.1 },
  { name: "Industrials", change: -0.1 },
  { name: "Real Estate", change: -0.6 },
];

export function SectorMonitorPanel() {
  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="panel-header">
        <span className="label text-t-amber">SECTOR MONITOR</span>
        <span className="text-[8px] text-t-muted font-mono">PRICE CHANGE</span>
      </div>
      <div className="flex-1 overflow-y-auto p-1.5">
        {SECTORS.map((sector) => {
          const isUp = sector.change >= 0;
          const color = isUp ? "text-t-green" : "text-t-red";
          const barWidth = Math.min(Math.abs(sector.change) * 40, 100);

          return (
            <div
              key={sector.name}
              className="flex items-center gap-2 px-1.5 py-1 text-[9px] font-mono"
            >
              <span className="text-t-secondary w-[72px] truncate">
                {sector.name}
              </span>
              <div className="flex-1 h-[3px] bg-t-border/50 rounded-full overflow-hidden relative">
                <div
                  className={`h-full rounded-full ${isUp ? "bg-t-green/60" : "bg-t-red/60"}`}
                  style={{ width: `${barWidth}%` }}
                />
              </div>
              <span className={`tabular-nums font-semibold w-[40px] text-right ${color}`}>
                {isUp ? "+" : ""}{sector.change.toFixed(1)}%
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
