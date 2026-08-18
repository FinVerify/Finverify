"use client";
import React, { useState, useRef, useEffect } from "react";
import { useConnection } from "@/lib/connection";

const SAMPLES = [
  "Tesla's operating margin in Q4 2022 was 16.9%.",
  "GETI ratio Q4 2022?",
  "Net income increase YoY?",
  "Revenue growth rate?",
  "HTM securities decrease?",
  "Class A shares outstanding change?",
];

type InputTab = "claim" | "ai_output" | "document";

interface Props {
  onSubmit: (q: string) => void;
  isLoading: boolean;
  latencyMs: number | null;
}

export default function QueryInput({ onSubmit, isLoading, latencyMs }: Props) {
  const [value, setValue] = useState("");
  const [uptimeSeconds, setUptimeSeconds] = useState(0);
  const [inputTab, setInputTab] = useState<InputTab>("claim");
  const ref = useRef<HTMLTextAreaElement>(null);
  const { backendOnline, modelName } = useConnection();

  useEffect(() => { ref.current?.focus(); }, []);

  useEffect(() => {
    const started = Date.now();
    const update = () => setUptimeSeconds(Math.floor((Date.now() - started) / 1000));
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  // Global keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setValue("");
        ref.current?.focus();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const submit = () => {
    if (!value.trim() || isLoading) return;
    onSubmit(value.trim());
  };

  const isMac = typeof navigator !== "undefined" && /Mac/.test(navigator.userAgent);
  const charCount = value.length;
  const maxChars = 500;

  return (
    <div className="panel flex flex-col h-full">
      {/* Header */}
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <span className="text-t-green text-[10px] font-bold">①</span>
          <span className="label">INPUT</span>
        </div>
        <span className={`status-dot ${isLoading ? "amber" : ""}`} />
      </div>

      <div className="flex-1 flex flex-col p-2.5 gap-2 overflow-y-auto">
        {/* Input Tabs */}
        <div className="flex border-b border-t-border">
          {(
            [
              { id: "claim" as InputTab, label: "CLAIM / QUESTION" },
              { id: "ai_output" as InputTab, label: "AI OUTPUT" },
              { id: "document" as InputTab, label: "DOCUMENT (PDF)" },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => tab.id === "claim" ? setInputTab(tab.id) : undefined}
              className={`px-3 py-1.5 text-[9px] font-mono font-bold uppercase tracking-wider transition-colors ${
                inputTab === tab.id
                  ? "text-t-green border-b border-t-green bg-white/[0.02]"
                  : tab.id !== "claim"
                    ? "text-t-muted/40 cursor-not-allowed"
                    : "text-t-muted hover:text-t-secondary cursor-pointer"
              }`}
              disabled={tab.id !== "claim"}
              title={tab.id !== "claim" ? "Not yet available" : undefined}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Textarea */}
        <div className="relative">
          <textarea
            ref={ref}
            id="query-input"
            value={value}
            onChange={(e) => setValue(e.target.value.slice(0, maxChars))}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); submit(); }
              if (e.key === "Enter" && !e.shiftKey && !e.metaKey && !e.ctrlKey) { e.preventDefault(); submit(); }
            }}
            placeholder="Enter financial question..."
            disabled={isLoading}
            rows={4}
            className="w-full bg-transparent text-t-green text-[12px] font-mono resize-none outline-none placeholder:text-t-green/20 border border-t-border focus:border-t-green/30 transition-colors p-2 rounded"
          />
          <span className="absolute bottom-2 right-2 text-[9px] text-t-muted/50 font-mono">
            {charCount} / {maxChars}
          </span>
        </div>

        {/* Suggested examples */}
        <div>
          <div className="text-[9px] text-t-muted font-mono uppercase tracking-wider mb-1.5">
            SUGGESTED EXAMPLES
          </div>
          <div className="flex flex-wrap gap-1">
            {SAMPLES.map((q, i) => (
              <button
                key={i}
                id={`sample-${i}`}
                disabled={isLoading}
                onClick={() => { setValue(q); ref.current?.focus(); }}
                className="text-[9px] font-mono px-2 py-0.5 rounded border border-t-border text-t-secondary hover:text-t-cyan hover:border-t-cyan/30 transition-all duration-200"
              >
                {q.length > 30 ? q.slice(0, 28) + "..." : q}
              </button>
            ))}
          </div>
        </div>

        {/* Query Settings — Domain / Tolerance / Rule Set */}
        <div className="space-y-1.5 mt-1">
          <div className="text-[9px] text-t-muted font-mono uppercase tracking-wider">QUERY SETTINGS</div>
          {/* Domain — disabled, placeholder */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-t-muted w-[80px]">DOMAIN</span>
            <div className="flex-1 px-2 py-1 bg-[#0d0d0d] border border-t-border/40 rounded text-[10px] font-mono text-t-muted/60 cursor-not-allowed">
              Equity / Public Company
            </div>
          </div>
          {/* Tolerance — fixed 5% */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-t-muted w-[80px]">TOLERANCE</span>
            <div className="flex-1 px-2 py-1 bg-[#0d0d0d] border border-t-border/40 rounded text-[10px] font-mono text-t-amber">
              5%
            </div>
          </div>
          {/* Rule Set — disabled */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-t-muted w-[80px]">RULE SET</span>
            <div className="flex-1 px-2 py-1 bg-[#0d0d0d] border border-t-border/40 rounded text-[10px] font-mono text-t-muted/60 cursor-not-allowed">
              Standard (v1)
            </div>
          </div>
        </div>

        {/* Verify Claim button */}
        <button
          id="execute-btn"
          onClick={submit}
          disabled={isLoading || !value.trim()}
          className="w-full py-2.5 text-[11px] font-mono font-bold uppercase tracking-[0.15em] rounded transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          style={{
            background: isLoading ? "rgba(0,255,136,0.06)" : "rgba(0,255,136,0.1)",
            color: "#00ff88",
            border: "1px solid rgba(0,255,136,0.25)",
            ...((!isLoading && value.trim()) ? { boxShadow: "0 0 12px rgba(0,255,136,0.15)" } : {}),
          }}
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              VERIFYING<span className="animate-pulse">...</span>
            </span>
          ) : (
            <>
              ▶ VERIFY CLAIM
              <span className="text-[9px] text-t-green/60 font-normal">
                {isMac ? "⌘" : "Ctrl"} + Enter
              </span>
            </>
          )}
        </button>

        {/* Engine Status */}
        <div className="bg-[#0d0d0d] border border-t-border/60 rounded px-3 py-2 mt-auto">
          <div className="text-[9px] text-t-muted font-mono uppercase tracking-wider mb-1.5">ENGINE STATUS</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[10px] font-mono">
            <div className="flex items-center gap-1.5">
              <span className={`w-[5px] h-[5px] rounded-full ${backendOnline ? "bg-t-green" : "bg-t-red"} inline-block`} />
              <span className="text-t-secondary">ENGINE:</span>
              <span className={backendOnline ? "text-t-green" : "text-t-red"}>{backendOnline ? "ONLINE" : "OFFLINE"}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-t-secondary">VERSION:</span>
              <span className="text-t-cyan">DVL 1.2.0</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-t-secondary">MODEL:</span>
              <span className="text-t-cyan">{modelName}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-t-secondary">UPTIME:</span>
              <span className="text-t-green">
                {Math.floor(uptimeSeconds / 3600).toString().padStart(2, "0")}:
                {Math.floor((uptimeSeconds % 3600) / 60).toString().padStart(2, "0")}:
                {(uptimeSeconds % 60).toString().padStart(2, "0")}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-t-secondary">PROVIDERS:</span>
              <span className="text-t-green">SEC EDGAR</span>
              <span className="text-t-muted">+</span>
              <span className="text-t-secondary">YFIN</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-t-secondary">LATENCY:</span>
              <span className="text-t-amber">
                {latencyMs !== null ? `${(latencyMs / 1000).toFixed(2)}s` : "—"}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-t-secondary">RULES:</span>
              <span className="text-t-primary">23</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-t-secondary">QUEUE:</span>
              <span className="text-t-primary">{isLoading ? "1" : "0"}</span>
            </div>
          </div>
        </div>

        {/* Tip */}
        <div className="text-[9px] font-mono text-t-muted/60 leading-relaxed">
          💡 Tip: Paste an AI output or upload a document to extract and verify multiple numerical claims at once.
        </div>
      </div>
    </div>
  );
}
