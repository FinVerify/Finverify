"use client";
import React from "react";
import type { BatchClaimEntity } from "@/lib/api";

interface Props {
  entity: BatchClaimEntity | null;
  isDegraded?: boolean;
}

export default function EntityResolvedPanel({ entity, isDegraded }: Props) {
  if (isDegraded) {
    return (
      <div className="panel" style={{ borderLeft: "3px solid #888" }}>
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <span className="text-t-muted text-[10px] font-bold">②</span>
            <span className="label text-t-muted">ENTITY RESOLVED</span>
          </div>
          <span className="text-[9px] font-mono text-t-muted">NOT PERFORMED</span>
        </div>
        <div className="px-3 py-2">
          <div className="text-[10px] font-mono text-t-muted">
            Entity resolution not available in degraded mode.
          </div>
        </div>
      </div>
    );
  }

  if (!entity) return null;

  return (
    <div className="panel" style={{ borderLeft: "3px solid #00ff88" }}>
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <span className="text-t-green text-[10px] font-bold">②</span>
          <span className="label text-t-green">ENTITY RESOLVED</span>
        </div>
        <span className="text-[9px] font-mono text-t-green">OK ✓</span>
      </div>
      <div className="px-3 py-2">
        <div className="grid grid-cols-[auto_1fr_auto_1fr] gap-x-4 gap-y-1 text-[10px] font-mono">
          <span className="text-t-muted">Entity</span>
          <span className="text-t-primary">{entity.name}</span>
          <span className="text-t-muted">Ticker</span>
          <span className="text-t-cyan">{entity.ticker || "—"}</span>
          {entity.cik && (
            <>
              <span className="text-t-muted">CIK</span>
              <span className="text-t-secondary">{entity.cik}</span>
            </>
          )}
          {entity.lei && (
            <>
              <span className="text-t-muted">LEI</span>
              <span className="text-t-secondary">{entity.lei}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
