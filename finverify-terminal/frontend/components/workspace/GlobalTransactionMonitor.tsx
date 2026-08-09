"use client";

import React from "react";
import { WORLD_MAP_PATHS } from "./worldMapData";

/**
 * GlobalTransactionMonitor — Real geographic world map with animated transaction arcs.
 * Uses Natural Earth 110m land data rendered as SVG via Mercator projection.
 * City nodes positioned at real lon/lat coordinates.
 * Command bar logic lives in CommandBar.tsx.
 */

/* ── Mercator Projection (matches the generator) ── */
const MAP_W = 1000;
const MAP_H = 500;

function mercatorProject(lon: number, lat: number): [number, number] {
  const clampedLat = Math.max(-85, Math.min(85, lat));
  const x = (lon + 180) * (MAP_W / 360);
  const latRad = (clampedLat * Math.PI) / 180;
  const mercN = Math.log(Math.tan(Math.PI / 4 + latRad / 2));
  const y = MAP_H / 2 - (MAP_W * mercN) / (2 * Math.PI);
  return [x, y];
}

/* ── City Node Data with real lat/lng ── */
interface CityNode {
  name: string;
  lon: number;
  lat: number;
  volume: string;
  changePct: number;
  size: "lg" | "md" | "sm";
}

const CITIES: CityNode[] = [
  { name: "San Francisco", lon: -122.42, lat: 37.77, volume: "$1.2B", changePct: 12.4, size: "sm" },
  { name: "New York",      lon: -74.01,  lat: 40.71, volume: "$3.8B", changePct: 8.7,  size: "lg" },
  { name: "São Paulo",     lon: -46.63,  lat: -23.55, volume: "$780M", changePct: -2.1, size: "sm" },
  { name: "London",        lon: -0.13,   lat: 51.51, volume: "$2.1B", changePct: 6.3,  size: "md" },
  { name: "Frankfurt",     lon: 8.68,    lat: 50.11, volume: "$1.6B", changePct: 4.6,  size: "sm" },
  { name: "Johannesburg",  lon: 28.05,   lat: -26.20, volume: "$420M", changePct: -1.3, size: "sm" },
  { name: "Mumbai",        lon: 72.88,   lat: 19.08, volume: "$950M", changePct: 3.8,  size: "sm" },
  { name: "Singapore",     lon: 103.82,  lat: 1.35, volume: "$2.9B", changePct: 9.2,  size: "md" },
  { name: "Tokyo",         lon: 139.65,  lat: 35.68, volume: "$1.4B", changePct: 5.1,  size: "md" },
  { name: "Sydney",        lon: 151.21,  lat: -33.87, volume: "$980M", changePct: 3.0,  size: "sm" },
];

/* ── Arc connections ── */
interface Arc {
  from: number;
  to: number;
  color: string;
  flowType: "high" | "medium" | "low" | "decreasing";
}

const ARCS: Arc[] = [
  { from: 1, to: 3, color: "#00ff88", flowType: "high" },
  { from: 3, to: 4, color: "#00ff88", flowType: "high" },
  { from: 3, to: 8, color: "#fbbf24", flowType: "medium" },
  { from: 1, to: 7, color: "#fbbf24", flowType: "medium" },
  { from: 0, to: 1, color: "#00ff88", flowType: "high" },
  { from: 1, to: 2, color: "#f97316", flowType: "low" },
  { from: 4, to: 5, color: "#f87171", flowType: "decreasing" },
  { from: 7, to: 9, color: "#fbbf24", flowType: "medium" },
  { from: 7, to: 6, color: "#00ff88", flowType: "high" },
];

const FLOW_LEGEND = [
  { label: "High Volume", color: "#00ff88" },
  { label: "Medium Volume", color: "#fbbf24" },
  { label: "Low Volume", color: "#f97316" },
  { label: "Decreasing", color: "#f87171" },
];

/* ── Pre-compute city positions ── */
const CITY_POSITIONS = CITIES.map((c) => mercatorProject(c.lon, c.lat));

/**
 * World-level viewBox tightened to fill the wide panel.
 * Shows ~72°N to ~50°S — all continents + all cities visible.
 * Mercator y at 72°N ≈ -35, at 50°S ≈ 440.
 * Tighter vertical range = map fills more of the container.
 */
const VIEWBOX = "0 -35 1000 480";

/* ── Main Component ── */
interface GlobalTransactionMonitorProps {
  onSelectSymbol: (symbol: string) => void;
}

export default function GlobalTransactionMonitor({ onSelectSymbol: _onSelectSymbol }: GlobalTransactionMonitorProps) {
  return (
    <div className="flex flex-col h-full min-h-0">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-t-border/50">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
            GLOBAL TRANSACTION MONITOR
          </span>
          <span className="flex items-center gap-1 text-[8px] font-mono text-t-green">
            <span className="w-[4px] h-[4px] rounded-full bg-t-green live-pulse" />
            LIVE
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
      <div className="flex-1 min-h-0 relative overflow-hidden bg-[#070a0e]">
        <svg
          viewBox={VIEWBOX}
          className="w-full h-full"
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <filter id="nodeGlow">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <filter id="arcGlow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
            <pattern id="mapGrid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.012)" strokeWidth="0.5" />
            </pattern>
          </defs>

          {/* Background grid */}
          <rect x="0" y="-35" width="1000" height="480" fill="url(#mapGrid)" />

          {/* Real geographic land masses */}
          {WORLD_MAP_PATHS.map((d, i) => (
            <path
              key={i}
              d={d}
              fill="rgba(255,255,255,0.045)"
              stroke="rgba(255,255,255,0.09)"
              strokeWidth="0.4"
              strokeLinejoin="round"
            />
          ))}

          {/* Transaction arcs */}
          {ARCS.map((arc, i) => {
            const [fromX, fromY] = CITY_POSITIONS[arc.from];
            const [toX, toY] = CITY_POSITIONS[arc.to];
            const midX = (fromX + toX) / 2;
            const midY = Math.min(fromY, toY) - 25 - Math.abs(fromX - toX) * 0.07;
            return (
              <g key={`arc-${i}`}>
                <path
                  d={`M ${fromX} ${fromY} Q ${midX} ${midY} ${toX} ${toY}`}
                  fill="none" stroke={arc.color} strokeWidth="1.2" strokeOpacity="0.15" filter="url(#arcGlow)"
                />
                <path
                  d={`M ${fromX} ${fromY} Q ${midX} ${midY} ${toX} ${toY}`}
                  fill="none" stroke={arc.color} strokeWidth="1.8" strokeOpacity="0.6"
                  strokeDasharray="6 8" className="arc-animated"
                  style={{ animationDelay: `${i * 0.3}s` }}
                />
              </g>
            );
          })}

          {/* City nodes — geographically positioned */}
          {CITIES.map((city, i) => {
            const [cx, cy] = CITY_POSITIONS[i];
            const r = city.size === "lg" ? 6 : city.size === "md" ? 5 : 4;
            const isUp = city.changePct >= 0;
            const color = isUp ? "#00ff88" : "#f87171";
            return (
              <g key={`city-${i}`}>
                {/* Outer pulse */}
                <circle cx={cx} cy={cy} r={r * 2.8} fill={color} opacity="0.08" className="node-pulse" style={{ animationDelay: `${i * 0.5}s` }} />
                {/* Node */}
                <circle cx={cx} cy={cy} r={r} fill={color} opacity="0.9" filter="url(#nodeGlow)" />
                <circle cx={cx} cy={cy} r={r * 0.35} fill="#fff" opacity="0.85" />
                {/* City name */}
                <text x={cx} y={cy - r - 9} textAnchor="middle" style={{ fontSize: "7px", fontFamily: "monospace", fill: "rgba(255,255,255,0.55)" }}>
                  {city.name.toUpperCase()}
                </text>
                {/* Volume */}
                <text x={cx} y={cy - r - 2.5} textAnchor="middle" style={{ fontSize: "9px", fontFamily: "monospace", fontWeight: "bold", fill: "rgba(255,255,255,0.85)" }}>
                  {city.volume}
                </text>
                {/* Change % */}
                <text x={cx + 20} y={cy + 3} textAnchor="start" style={{ fontSize: "7px", fontFamily: "monospace", fontWeight: "bold", fill: color }}>
                  {isUp ? "▲" : "▼"}{Math.abs(city.changePct).toFixed(1)}%
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend overlay — bottom left */}
        <div className="absolute bottom-2 left-2 bg-[#0a0a0a]/85 border border-t-border/30 rounded px-2 py-1.5">
          <div className="text-[7px] font-mono text-t-muted uppercase tracking-wider mb-1">TRANSACTION FLOW</div>
          {FLOW_LEGEND.map((item) => (
            <div key={item.label} className="flex items-center gap-2 mb-0.5">
              <div className="w-[12px] h-[2px] rounded-full" style={{ backgroundColor: item.color }} />
              <span className="text-[7px] font-mono text-t-muted">{item.label}</span>
            </div>
          ))}
        </div>

        {/* Stats overlay — bottom right */}
        <div className="absolute bottom-2 right-2 bg-[#0a0a0a]/85 border border-t-border/30 rounded px-2.5 py-1.5">
          <div className="text-[7px] font-mono text-t-muted uppercase tracking-wider mb-1">GLOBAL STATS (24H)</div>
          <div className="flex gap-4">
            <div>
              <div className="text-[7px] font-mono text-t-muted">TOTAL VOLUME</div>
              <div className="text-[11px] font-mono font-bold text-t-primary tabular-nums">$28.4B</div>
              <div className="text-[7px] font-mono text-t-green">▲8.2%</div>
            </div>
            <div>
              <div className="text-[7px] font-mono text-t-muted">TRANSACTIONS</div>
              <div className="text-[11px] font-mono font-bold text-t-primary tabular-nums">128,842</div>
              <div className="text-[7px] font-mono text-t-green">▲6.1%</div>
            </div>
            <div>
              <div className="text-[7px] font-mono text-t-muted">ACTIVE NODES</div>
              <div className="text-[11px] font-mono font-bold text-t-primary tabular-nums">23</div>
              <div className="text-[7px] font-mono text-t-green">▲2</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
