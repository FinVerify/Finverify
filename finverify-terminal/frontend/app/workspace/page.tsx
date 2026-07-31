"use client";

import React, { useState } from "react";
import MarketPulsePanel from "@/components/workspace/MarketPulsePanel";
import WatchlistPanel from "@/components/workspace/WatchlistPanel";
import IntegrityMonitorPanel from "@/components/workspace/IntegrityMonitorPanel";
import FocusView from "@/components/workspace/FocusView";
import {
  NewsRadarPanel,
  FilingRadarPanel,
  EarningsRadarPanel,
  SectorMonitorPanel,
} from "@/components/workspace/RightColumnPanels";
import WorkspaceBottomBar from "@/components/workspace/WorkspaceBottomBar";
import MarketAlertBanner from "@/components/workspace/MarketAlertBanner";

// Root header ~44px + TickerBar ~32px = ~76px already consumed by root layout
const ROOT_CHROME_HEIGHT = 76;

export default function WorkspacePage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  return (
    <div
      className="flex flex-col overflow-hidden"
      style={{ height: `calc(100vh - ${ROOT_CHROME_HEIGHT}px)` }}
    >
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

      {/* Market Alert Banner — ~32px */}
      <div className="hidden lg:block">
        <MarketAlertBanner />
      </div>

      {/* Main Grid — fills remaining viewport height */}
      <div className="hidden lg:grid grid-cols-[280px_1fr_300px] gap-[6px] p-[6px] min-h-0 flex-1 overflow-hidden">
        {/* ── Left Column ── */}
        <div className="flex flex-col gap-[6px] min-h-0 overflow-hidden">
          <div className="h-[220px] min-h-[220px]">
            <MarketPulsePanel />
          </div>
          <div className="flex-1 min-h-[160px] overflow-hidden">
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
          {/* Focus View */}
          <FocusView
            selectedSymbol={selectedSymbol}
            onDeselect={() => setSelectedSymbol(null)}
            onSelectSymbol={setSelectedSymbol}
          />
        </div>

        {/* ── Right Column ── */}
        <div className="flex flex-col gap-[6px] min-h-0 overflow-y-auto">
          <div className="h-[180px] min-h-[180px]">
            <NewsRadarPanel />
          </div>
          <div className="h-[160px] min-h-[160px]">
            <FilingRadarPanel />
          </div>
          <div className="h-[160px] min-h-[160px]">
            <EarningsRadarPanel />
          </div>
          <div className="flex-1 min-h-[120px]">
            <SectorMonitorPanel />
          </div>
        </div>
      </div>

      {/* ── System Status Footer ── */}
      <div className="hidden lg:block">
        <WorkspaceBottomBar onSelectSymbol={setSelectedSymbol} />
      </div>
    </div>
  );
}
