"use client";

import React, { useEffect, useState } from "react";
import { getMarketIndices, type MarketQuote } from "@/lib/api";

/**
 * MarketPulsePanel — Left column, top, 220px fixed.
 * Shows market indices with fallback data for instant render.
 * Ported from MarketContext.tsx's index-card rendering block.
 * Per §5.1 of UI_IMPLEMENTATION_PLAN.md.
 */

const FALLBACK_INDICES: MarketQuote[] = [
  { symbol: "SPY", display_name: "S&P 500", price: 5287.14, prev_close: 5245.0, change: 42.14, change_pct: 0.80, volume: 0, market_cap: 0 },
  { symbol: "QQQ", display_name: "NASDAQ", price: 18431.28, prev_close: 18212.8, change: 218.48, change_pct: 1.20, volume: 0, market_cap: 0 },
  { symbol: "^VIX", display_name: "VIX", price: 14.32, prev_close: 14.38, change: -0.06, change_pct: -0.42, volume: 0, market_cap: 0 },
  { symbol: "TNX", display_name: "10Y Yield", price: 4.25, prev_close: 4.22, change: 0.03, change_pct: 0.71, volume: 0, market_cap: 0 },
  { symbol: "BTC", display_name: "BTC", price: 63241.0, prev_close: 62800.0, change: 441.0, change_pct: 0.70, volume: 0, market_cap: 0 },
];

export default function MarketPulsePanel() {
  const [indices, setIndices] = useState<MarketQuote[]>(FALLBACK_INDICES);

  useEffect(() => {
    const fetchIndices = async () => {
      try {
        const data = await getMarketIndices();
        if (data.length > 0) setIndices(data);
      } catch {
        // Keep fallback data — no loading state needed
      }
    };
    fetchIndices();
    const interval = setInterval(fetchIndices, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="panel-header">
        <span className="label text-t-cyan">MARKET PULSE</span>
        <span className="text-[9px] text-t-muted font-mono">INDICES</span>
      </div>
      <div className="flex-1 overflow-y-auto p-1.5 space-y-1">
        {indices.map((idx) => {
          const isUp = idx.change_pct >= 0;
          const color = isUp ? "text-t-green" : "text-t-red";
          const name = idx.display_name || idx.symbol;

          return (
            <div key={idx.symbol} className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-white/[0.02] transition-colors">
              <div className="flex flex-col">
                <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
                  {name}
                </span>
                <span className="text-[12px] font-mono font-bold text-t-primary tabular-nums">
                  {idx.price >= 1000
                    ? idx.price.toLocaleString(undefined, { maximumFractionDigits: 2 })
                    : idx.price.toFixed(2)}
                </span>
              </div>
              <div className="flex flex-col items-end">
                <span className={`text-[9px] font-mono font-bold ${color}`}>
                  {isUp ? "▲" : "▼"} {isUp ? "+" : ""}{idx.change_pct.toFixed(2)}%
                </span>
                <span className={`text-[9px] font-mono tabular-nums ${color}`}>
                  {isUp ? "+" : ""}{idx.change.toFixed(2)}
                </span>
              </div>
              {idx.stale && (
                <span className="text-[8px] text-t-amber font-mono ml-1">STALE</span>
              )}
            </div>
          );
        })}

        {/* Verifications pending — placeholder per §5.1 */}
        <div className="flex items-center justify-between px-2 py-1.5 border-t border-t-border/50 mt-1">
          <span className="text-[9px] font-mono text-t-muted uppercase tracking-wider">
            Verifications Pending
          </span>
          <span className="text-[9px] font-mono text-t-muted">—</span>
        </div>
      </div>
    </div>
  );
}
