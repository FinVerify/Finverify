"use client";

import React, { useEffect, useState, useCallback } from "react";
import { type MarketQuote } from "@/lib/api";
import { getAllQuotes, isFinnhubConfigured, type FinnhubQuote } from "@/lib/market";

/**
 * WatchlistPanel — Left column, flex-1.
 * Enhanced per target screenshot: adds VERIF. STATUS column,
 * + ADD SYMBOL link, VIEW ALL link.
 */

const DEFAULT_WATCHLIST = ["AAPL", "TSLA", "NVDA", "MSFT", "JPM", "GS", "AMZN", "META"];

const FALLBACK_QUOTES: MarketQuote[] = [
  { symbol: "AAPL", price: 192.34, prev_close: 190.13, change: 2.21, change_pct: 1.16, volume: 58_000_000, market_cap: 2_980_000_000_000 },
  { symbol: "TSLA", price: 174.82, prev_close: 176.22, change: -1.40, change_pct: -0.79, volume: 112_000_000, market_cap: 556_000_000_000 },
  { symbol: "NVDA", price: 877.35, prev_close: 857.60, change: 19.75, change_pct: 2.30, volume: 42_000_000, market_cap: 2_160_000_000_000 },
  { symbol: "MSFT", price: 422.86, prev_close: 420.72, change: 2.14, change_pct: 0.51, volume: 22_000_000, market_cap: 3_140_000_000_000 },
  { symbol: "JPM", price: 198.45, prev_close: 197.50, change: 0.95, change_pct: 0.48, volume: 9_200_000, market_cap: 572_000_000_000 },
  { symbol: "GS", price: 467.20, prev_close: 465.80, change: 1.40, change_pct: 0.30, volume: 2_100_000, market_cap: 155_000_000_000 },
  { symbol: "AMZN", price: 223.12, prev_close: 218.74, change: 4.38, change_pct: 2.0, volume: 35_000_000, market_cap: 2_310_000_000_000 },
  { symbol: "META", price: 518.52, prev_close: 513.14, change: 5.38, change_pct: 1.05, volume: 18_500_000, market_cap: 1_320_000_000_000 },
];

// Demo verification statuses
const VERIF_STATUS: Record<string, { label: string; color: string }> = {
  AAPL: { label: "✓", color: "text-t-green" },
  TSLA: { label: "⚠", color: "text-t-amber" },
  NVDA: { label: "✓", color: "text-t-green" },
  MSFT: { label: "✓", color: "text-t-green" },
  JPM: { label: "✓", color: "text-t-green" },
  GS: { label: "✓", color: "text-t-green" },
  AMZN: { label: "✓", color: "text-t-green" },
  META: { label: "◆", color: "text-t-amber" },
};

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
  const [watchlist, setWatchlist] = useState(DEFAULT_WATCHLIST);
  const [isEditing, setIsEditing] = useState(false);
  const [newSymbol, setNewSymbol] = useState("");
  const [quotes, setQuotes] = useState<MarketQuote[]>(FALLBACK_QUOTES);
  const [isLive, setIsLive] = useState(false);

  const fetchQuotes = useCallback(async () => {
    if (!isFinnhubConfigured()) return;
    try {
      const data = await getAllQuotes(watchlist);
      if (data.length > 0) {
        setQuotes(data.map(toMarketQuote));
        setIsLive(true);
      }
    } catch {
      // Keep existing data
    }
  }, [watchlist]);

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
          <span className="label text-t-green">WATCHLIST</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[8px] text-t-muted font-mono">{quotes.length} SYMBOLS</span>
          <button onClick={() => setIsEditing((value) => !value)} className="text-[8px] text-t-muted hover:text-t-secondary font-mono transition-colors">{isEditing ? "DONE" : "EDIT"}</button>
        </div>
      </div>

      {/* Column labels */}
      <div className="grid grid-cols-[42px_1fr_55px_55px_36px] gap-0.5 px-2 py-1 text-[7px] font-mono text-t-muted uppercase tracking-wider border-b border-t-border/50">
        <span>SYMBOL</span>
        <span className="text-right">PRICE</span>
        <span className="text-right">CHANGE</span>
        <span className="text-right">%</span>
        <span className="text-center">VERIF.</span>
      </div>

      {/* Rows */}
      <div className="flex-1 overflow-y-auto">
        {quotes.filter((q) => watchlist.includes(q.symbol)).map((q) => {
          const isUp = q.change_pct >= 0;
          const color = isUp ? "text-t-green" : "text-t-red";
          const isSelected = q.symbol === selectedSymbol;
          const verif = VERIF_STATUS[q.symbol] || { label: "—", color: "text-t-muted" };

          return (
            <button
              key={q.symbol}
              onClick={() => onSelectSymbol(q.symbol)}
              className={`
                w-full grid grid-cols-[42px_1fr_55px_55px_36px] gap-0.5 items-center px-2 py-1.5
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
                {isUp ? "+" : ""}{q.change.toFixed(2)}
              </span>
              <span className={`text-right tabular-nums font-semibold ${color}`}>
                {isUp ? "+" : ""}{q.change_pct.toFixed(1)}%
              </span>
              <span className={`text-center ${verif.color}`}>
                {verif.label}
              </span>
              {isEditing && (
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(event) => { event.stopPropagation(); setWatchlist((symbols) => symbols.filter((symbol) => symbol !== q.symbol)); }}
                  className="text-t-red ml-1"
                >×</span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <div className="px-2 py-1 border-t border-t-border/50 flex justify-between text-[8px] font-mono text-t-muted">
        <form onSubmit={(event) => {
          event.preventDefault();
          const symbol = newSymbol.trim().toUpperCase();
          if (symbol && !watchlist.includes(symbol)) {
            setWatchlist((symbols) => [...symbols, symbol]);
            setQuotes((current) => current.some((quote) => quote.symbol === symbol)
              ? current
              : [...current, { symbol, price: 0, prev_close: 0, change: 0, change_pct: 0, volume: 0, market_cap: 0 }]);
          }
          setNewSymbol("");
        }} className="flex items-center gap-1">
          {isEditing && <input value={newSymbol} onChange={(event) => setNewSymbol(event.target.value)} placeholder="TICKER" className="w-[48px] bg-transparent border-b border-t-border text-[8px] font-mono text-t-primary outline-none" />}
          <button type="submit" className="hover:text-t-secondary transition-colors">+ ADD SYMBOL</button>
        </form>
        <span className="hover:text-t-secondary cursor-pointer transition-colors">VIEW ALL →</span>
      </div>
    </div>
  );
}
