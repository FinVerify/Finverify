"use client";

import React, { useEffect, useState, useCallback } from "react";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { type MarketQuote } from "@/lib/api";
import { getAllQuotes, isFinnhubConfigured, type FinnhubQuote } from "@/lib/market";

/**
 * WatchlistPanel — Left column, flex-1.
 * Near-total port of Watchlist.tsx, adapted for workspace density.
 * Click-to-select drives the Focus View.
 * Per §5.2 of UI_IMPLEMENTATION_PLAN.md.
 */

const DEFAULT_WATCHLIST = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN", "GOOG", "JPM", "GS"];

const FALLBACK_QUOTES: MarketQuote[] = [
  { symbol: "AAPL", price: 333.43, prev_close: 338.19, change: -4.76, change_pct: -1.4, volume: 58_000_000, market_cap: 2_980_000_000_000 },
  { symbol: "TSLA", price: 308.85, prev_close: 298.32, change: 10.53, change_pct: 3.5, volume: 112_000_000, market_cap: 556_000_000_000 },
  { symbol: "NVDA", price: 905.25, prev_close: 885.84, change: 19.41, change_pct: 2.2, volume: 42_000_000, market_cap: 2_160_000_000_000 },
  { symbol: "MSFT", price: 418.68, prev_close: 414.06, change: 4.62, change_pct: 1.1, volume: 22_000_000, market_cap: 3_140_000_000_000 },
  { symbol: "AMZN", price: 223.12, prev_close: 218.74, change: 4.38, change_pct: 2.0, volume: 35_000_000, market_cap: 2_310_000_000_000 },
  { symbol: "GOOG", price: 155.32, prev_close: 156.50, change: -1.18, change_pct: -0.7, volume: 28_000_000, market_cap: 1_940_000_000_000 },
  { symbol: "JPM", price: 198.45, prev_close: 197.50, change: 0.95, change_pct: 0.48, volume: 9_200_000, market_cap: 572_000_000_000 },
  { symbol: "GS", price: 467.20, prev_close: 465.80, change: 1.40, change_pct: 0.30, volume: 2_100_000, market_cap: 155_000_000_000 },
];

function generateSparkline(currentPrice: number, changePct: number): { v: number }[] {
  const points: { v: number }[] = [];
  let price = currentPrice / (1 + changePct / 100);
  for (let i = 0; i < 20; i++) {
    price += (Math.random() - 0.48) * (currentPrice * 0.002);
    points.push({ v: price });
  }
  points.push({ v: currentPrice });
  return points;
}

function toMarketQuote(fq: FinnhubQuote): MarketQuote {
  return {
    symbol: fq.symbol,
    price: fq.price,
    prev_close: fq.prevClose,
    change: fq.change,
    change_pct: fq.changePct,
    volume: 0,
    market_cap: 0,
  };
}

interface WatchlistPanelProps {
  selectedSymbol: string | null;
  onSelectSymbol: (symbol: string) => void;
  sectorFilter?: string | null;
}

export default function WatchlistPanel({ selectedSymbol, onSelectSymbol }: WatchlistPanelProps) {
  const [quotes, setQuotes] = useState<MarketQuote[]>(FALLBACK_QUOTES);
  const [isLive, setIsLive] = useState(false);

  const fetchQuotes = useCallback(async () => {
    if (!isFinnhubConfigured()) return;
    try {
      const data = await getAllQuotes(DEFAULT_WATCHLIST);
      if (data.length > 0) {
        setQuotes(data.map(toMarketQuote));
        setIsLive(true);
      }
    } catch {
      // Keep existing data
    }
  }, []);

  useEffect(() => {
    fetchQuotes();
    const interval = setInterval(fetchQuotes, 30000);
    return () => clearInterval(interval);
  }, [fetchQuotes]);

  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="panel-header">
        <div className="flex items-center gap-1.5">
          <span className="text-t-green text-[9px]">◆</span>
          <span className="label text-t-green">
            WATCHLIST — {isLive ? (
              <span className="text-t-green">LIVE</span>
            ) : (
              <span className="text-t-muted">DEMO</span>
            )}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[8px] text-t-muted font-mono">{quotes.length} SYMBOLS</span>
          <span className="text-[8px] text-t-muted hover:text-t-secondary cursor-pointer font-mono transition-colors">EDIT</span>
        </div>
      </div>

      {/* Column labels */}
      <div className="grid grid-cols-[50px_1fr_60px_60px_44px] gap-1 px-2 py-1 text-[8px] font-mono text-t-muted uppercase tracking-wider border-b border-t-border/50">
        <span>SYM</span>
        <span className="text-right">PRICE</span>
        <span className="text-right">CHG</span>
        <span className="text-right">%CHG</span>
        <span className="text-center">TREND</span>
      </div>

      {/* Rows */}
      <div className="flex-1 overflow-y-auto">
        {quotes.map((q) => {
          const isUp = q.change_pct >= 0;
          const color = isUp ? "text-t-green" : "text-t-red";
          const sparkData = generateSparkline(q.price, q.change_pct);
          const isSelected = q.symbol === selectedSymbol;

          return (
            <button
              key={q.symbol}
              onClick={() => onSelectSymbol(q.symbol)}
              className={`
                w-full grid grid-cols-[50px_1fr_60px_60px_44px] gap-1 items-center px-2 py-1.5
                text-[10px] font-mono transition-all duration-150 border-l-2
                ${isSelected
                  ? "bg-white/[0.04] border-t-green"
                  : "border-transparent hover:bg-white/[0.02]"
                }
              `}
            >
              <span className={`font-bold ${isSelected ? "text-t-green" : "text-t-primary"}`}>
                {q.symbol}
              </span>
              <span className="text-right text-t-primary tabular-nums">
                ${q.price >= 1000 ? q.price.toLocaleString(undefined, { maximumFractionDigits: 2 }) : q.price.toFixed(2)}
              </span>
              <span className={`text-right tabular-nums ${color}`}>
                {isUp ? "+" : "-"}${Math.abs(q.change).toFixed(2)}
              </span>
              <span className={`text-right tabular-nums font-semibold ${color}`}>
                {isUp ? "▲" : "▼"} {Math.abs(q.change_pct).toFixed(1)}%
              </span>
              <div className="h-[22px] w-[40px] mx-auto">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={sparkData}>
                    <Line
                      type="monotone"
                      dataKey="v"
                      stroke={isUp ? "#00ff88" : "#f87171"}
                      strokeWidth={1}
                      dot={false}
                      isAnimationActive={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-2 py-1 border-t border-t-border/50 flex justify-between text-[8px] font-mono text-t-muted">
        <span>Click symbol for analysis</span>
        {!isLive && <span className="text-t-amber">DEMO MODE</span>}
      </div>
    </div>
  );
}
