"use client";

import React, { useState, useEffect } from "react";
import { useConnection } from "@/lib/connection";

/**
 * WorkspaceBottomBar — System Status Footer per target screenshot.
 * Shows: Workspace Online / Data Sources / Last Updated / Connection / System Status label.
 */

interface WorkspaceBottomBarProps {
  onSelectSymbol: (symbol: string) => void;
}

export default function WorkspaceBottomBar({ onSelectSymbol: _onSelectSymbol }: WorkspaceBottomBarProps) {
  const [utcTime, setUtcTime] = useState("");
  const { backendOnline } = useConnection();

  useEffect(() => {
    const update = () => setUtcTime(new Date().toISOString().slice(11, 19) + " UTC");
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-[30px] flex items-center justify-between px-4 border-t border-t-border/50 bg-[#0a0a0a] text-[8px] font-mono">
      {/* Left status items */}
      <div className="flex items-center gap-3 overflow-hidden">
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`w-[5px] h-[5px] rounded-full ${backendOnline ? "bg-t-green live-pulse" : "bg-t-red"}`} />
          <span className="text-t-secondary font-bold">WORKSPACE ONLINE</span>
          <span className="text-t-muted hidden sm:inline">All systems operational</span>
        </div>

        <div className="w-px h-[14px] bg-t-border/50 shrink-0" />

        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-t-muted">⧉</span>
          <span className="text-t-secondary font-bold">DATA SOURCES</span>
          <span className="text-t-muted">18/20 Active</span>
        </div>

        <div className="w-px h-[14px] bg-t-border/50 shrink-0" />

        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-t-muted">🕐</span>
          <span className="text-t-secondary font-bold">LAST UPDATED</span>
          <span className="text-t-muted tabular-nums">{utcTime}</span>
        </div>

        <div className="w-px h-[14px] bg-t-border/50 shrink-0" />

        <div className="flex items-center gap-1.5 shrink-0">
          <span className="text-t-muted">🔒</span>
          <span className="text-t-secondary font-bold">CONNECTION</span>
          <span className={backendOnline ? "text-t-green" : "text-t-red"}>
            {backendOnline ? "Secure" : "Offline"}
          </span>
        </div>
      </div>

      {/* Right: System Status label */}
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-t-muted">SYSTEM STATUS</span>
      </div>
    </div>
  );
}
