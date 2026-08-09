"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { verifyNumber, queryLLM, type QueryResponse } from "@/lib/api";

/**
 * CommandBar — Persistent command/action bar for the workspace center column.
 * Quick action chips + command input.
 * Per target screenshot — sits below the center content with action buttons.
 */

const KNOWN_TICKERS = ["AAPL", "TSLA", "JPM", "NVDA", "MSFT", "GS", "COIN", "INTC", "AMZN", "GOOG"];
const DEMO_NUMS: Record<string, number> = {
  "YoY operating margin change?": 0.1240, "CET1 ratio Q4 2022?": 10.935,
  "Net income increase YoY?": 1250000, "Revenue growth rate?": 8.14,
};

const QUICK_ACTIONS = [
  { icon: "📄", label: "Analyze Apple 10-Q Filing", query: "Analyze Apple 10-Q filing" },
  { icon: "🛡", label: "Verify a Claim", query: "Verify TSLA revenue claim" },
  { icon: "📊", label: "Analyze Filing", query: "Analyze latest 10-K filing" },
  { icon: "✦", label: "Check Earnings", query: "Check NVDA earnings" },
  { icon: "📁", label: "Upload Document", query: "" },
];

interface CommandBarProps {
  onSelectSymbol: (symbol: string, tab?: "evidence" | "verification") => void;
  onVerification: (result: QueryResponse) => void;
}

export default function CommandBar({ onSelectSymbol, onVerification }: CommandBarProps) {
  const [queryValue, setQueryValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
    setError(null);
    setResult(null);
    try {
      const knownDemo = DEMO_NUMS[q];
      let response: QueryResponse | null = null;
      if (knownDemo !== undefined) {
        response = await verifyNumber(q, knownDemo);
      } else {
        response = await queryLLM(q);
      }
      if (response) {
        setResult(response);
        onVerification(response);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Verification failed — try again");
    }
    finally { setIsLoading(false); setQueryValue(""); }
  }, [queryValue, isLoading, onSelectSymbol, onVerification]);

  return (
    <div className="border-t border-t-border/50 bg-[#0a0a0a]">
      <div className="flex items-center gap-2 px-3 py-2">
        {/* Quick action chips */}
        <div className="flex items-center gap-1.5 overflow-x-auto flex-1">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              onClick={() => {
                if (action.label === "Analyze Apple 10-Q Filing") {
                  onSelectSymbol("AAPL", "evidence");
                } else if (action.label === "Check Earnings") {
                  onSelectSymbol("NVDA", "verification");
                } else if (action.label === "Upload Document") {
                  setError("Document upload is not available yet");
                } else if (action.query) {
                  setQueryValue(action.query);
                  setError(null);
                  inputRef.current?.focus();
                }
              }}
              className="flex items-center gap-1 text-[8px] font-mono text-t-muted border border-t-border/30 rounded px-2 py-1 whitespace-nowrap hover:text-t-secondary hover:border-t-border/60 transition-colors shrink-0"
            >
              <span>{action.icon}</span>
              <span>{action.label}</span>
            </button>
          ))}
        </div>
      </div>
      
      {/* Command input */}
      <div className="flex items-center gap-2 px-3 pb-2">
        <div className="flex-1 flex items-center gap-2 bg-[#0d0d0d] border border-t-border/50 rounded px-3 py-1.5 command-input-glow">
          <span className="text-t-muted text-[10px]">🔍</span>
          <input
            ref={inputRef}
            type="text"
            value={queryValue}
            onChange={(e) => setQueryValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); handleSubmit(); } }}
            placeholder={isLoading ? "Processing..." : "Ask anything or select an action..."}
            disabled={isLoading}
            className="flex-1 bg-transparent text-[11px] font-mono text-t-green outline-none placeholder:text-t-muted/40 border-none disabled:opacity-50"
          />
          {isLoading && <span className="w-[5px] h-[5px] rounded-full bg-t-amber animate-pulse shrink-0" />}
          <button
            onClick={handleSubmit}
            disabled={isLoading || !queryValue.trim()}
            className="text-[8px] font-mono text-t-muted bg-white/[0.03] border border-t-border px-2 py-0.5 rounded hover:text-t-secondary transition-colors disabled:opacity-30 shrink-0"
          >
            SUBMIT
          </button>
          <button
            onClick={handleSubmit}
            disabled={isLoading || !queryValue.trim()}
            className="w-[24px] h-[24px] rounded bg-t-green/20 border border-t-green/30 flex items-center justify-center text-t-green hover:bg-t-green/30 transition-colors disabled:opacity-30 shrink-0"
          >
            <span className="text-[10px]">→</span>
          </button>
        </div>
      </div>
      {(error || result) && (
        <div className={`px-3 pb-2 text-[9px] font-mono ${error ? "text-t-red" : "text-t-green"}`}>
          {error ? `× ${error}` : `✓ ${result?.verified ? "VERIFIED" : "PROCESSED"} — ${result?.display_value || "Result received"}`}
        </div>
      )}
    </div>
  );
}
