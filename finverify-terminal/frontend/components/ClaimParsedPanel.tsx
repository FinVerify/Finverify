"use client";
import React from "react";
import type { BatchClaim } from "@/lib/api";

interface Props {
  claim: BatchClaim | null;
  isDegraded?: boolean;
}

export default function ClaimParsedPanel({ claim, isDegraded }: Props) {
  if (!claim) return null;

  return (
    <div className="panel" style={{ borderLeft: "3px solid #00ff88" }}>
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <span className="text-t-green text-[10px] font-bold">①</span>
          <span className="label text-t-green">CLAIM PARSED</span>
        </div>
        <span className="text-[9px] font-mono text-t-green">OK ✓</span>
      </div>
      <div className="px-3 py-2 space-y-1.5">
        {isDegraded && (
          <div className="text-[9px] font-mono text-t-amber mb-1">
            ⚠ DEGRADED MODE — local parse only
          </div>
        )}
        <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[10px] font-mono">
          {claim.metric?.name && (
            <>
              <span className="text-t-muted">Metric</span>
              <span className="text-t-primary">{claim.metric.name}</span>
            </>
          )}
          {claim.period && (
            <>
              <span className="text-t-muted">Period</span>
              <span className="text-t-primary">{claim.period}</span>
            </>
          )}
          {claim.raw_value !== null && (
            <>
              <span className="text-t-muted">Claimed Value</span>
              <span className="text-t-primary">{claim.raw_value}</span>
            </>
          )}
          {claim.metric?.unit && (
            <>
              <span className="text-t-muted">Type</span>
              <span className="text-t-primary">{claim.metric.unit}</span>
            </>
          )}
          {!claim.metric?.unit && claim.metric?.name && (
            <>
              <span className="text-t-muted">Type</span>
              <span className="text-t-secondary">
                {/margin|ratio|rate|percent|growth|yield|return/i.test(claim.metric.name) ? "Percentage" : "Numeric"}
              </span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
