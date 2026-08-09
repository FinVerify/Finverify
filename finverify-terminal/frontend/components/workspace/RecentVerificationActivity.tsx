"use client";

import React from "react";
import type { QueryResponse } from "@/lib/api";

/**
 * RecentVerificationActivity — Shows recently verified/corrected/conflicting claims.
 * Per target screenshot — compact list with severity badges and timestamps.
 */

interface ActivityItem {
  symbol: string;
  description: string;
  time: string;
  severity: "HIGH" | "MEDIUM" | "LOW";
  type: "verified" | "corrected" | "conflict";
}

const DEMO_ACTIVITY: ActivityItem[] = [
  { symbol: "NVDA", description: "NVDA Revenue (Q2 FY24)", time: "15m ago", severity: "LOW", type: "verified" },
  { symbol: "AAPL", description: "AAPL Diluted EPS (Q3 FY24)", time: "22m ago", severity: "LOW", type: "verified" },
  { symbol: "JPM", description: "JPM Net Income (Q2 FY24)", time: "28m ago", severity: "MEDIUM", type: "corrected" },
  { symbol: "TSLA", description: "TSLA Operating Margin (Q2 FY24)", time: "35m ago", severity: "HIGH", type: "conflict" },
  { symbol: "MSFT", description: "MSFT Azure Revenue (Q4 FY24)", time: "41m ago", severity: "LOW", type: "verified" },
];

function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === "HIGH"
      ? "bg-t-red/10 text-t-red border-t-red/20"
      : severity === "MEDIUM"
      ? "bg-t-amber/10 text-t-amber border-t-amber/20"
      : "bg-t-green/10 text-t-green border-t-green/20";
  return (
    <span className={`text-[7px] font-mono font-bold px-1 py-0.5 rounded border ${cls}`}>
      {severity}
    </span>
  );
}

const KNOWN_SYMBOLS = ["AAPL", "TSLA", "JPM", "NVDA", "MSFT", "GS", "COIN", "INTC", "AMZN", "META"];

function responseToActivity(result: QueryResponse): ActivityItem {
  const symbol = KNOWN_SYMBOLS.find((ticker) => result.question.toUpperCase().includes(ticker)) || "DVL";
  const corrected = result.correction_log.length > 0;
  const severity = result.trust_score === "LOW" ? "HIGH" : result.trust_score === "MEDIUM" || corrected ? "MEDIUM" : "LOW";
  return { symbol, description: result.question, time: "JUST NOW", severity, type: corrected ? "corrected" : "verified" };
}

interface RecentVerificationActivityProps {
  verificationHistory: QueryResponse[];
  onSelectSymbol?: (symbol: string) => void;
}

export default function RecentVerificationActivity({ verificationHistory, onSelectSymbol }: RecentVerificationActivityProps) {
  const activity = verificationHistory.length ? verificationHistory.map(responseToActivity) : DEMO_ACTIVITY;
  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-t-border/50">
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
            RECENT VERIFICATION ACTIVITY
          </span>
          <span className="flex items-center gap-1 text-[8px] font-mono text-t-green">
            <span className="w-[3px] h-[3px] rounded-full bg-t-green live-pulse" />
            LIVE
          </span>
        </div>
        <span className="text-[7px] font-mono text-t-muted">LAST 24H</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {activity.map((item, i) => (
          <button
            key={i}
            onClick={() => item.symbol !== "DVL" && onSelectSymbol?.(item.symbol)}
            disabled={item.symbol === "DVL" || !onSelectSymbol}
            className="flex items-center gap-2 px-2 py-1.5 border-b border-t-border/20 last:border-b-0 hover:bg-white/[0.02] transition-colors text-[9px] font-mono"
          >
            <span className={`font-bold w-[36px] shrink-0 ${
              item.type === "conflict" ? "text-t-red" : 
              item.type === "corrected" ? "text-t-amber" : "text-t-green"
            }`}>
              {item.type === "conflict" ? "⚠" : item.type === "corrected" ? "◆" : "✓"} 
            </span>
            <div className="flex-1 min-w-0">
              <div className={`truncate ${
                item.type === "conflict" ? "text-t-red" : 
                item.type === "corrected" ? "text-t-amber" : "text-t-secondary"
              }`}>
                {item.description}
              </div>
            </div>
            <span className="text-t-muted/60 shrink-0 tabular-nums text-[8px]">{item.time}</span>
            <SeverityBadge severity={item.severity} />
          </button>
        ))}
      </div>
      <div className="px-2 py-1 border-t border-t-border/50 text-center">
        <span className="text-[8px] font-mono text-t-muted hover:text-t-secondary cursor-pointer transition-colors">
          VIEW ALL ACTIVITY →
        </span>
      </div>
    </div>
  );
}
