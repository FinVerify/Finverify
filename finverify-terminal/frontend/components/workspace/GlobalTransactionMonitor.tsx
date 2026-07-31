"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { useConnection } from "@/lib/connection";
import { verifyNumber, queryLLM, type QueryResponse } from "@/lib/api";

/**
 * GlobalTransactionMonitor — The hero center panel for the workspace default state.
 * SVG world map with animated transaction arcs, glowing city nodes, legend, stats,
 * sector filter tabs, and the command query input with quick actions.
 * Per §6 of visual parity spec.
 */

/* ── City Node Data ── */
interface CityNode {
  name: string;
  x: number; // SVG viewBox x (0-1000)
  y: number; // SVG viewBox y (0-500)
  volume: string;
  changePct: number;
  size: "lg" | "md" | "sm";
}

const CITIES: CityNode[] = [
  { name: "San Francisco", x: 120, y: 195, volume: "$1.2B", changePct: 12.4, size: "sm" },
  { name: "New York",      x: 230, y: 185, volume: "$3.8B", changePct: 8.7,  size: "lg" },
  { name: "São Paulo",     x: 290, y: 340, volume: "$780M", changePct: -2.1, size: "sm" },
  { name: "London",        x: 470, y: 145, volume: "$2.1B", changePct: 6.3,  size: "md" },
  { name: "Frankfurt",     x: 510, y: 160, volume: "$1.6B", changePct: 4.6,  size: "sm" },
  { name: "Johannesburg",  x: 540, y: 355, volume: "$420M", changePct: -1.3, size: "sm" },
  { name: "Mumbai",        x: 650, y: 240, volume: "$950M", changePct: 3.8,  size: "sm" },
  { name: "Singapore",     x: 730, y: 290, volume: "$2.9B", changePct: 9.2,  size: "md" },
  { name: "Tokyo",         x: 830, y: 185, volume: "$1.4B", changePct: 5.1,  size: "md" },
  { name: "Sydney",        x: 860, y: 380, volume: "$980M", changePct: 3.0,  size: "sm" },
];

/* ── Arc connections ── */
interface Arc {
  from: number; // index into CITIES
  to: number;
  color: string;
  flowType: "high" | "medium" | "low" | "decreasing";
}

const ARCS: Arc[] = [
  { from: 1, to: 3, color: "#00ff88", flowType: "high" },     // NY → London
  { from: 3, to: 4, color: "#00ff88", flowType: "high" },     // London → Frankfurt
  { from: 3, to: 8, color: "#fbbf24", flowType: "medium" },   // London → Tokyo
  { from: 1, to: 7, color: "#fbbf24", flowType: "medium" },   // NY → Singapore
  { from: 0, to: 1, color: "#00ff88", flowType: "high" },     // SF → NY
  { from: 1, to: 2, color: "#f97316", flowType: "low" },      // NY → São Paulo
  { from: 4, to: 5, color: "#f87171", flowType: "decreasing" }, // Frankfurt → Johannesburg
  { from: 7, to: 9, color: "#fbbf24", flowType: "medium" },   // Singapore → Sydney
  { from: 7, to: 6, color: "#00ff88", flowType: "high" },     // Singapore → Mumbai
];

const FLOW_LEGEND = [
  { label: "High Volume", color: "#00ff88" },
  { label: "Medium Volume", color: "#fbbf24" },
  { label: "Low Volume", color: "#f97316" },
  { label: "Decreasing", color: "#f87171" },
];

const SECTORS = [
  "ALL SECTORS", "TECHNOLOGY", "FINANCIALS", "HEALTHCARE", "ENERGY",
  "CONSUMER", "INDUSTRIALS", "UTILITIES", "REAL ESTATE", "MATERIALS",
];

/* ── Simplified world map path (low-poly continents) ── */
const WORLD_PATH = `M 80 180 Q 90 150 130 160 L 160 155 Q 180 140 220 150 L 250 145 Q 270 130 280 150 L 270 180 Q 260 210 240 230 L 220 260 Q 230 290 250 310 L 270 330 Q 290 360 280 390 L 260 400 Q 240 380 230 350 L 210 310 Q 190 280 170 300 L 150 330 Q 130 350 120 330 L 110 300 Q 100 270 90 250 L 80 220 Z
M 420 100 L 450 90 Q 480 80 520 95 L 560 100 Q 600 90 640 100 L 680 110 Q 720 100 760 115 L 800 120 Q 840 110 870 130 L 890 150 Q 900 170 890 190 L 870 200 Q 840 210 810 195 L 780 190 Q 750 200 730 220 L 720 250 Q 700 260 680 250 L 660 230 Q 640 220 620 230 L 600 250 Q 580 260 560 240 L 540 220 Q 520 210 500 220 L 480 230 Q 460 220 440 200 L 420 180 Q 410 160 420 140 Z
M 500 280 L 530 270 Q 560 260 580 280 L 590 310 Q 580 340 560 360 L 540 380 Q 520 390 500 370 L 490 340 Q 485 310 500 280 Z
M 750 300 Q 770 280 800 290 L 830 300 Q 860 310 880 340 L 890 370 Q 880 400 860 410 L 830 400 Q 800 390 780 370 L 760 340 Q 745 320 750 300 Z`;

/* ── Demo query helpers (reused from WorkspaceBottomBar) ── */
const KNOWN_TICKERS = ["AAPL", "TSLA", "JPM", "NVDA", "MSFT", "GS", "COIN", "INTC", "AMZN", "GOOG"];
const RATIO_KW = ["ratio", "margin", "return", "yield", "growth", "change", "increase", "decrease", "percent", "rate"];
const DEMO_NUMS: Record<string, number> = {
  "YoY operating margin change?": 0.1240, "CET1 ratio Q4 2022?": 10.935,
  "Net income increase YoY?": 1250000, "Revenue growth rate?": 8.14,
};

function quickDVL(question: string, raw: number): QueryResponse {
  const isRatio = RATIO_KW.some((kw) => question.toLowerCase().includes(kw));
  let value = raw;
  const log: QueryResponse["correction_log"] = [];
  if (isRatio && Math.abs(value) > 100) {
    log.push({ rule: "scale_div100", before: value, after: value / 100, description: "Scale corrected" });
    value = value / 100;
  } else if (isRatio && Math.abs(value) < 1) {
    log.push({ rule: "scale_mul100", before: value, after: value * 100, description: "Scale corrected" });
    value = value * 100;
  }
  const trust = log.length === 0 ? "HIGH" : "MEDIUM";
  const display = isRatio ? `${value.toFixed(2)}%` : value.toLocaleString();
  return { question, raw_text: `${raw}`, raw_number: raw, verified_number: value, correction_log: log, trust_score: trust, trust_color: trust === "HIGH" ? "#00ff88" : "#fbbf24", display_value: display, mode: "numerical", verified: true };
}

const QUICK_ACTIONS = [
  { icon: "📄", label: "Analyze AAPL 10-Q", query: "Analyze Apple 10-Q filing" },
  { icon: "🛡", label: "Verify TSLA revenue claim", query: "Verify TSLA revenue claim" },
  { icon: "⇄", label: "Compare NVDA vs AMD", query: "Compare NVDA vs AMD" },
  { icon: "✦", label: "Check market anomalies", query: "Check market anomalies" },
  { icon: "📊", label: "Generate report", query: "Generate financial report" },
];

/* ── Main Component ── */
interface GlobalTransactionMonitorProps {
  onSelectSymbol: (symbol: string) => void;
}

export default function GlobalTransactionMonitor({ onSelectSymbol }: GlobalTransactionMonitorProps) {
  const [activeSector, setActiveSector] = useState("ALL SECTORS");
  const [queryValue, setQueryValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { backendOnline } = useConnection();

  // Ctrl+K to focus
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
      if (e.key === "Escape" && document.activeElement === inputRef.current) {
        setQueryValue("");
        inputRef.current?.blur();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const handleSubmit = useCallback(async () => {
    const q = queryValue.trim();
    if (!q || isLoading) return;
    if (KNOWN_TICKERS.includes(q.toUpperCase())) {
      onSelectSymbol(q.toUpperCase());
      setQueryValue("");
      return;
    }
    setIsLoading(true);
    try {
      const knownDemo = DEMO_NUMS[q];
      if (knownDemo !== undefined) {
        if (backendOnline) { try { await verifyNumber(q, knownDemo); } catch { quickDVL(q, knownDemo); } }
        else { quickDVL(q, knownDemo); }
      } else if (backendOnline) { await queryLLM(q); }
    } catch { /* swallow */ }
    finally { setIsLoading(false); setQueryValue(""); }
  }, [queryValue, isLoading, backendOnline, onSelectSymbol]);

  const isMac = typeof navigator !== "undefined" && /Mac/.test(navigator.userAgent);

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-t-border/50">
        <div className="flex items-center gap-2">
          <span className="text-t-green text-[9px]">▷</span>
          <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
            GLOBAL TRANSACTION MONITOR
          </span>
          <span className="flex items-center gap-1 text-[8px] font-mono text-t-amber border border-t-amber/20 bg-t-amber/[0.04] px-1.5 py-0.5 rounded">
            DEMO
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 text-[8px] font-mono text-t-muted">
            <span>FLOW TYPE</span>
            <select className="bg-transparent border border-t-border/50 rounded px-1 py-0.5 text-[8px] text-t-secondary font-mono outline-none">
              <option>All Transactions</option>
            </select>
          </div>
          <div className="flex items-center gap-1 text-[8px] font-mono text-t-muted">
            <span>TIME RANGE</span>
            <select className="bg-transparent border border-t-border/50 rounded px-1 py-0.5 text-[8px] text-t-secondary font-mono outline-none">
              <option>24H</option>
              <option>7D</option>
              <option>30D</option>
            </select>
          </div>
          <button className="text-[10px] text-t-muted hover:text-t-secondary transition-colors" title="Refresh">⟳</button>
          <button className="text-[10px] text-t-muted hover:text-t-secondary transition-colors" title="Fullscreen">⛶</button>
        </div>
      </div>

      {/* ── Map Area ── */}
      <div className="flex-1 min-h-0 relative overflow-hidden bg-[#080a0e]">
        <svg viewBox="0 0 1000 500" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
          <defs>
            {/* Glow filters */}
            <filter id="nodeGlow">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <filter id="arcGlow">
              <feGaussianBlur stdDeviation="2" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            {/* Grid pattern */}
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.015)" strokeWidth="0.5" />
            </pattern>
          </defs>

          {/* Background grid */}
          <rect width="1000" height="500" fill="url(#grid)" />

          {/* Continents */}
          <path d={WORLD_PATH} fill="rgba(255,255,255,0.03)" stroke="rgba(255,255,255,0.06)" strokeWidth="0.5" />

          {/* Arcs */}
          {ARCS.map((arc, i) => {
            const from = CITIES[arc.from];
            const to = CITIES[arc.to];
            const midX = (from.x + to.x) / 2;
            const midY = Math.min(from.y, to.y) - 40 - Math.abs(from.x - to.x) * 0.1;
            return (
              <g key={i}>
                <path
                  d={`M ${from.x} ${from.y} Q ${midX} ${midY} ${to.x} ${to.y}`}
                  fill="none"
                  stroke={arc.color}
                  strokeWidth="1"
                  strokeOpacity="0.15"
                  filter="url(#arcGlow)"
                />
                <path
                  d={`M ${from.x} ${from.y} Q ${midX} ${midY} ${to.x} ${to.y}`}
                  fill="none"
                  stroke={arc.color}
                  strokeWidth="1.5"
                  strokeOpacity="0.6"
                  strokeDasharray="6 8"
                  className="arc-animated"
                  style={{ animationDelay: `${i * 0.3}s` }}
                />
              </g>
            );
          })}

          {/* City nodes */}
          {CITIES.map((city, i) => {
            const r = city.size === "lg" ? 6 : city.size === "md" ? 4.5 : 3.5;
            const isUp = city.changePct >= 0;
            const color = isUp ? "#00ff88" : "#f87171";
            return (
              <g key={i}>
                {/* Outer pulse */}
                <circle cx={city.x} cy={city.y} r={r * 2.5} fill={color} opacity="0.08" className="node-pulse" style={{ animationDelay: `${i * 0.5}s` }} />
                {/* Node */}
                <circle cx={city.x} cy={city.y} r={r} fill={color} opacity="0.9" filter="url(#nodeGlow)" />
                <circle cx={city.x} cy={city.y} r={r * 0.4} fill="#fff" opacity="0.8" />
                {/* Label */}
                <text x={city.x} y={city.y - r - 12} textAnchor="middle" className="fill-[rgba(255,255,255,0.5)]" style={{ fontSize: "7px", fontFamily: "monospace" }}>
                  {city.name.toUpperCase()}
                </text>
                <text x={city.x} y={city.y - r - 4} textAnchor="middle" className="fill-[rgba(255,255,255,0.85)]" style={{ fontSize: "9px", fontFamily: "monospace", fontWeight: "bold" }}>
                  {city.volume}
                </text>
                <text x={city.x + 25} y={city.y + 3} textAnchor="start" style={{ fontSize: "7px", fontFamily: "monospace", fontWeight: "bold", fill: color }}>
                  {isUp ? "▲" : "▼"}{Math.abs(city.changePct).toFixed(1)}%
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend overlay — bottom left */}
        <div className="absolute bottom-3 left-3 bg-[#0a0a0a]/80 border border-t-border/30 rounded px-2.5 py-2">
          <div className="text-[7px] font-mono text-t-muted uppercase tracking-wider mb-1.5">TRANSACTION FLOW</div>
          {FLOW_LEGEND.map((item) => (
            <div key={item.label} className="flex items-center gap-2 mb-0.5">
              <div className="w-[14px] h-[2px] rounded-full" style={{ backgroundColor: item.color }} />
              <span className="text-[7px] font-mono text-t-muted">{item.label}</span>
            </div>
          ))}
        </div>

        {/* Stats overlay — bottom right */}
        <div className="absolute bottom-3 right-3 bg-[#0a0a0a]/80 border border-t-border/30 rounded px-3 py-2">
          <div className="text-[7px] font-mono text-t-muted uppercase tracking-wider mb-1.5">GLOBAL STATS (24H)</div>
          <div className="flex gap-4">
            <div>
              <div className="text-[8px] font-mono text-t-muted">TOTAL VOLUME</div>
              <div className="text-[11px] font-mono font-bold text-t-primary tabular-nums">$28.4B</div>
              <div className="text-[7px] font-mono text-t-green">▲8.2%</div>
            </div>
            <div>
              <div className="text-[8px] font-mono text-t-muted">TRANSACTIONS</div>
              <div className="text-[11px] font-mono font-bold text-t-primary tabular-nums">128,842</div>
              <div className="text-[7px] font-mono text-t-green">▲6.1%</div>
            </div>
            <div>
              <div className="text-[8px] font-mono text-t-muted">ACTIVE NODES</div>
              <div className="text-[11px] font-mono font-bold text-t-primary tabular-nums">23</div>
              <div className="text-[7px] font-mono text-t-green">▲2</div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Sector Filter Tabs ── */}
      <div className="flex items-center gap-1 px-3 py-1.5 border-t border-t-border/50 overflow-x-auto">
        {SECTORS.map((sector) => (
          <button
            key={sector}
            onClick={() => setActiveSector(sector)}
            className={`text-[8px] font-mono font-bold px-2 py-1 rounded whitespace-nowrap transition-colors ${
              activeSector === sector
                ? "bg-t-green/15 text-t-green border border-t-green/30"
                : "text-t-muted border border-transparent hover:text-t-secondary hover:border-t-border/30"
            }`}
          >
            {sector}
          </button>
        ))}
      </div>

      {/* ── Command Query Input ── */}
      <div className="px-3 py-2 border-t border-t-border/50">
        <div className="flex items-center gap-2 bg-[#0d0d0d] border border-t-border/50 rounded-lg px-3 py-2.5 command-input-glow">
          <span className="text-t-muted text-[12px]">🔍</span>
          <input
            ref={inputRef}
            type="text"
            value={queryValue}
            onChange={(e) => setQueryValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleSubmit(); } }}
            placeholder={isLoading ? "Processing..." : "Ask FinVerify anything..."}
            disabled={isLoading}
            className="flex-1 bg-transparent text-[12px] font-mono text-t-green outline-none placeholder:text-t-muted/40 border-none disabled:opacity-50"
          />
          {isLoading && <span className="w-[6px] h-[6px] rounded-full bg-t-amber animate-pulse shrink-0" />}
          <span className="text-[8px] font-mono text-t-muted/50 bg-white/[0.03] border border-t-border px-1.5 py-0.5 rounded shrink-0">
            {isMac ? "⌘" : "Ctrl"}+K
          </span>
          <button
            onClick={handleSubmit}
            disabled={isLoading || !queryValue.trim()}
            className="w-[28px] h-[28px] rounded-full bg-t-green/20 border border-t-green/30 flex items-center justify-center text-t-green hover:bg-t-green/30 transition-colors disabled:opacity-30 shrink-0"
          >
            <span className="text-[12px]">→</span>
          </button>
        </div>

        {/* Quick Actions */}
        <div className="flex items-center gap-2 mt-2 overflow-x-auto pb-0.5">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => { setQueryValue(action.query); inputRef.current?.focus(); }}
              className="flex items-center gap-1 text-[8px] font-mono text-t-muted border border-t-border/30 rounded px-2 py-1 whitespace-nowrap hover:text-t-secondary hover:border-t-border/60 transition-colors"
            >
              <span>{action.icon}</span>
              <span>{action.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
