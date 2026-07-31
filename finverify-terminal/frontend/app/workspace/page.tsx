"use client";

import React, { useState } from "react";
import WorkspaceTopBar from "@/components/workspace/WorkspaceTopBar";
import MarketPulsePanel from "@/components/workspace/MarketPulsePanel";
import WatchlistPanel from "@/components/workspace/WatchlistPanel";
import IntegrityMonitorPanel from "@/components/workspace/IntegrityMonitorPanel";

/**
 * WorkspacePage — The Intelligence Workspace main page.
 * Owns top-level state: selectedSymbol, feedExpanded, activeSectorFilter.
 * Renders 3-column grid (280px / fluid / 300px) + bottom bar.
 * Per §3, §4, §12 of UI_IMPLEMENTATION_PLAN.md.
 */

type FocusTab =
  | "integrity"
  | "verification"
  | "financials"
  | "evidence"
  | "timeline"
  | "filings";

export default function WorkspacePage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [feedExpanded, setFeedExpanded] = useState(false);
  const [activeSectorFilter, setActiveSectorFilter] = useState<string | null>(
    null
  );
  const [activeTab, setActiveTab] = useState<FocusTab>("integrity");

  // Bottom bar height calculation
  const bottomBarHeight = feedExpanded ? 196 : 64;

  return (
    <>
      {/* Top Bar — 40px */}
      <WorkspaceTopBar />

      {/* Viewport < 1024px notice */}
      <div className="lg:hidden flex-1 flex items-center justify-center p-8">
        <div className="panel p-6 text-center max-w-md">
          <div className="text-[11px] font-mono text-t-amber font-bold uppercase tracking-wider mb-2">
            ⚠ VIEWPORT TOO NARROW
          </div>
          <div className="text-[10px] font-mono text-t-secondary leading-relaxed mb-3">
            The Intelligence Workspace requires a viewport of at least 1024px
            width for optimal information density.
          </div>
          <a
            href="/market"
            className="text-[10px] font-mono text-t-cyan hover:underline"
          >
            → Open Market Mode instead
          </a>
        </div>
      </div>

      {/* Main Grid — fills remaining viewport height */}
      <div
        className="hidden lg:grid grid-cols-[280px_1fr_300px] gap-[6px] p-[6px] min-h-0 flex-1"
        style={{ height: `calc(100vh - 40px - ${bottomBarHeight}px)` }}
      >
        {/* ── Left Column ── */}
        <div className="flex flex-col gap-[6px] min-h-0 overflow-hidden">
          <div className="h-[220px] min-h-[220px]">
            <MarketPulsePanel />
          </div>
          <div className="flex-1 min-h-[160px]">
            <WatchlistPanel
              selectedSymbol={selectedSymbol}
              onSelectSymbol={setSelectedSymbol}
            />
          </div>
          <div className="h-[200px] min-h-[200px]">
            <IntegrityMonitorPanel
              selectedSymbol={selectedSymbol}
              onSelectSymbol={setSelectedSymbol}
            />
          </div>
        </div>

        {/* ── Center Column ── */}
        <div className="flex flex-col min-h-0 overflow-hidden">
          {/* FocusView placeholder */}
          <div className="panel flex-1 min-h-0">
            <div className="panel-header">
              <span className="label text-t-green">FOCUS VIEW</span>
              <span className="text-[9px] text-t-muted font-mono">
                {selectedSymbol
                  ? selectedSymbol.toUpperCase()
                  : "MARKET OVERVIEW"}
              </span>
            </div>
            <div className="flex-1 flex items-center justify-center p-4">
              <span className="text-[10px] font-mono text-t-muted">
                {selectedSymbol
                  ? `Analyzing ${selectedSymbol}...`
                  : "Select a company from the Watchlist to begin analysis"}
              </span>
            </div>
          </div>
        </div>

        {/* ── Right Column ── */}
        <div className="flex flex-col gap-[6px] min-h-0 overflow-hidden">
          {/* NewsRadarPanel placeholder */}
          <div className="panel h-[180px] min-h-[180px]">
            <div className="panel-header">
              <span className="label text-t-blue">NEWS RADAR</span>
            </div>
          </div>

          {/* FilingRadarPanel placeholder */}
          <div className="panel h-[160px] min-h-[160px]">
            <div className="panel-header">
              <span className="label text-t-cyan">FILING RADAR</span>
            </div>
          </div>

          {/* EarningsRadarPanel placeholder */}
          <div className="panel h-[160px] min-h-[160px]">
            <div className="panel-header">
              <span className="label text-t-purple">EARNINGS RADAR</span>
            </div>
          </div>

          {/* SectorMonitorPanel placeholder */}
          <div className="panel flex-1 min-h-[120px]">
            <div className="panel-header">
              <span className="label text-t-amber">SECTOR MONITOR</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Bottom Bar ── */}
      <div
        className={`hidden lg:flex flex-col border-t border-t-border bg-t-bg sticky bottom-0 z-40`}
        style={{ height: `${bottomBarHeight}px`, minHeight: `${bottomBarHeight}px` }}
      >
        {/* Intelligence Feed */}
        <button
          onClick={() => setFeedExpanded(!feedExpanded)}
          className="h-[28px] min-h-[28px] flex items-center px-3 gap-2 text-[9px] font-mono text-t-secondary hover:bg-white/[0.02] transition-colors w-full text-left border-b border-t-border/50 overflow-hidden"
        >
          <span className="text-t-cyan">📡</span>
          <span className="text-t-muted">
            {feedExpanded ? "▼" : "▶"} Awaiting activity...
          </span>
        </button>

        {/* Expanded feed area */}
        {feedExpanded && (
          <div className="flex-1 min-h-0 overflow-y-auto px-3 py-1">
            <div className="text-[9px] font-mono text-t-muted text-center py-4">
              Intelligence Feed — events will appear here
            </div>
          </div>
        )}

        {/* Persistent Query Input */}
        <div className="h-[36px] min-h-[36px] flex items-center px-3 gap-2">
          <span className="text-t-cyan text-[11px]">🔍</span>
          <input
            type="text"
            placeholder="Type a question or ticker..."
            className="flex-1 bg-transparent text-[11px] font-mono text-t-green outline-none placeholder:text-t-muted/40 border-none"
          />
          <button className="text-[10px] font-mono text-t-muted hover:text-t-secondary transition-colors px-1">
            ⏎
          </button>
          <button className="text-[10px] font-mono text-t-muted hover:text-t-secondary transition-colors px-1">
            🔎
          </button>
          <button className="text-[10px] font-mono text-t-muted hover:text-t-secondary transition-colors px-1">
            📊
          </button>
        </div>
      </div>
    </>
  );
}
