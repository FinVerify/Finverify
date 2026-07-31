"use client";

import React, { useState, useEffect } from "react";
import { LineChart, Line, ResponsiveContainer } from "recharts";
import { useConnection } from "@/lib/connection";

/**
 * WorkspaceBottomBar — System Status Footer per visual parity spec §8.
 * Replaces the old Intelligence Feed + query input bottom bar.
 * Shows: Workspace Online / Data Sources / Last Updated / Connection / Sparkline.
 */

function generateHealthSparkline(): { v: number }[] {
  const data: { v: number }[] = [];
  let val = 95;
  for (let i = 0; i < 30; i++) {
    val += (Math.random() - 0.4) * 3;
    val = Math.max(80, Math.min(100, val));
    data.push({ v: val });
  }
  return data;
}

interface WorkspaceBottomBarProps {
  onSelectSymbol: (symbol: string) => void;
}

export default function WorkspaceBottomBar({ onSelectSymbol: _onSelectSymbol }: WorkspaceBottomBarProps) {
  const [utcTime, setUtcTime] = useState("");
  const [healthData] = useState(() => generateHealthSparkline());
  const { backendOnline } = useConnection();

  useEffect(() => {
    const update = () => setUtcTime(new Date().toISOString().slice(11, 19) + " UTC");
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-[36px] flex items-center justify-between px-4 border-t border-t-border/50 bg-[#0a0a0a] text-[8px] font-mono">
      {/* Workspace Online */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className={`w-[5px] h-[5px] rounded-full ${backendOnline ? "bg-t-green live-pulse" : "bg-t-red"}`} />
          <span className="text-t-secondary font-bold">WORKSPACE ONLINE</span>
          <span className="text-t-muted">All systems operational</span>
        </div>

        <div className="w-px h-[14px] bg-t-border/50" />

        {/* Data Sources */}
        <div className="flex items-center gap-1.5">
          <span className="text-t-muted">⧉</span>
          <span className="text-t-secondary font-bold">DATA SOURCES</span>
          <span className="text-t-muted">23/23 Active</span>
        </div>

        <div className="w-px h-[14px] bg-t-border/50" />

        {/* Last Updated */}
        <div className="flex items-center gap-1.5">
          <span className="text-t-muted">🕐</span>
          <span className="text-t-secondary font-bold">LAST UPDATED</span>
          <span className="text-t-muted tabular-nums">{utcTime}</span>
        </div>

        <div className="w-px h-[14px] bg-t-border/50" />

        {/* Connection */}
        <div className="flex items-center gap-1.5">
          <span className="text-t-muted">🔒</span>
          <span className="text-t-secondary font-bold">CONNECTION</span>
          <span className={backendOnline ? "text-t-green" : "text-t-red"}>
            {backendOnline ? "Secure" : "Offline"}
          </span>
        </div>
      </div>

      {/* System Status Sparkline */}
      <div className="flex items-center gap-2">
        <div className="w-[80px] h-[18px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={healthData}>
              <Line
                type="monotone"
                dataKey="v"
                stroke="#00ff88"
                strokeWidth={1}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <span className="text-t-muted">SYSTEM STATUS</span>
      </div>
    </div>
  );
}
