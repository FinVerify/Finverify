"use client";

import React, { useState, useEffect } from "react";
import { AreaChart, Area, ResponsiveContainer } from "recharts";
import { getMarketIndices, type MarketQuote } from "@/lib/api";

/**
 * MarketPulsePanel — Rebuilt per visual parity spec §3.
 * Shows timeframe tabs + sparkline area chart + SPX/NDX/VIX stat row.
 */

const TIMEFRAMES = ["1D", "1W", "1M", "YTD", "1Y"];

const FALLBACK_INDICES: { symbol: string; name: string; price: number; change_pct: number }[] = [
  { symbol: "SPX", name: "SPX", price: 5287.14, change_pct: 0.88 },
  { symbol: "NDX", name: "NDX", price: 18431.28, change_pct: 1.28 },
  { symbol: "VIX", name: "VIX", price: 14.32, change_pct: -0.42 },
];

function generateChartData(points: number = 60): { t: number; v: number }[] {
  const data: { t: number; v: number }[] = [];
  let val = 5200 + Math.random() * 50;
  for (let i = 0; i < points; i++) {
    val += (Math.random() - 0.45) * 15;
    data.push({ t: i, v: val });
  }
  return data;
}

export default function MarketPulsePanel() {
  const [activeTimeframe, setActiveTimeframe] = useState("1D");
  const [indices, setIndices] = useState(FALLBACK_INDICES);
  const [chartData] = useState(() => generateChartData());

  useEffect(() => {
    const fetchIndices = async () => {
      try {
        const data = await getMarketIndices();
        if (data.length > 0) {
          const mapped = data.slice(0, 3).map((d: MarketQuote) => ({
            symbol: d.display_name || d.symbol,
            name: d.display_name || d.symbol,
            price: d.price,
            change_pct: d.change_pct,
          }));
          if (mapped.length >= 3) setIndices(mapped);
        }
      } catch { /* keep fallback */ }
    };
    fetchIndices();
    const interval = setInterval(fetchIndices, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="panel flex flex-col h-full min-h-0">
      {/* Header with timeframe tabs */}
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-t-border/50">
        <div className="flex items-center gap-1.5">
          <span className="text-t-green text-[9px]">▶</span>
          <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
            MARKET PULSE
          </span>
        </div>
        <div className="flex items-center gap-0.5">
          {TIMEFRAMES.map((tf) => (
            <button
              key={tf}
              onClick={() => setActiveTimeframe(tf)}
              className={`text-[8px] font-mono font-bold px-1.5 py-0.5 rounded transition-colors ${
                activeTimeframe === tf
                  ? "bg-t-green/15 text-t-green"
                  : "text-t-muted hover:text-t-secondary"
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Sparkline chart */}
      <div className="h-[90px] px-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 0, left: 5 }}>
            <defs>
              <linearGradient id="marketPulseGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00ff88" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#00ff88" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <Area
              type="monotone"
              dataKey="v"
              stroke="#00ff88"
              strokeWidth={1.5}
              fill="url(#marketPulseGradient)"
              dot={false}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Index stat row */}
      <div className="grid grid-cols-3 gap-1 px-2 pb-2 pt-1">
        {indices.map((idx) => {
          const isUp = idx.change_pct >= 0;
          const color = isUp ? "text-t-green" : "text-t-red";
          return (
            <div key={idx.symbol} className="text-center">
              <div className="text-[8px] font-mono text-t-muted uppercase tracking-wider">
                {idx.name}
              </div>
              <div className="text-[12px] font-mono font-bold text-t-primary tabular-nums">
                {idx.price >= 1000
                  ? idx.price.toLocaleString(undefined, { maximumFractionDigits: 2 })
                  : idx.price.toFixed(2)}
              </div>
              <div className={`text-[9px] font-mono font-semibold tabular-nums ${color}`}>
                {isUp ? "▲" : "▼"} {isUp ? "+" : ""}{idx.change_pct.toFixed(2)}%
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
