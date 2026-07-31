"use client";

import React from "react";
import NavHealthIndicator from "@/components/NavHealthIndicator";

export default function WorkspaceTopBar() {
  return (
    <div className="h-[40px] border-b border-t-border bg-t-bg flex items-center justify-between px-4 sticky top-0 z-50">
      <div className="flex items-center gap-2">
        <span className="text-[12px] font-mono font-bold text-t-green">FINVERIFY</span>
        <span className="text-[9px] font-mono text-t-muted">— INTELLIGENCE WORKSPACE</span>
      </div>
      <div className="flex items-center gap-4">
        <NavHealthIndicator />
        <span className="text-[10px] font-mono text-t-muted">⌘K</span>
      </div>
    </div>
  );
}