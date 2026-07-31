"use client";

import React, { useState, useEffect } from "react";
import NavHealthIndicator from "@/components/NavHealthIndicator";

/**
 * WorkspaceTopBar — 40px sticky top bar for the Intelligence Workspace.
 * Left: wordmark. Right: live clock, health indicator, settings stub, ⌘K hint.
 * Per §3.2 of UI_IMPLEMENTATION_PLAN.md.
 */
export default function WorkspaceTopBar() {
  const [time, setTime] = useState("");

  useEffect(() => {
    const update = () =>
      setTime(new Date().toLocaleTimeString("en-US", { hour12: false }));
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  const isMac =
    typeof navigator !== "undefined" && /Mac/.test(navigator.userAgent);

  return (
    <header className="h-[40px] min-h-[40px] flex items-center justify-between px-4 border-b border-t-border bg-t-bg sticky top-0 z-50">
      {/* Left: Wordmark */}
      <div className="flex items-center gap-2">
        <span className="text-t-green font-bold text-sm tracking-widest font-mono">
          FINVERIFY
        </span>
        <span className="text-t-secondary text-[10px] font-mono">
          — INTELLIGENCE WORKSPACE
        </span>
      </div>

      {/* Right: Clock, Health, Settings, Shortcut */}
      <div className="flex items-center gap-4">
        <span className="text-[10px] font-mono text-t-secondary tabular-nums">
          {time}
        </span>
        <NavHealthIndicator />
        <button
          className="text-[10px] font-mono text-t-muted hover:text-t-secondary transition-colors"
          title="Settings (coming soon)"
        >
          ⚙
        </button>
        <span className="text-[9px] font-mono text-t-muted bg-white/[0.03] border border-t-border px-1.5 py-0.5 rounded">
          {isMac ? "⌘" : "Ctrl"}+K
        </span>
      </div>
    </header>
  );
}
