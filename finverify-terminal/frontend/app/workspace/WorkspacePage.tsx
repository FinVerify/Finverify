"use client";

import React, { useState } from "react";
import MarketPulsePanel from "@/components/workspace/MarketPulsePanel";
import WatchlistPanel from "@/components/workspace/WatchlistPanel";
import IntegrityMonitorPanel from "@/components/workspace/IntegrityMonitorPanel";
import FocusView from "@/components/workspace/FocusView";
import { NewsRadarPanel, FilingRadarPanel, EarningsRadarPanel, SectorMonitorPanel } from "@/components/workspace/RightColumnPanels";
import WorkspaceBottomBar from "@/components/workspace/WorkspaceBottomBar";
import MarketAlertBanner from "@/components/workspace/MarketAlertBanner";

export default function WorkspacePage() {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

  return (
    <div className="flex flex-col min-h-[calc(100vh-68px)] lg:h-[calc(100vh-68px)] lg:overflow-hidden">
      {/* Market Alert Banner */}
      <div className="block shrink-0">
        <MarketAlertBanner />
      </div>

      {/* Main 3-column grid */}
      <div className="grid grid-cols-1 gap-1.5 p-1.5 min-w-0 flex-1 overflow-visible lg:grid-cols-[minmax(200px,0.8fr)_minmax(0,1.6fr)_minmax(200px,0.85fr)] lg:gap-1 lg:p-1 lg:overflow-hidden xl:grid-cols-[260px_minmax(0,1fr)_280px] xl:gap-[5px] xl:p-[5px]">
        {/* ── LEFT COLUMN ── */}
        <div className="flex flex-col gap-1.5 min-w-0 lg:gap-1 lg:min-h-0 lg:overflow-hidden xl:gap-[5px]">
          <div className="h-[200px] min-h-[200px] shrink-0">
            <MarketPulsePanel />
          </div>
          <div className="h-[340px] min-h-[240px] lg:flex-1 lg:min-h-[140px] lg:overflow-hidden">
            <WatchlistPanel selectedSymbol={selectedSymbol} onSelectSymbol={setSelectedSymbol} />
          </div>
          <div className="h-[180px] min-h-[160px] lg:h-[170px] shrink-0">
            <IntegrityMonitorPanel selectedSymbol={selectedSymbol} onSelectSymbol={setSelectedSymbol} />
          </div>
        </div>

        {/* ── CENTER COLUMN ── */}
        <div className="flex flex-col min-w-0 min-h-[520px] lg:min-h-0 lg:overflow-hidden">
          <FocusView
            selectedSymbol={selectedSymbol}
            onDeselect={() => setSelectedSymbol(null)}
            onSelectSymbol={setSelectedSymbol}
          />
        </div>

        {/* ── RIGHT COLUMN ── */}
        <div className="flex flex-col gap-1.5 min-w-0 lg:gap-1 lg:min-h-0 lg:overflow-y-auto xl:gap-[5px]">
          <div className="h-[165px] min-h-[165px] shrink-0"><NewsRadarPanel /></div>
          <div className="h-[150px] min-h-[150px] shrink-0"><FilingRadarPanel /></div>
          <div className="h-[140px] min-h-[140px] shrink-0"><EarningsRadarPanel /></div>
          <div className="flex-1 min-h-[160px]"><SectorMonitorPanel /></div>
        </div>
      </div>

      {/* Bottom Status Bar */}
      <div className="block shrink-0 overflow-hidden">
        <WorkspaceBottomBar onSelectSymbol={setSelectedSymbol} />
      </div>
    </div>
  );
}
