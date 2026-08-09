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
    <div className="flex flex-col min-h-[calc(100vh-76px)] lg:h-[calc(100vh-76px)] lg:overflow-hidden">
      <div className="block shrink-0">
        <MarketAlertBanner />
      </div>

      <div className="grid grid-cols-1 gap-2 p-2 min-w-0 flex-1 overflow-visible lg:grid-cols-[minmax(220px,0.85fr)_minmax(0,1.5fr)_minmax(220px,0.9fr)] lg:gap-1 lg:p-1 lg:overflow-hidden xl:grid-cols-[280px_minmax(0,1fr)_300px] xl:gap-[6px] xl:p-[6px]">
        <div className="flex flex-col gap-2 min-w-0 lg:gap-1 lg:min-h-0 lg:overflow-hidden xl:gap-[6px]">
          <div className="h-[220px] min-h-[220px]">
            <MarketPulsePanel />
          </div>
          <div className="h-[360px] min-h-[260px] lg:flex-1 lg:min-h-[160px] lg:overflow-hidden">
            <WatchlistPanel selectedSymbol={selectedSymbol} onSelectSymbol={setSelectedSymbol} />
          </div>
          <div className="h-[220px] min-h-[200px] lg:h-[200px]">
            <IntegrityMonitorPanel selectedSymbol={selectedSymbol} onSelectSymbol={setSelectedSymbol} />
          </div>
        </div>

        <div className="flex flex-col min-w-0 min-h-[520px] lg:min-h-0 lg:overflow-hidden">
          <FocusView
            selectedSymbol={selectedSymbol}
            onDeselect={() => setSelectedSymbol(null)}
            onSelectSymbol={setSelectedSymbol}
          />
        </div>

        <div className="flex flex-col gap-2 min-w-0 lg:gap-1 lg:min-h-0 lg:overflow-y-auto xl:gap-[6px]">
          <div className="h-[180px] min-h-[180px]"><NewsRadarPanel /></div>
          <div className="h-[160px] min-h-[160px]"><FilingRadarPanel /></div>
          <div className="h-[160px] min-h-[160px]"><EarningsRadarPanel /></div>
          <div className="flex-1 min-h-[120px]"><SectorMonitorPanel /></div>
        </div>
      </div>

      <div className="block shrink-0 overflow-hidden">
        <WorkspaceBottomBar onSelectSymbol={setSelectedSymbol} />
      </div>
    </div>
  );
}
