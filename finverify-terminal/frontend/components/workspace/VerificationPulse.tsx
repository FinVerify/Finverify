"use client";

import React from "react";

/**
 * VerificationPulse — Horizontal metric strip showing high-level verification state.
 * Claims Checked, Verified, Corrected, Conflicts, Unresolved.
 * Per target screenshot — compact horizontal layout with strong numerical hierarchy.
 */

interface PulseMetric {
  label: string;
  value: number;
  subLabel?: string;
  subValue?: string;
  color: string;
}

const PULSE_METRICS: PulseMetric[] = [
  { label: "CLAIMS CHECKED", value: 1248, subLabel: "Today", subValue: "+23", color: "text-t-primary" },
  { label: "VERIFIED", value: 1082, subLabel: "", subValue: "77.9%", color: "text-t-green" },
  { label: "CORRECTED", value: 94, subLabel: "", subValue: "6.8%", color: "text-t-amber" },
  { label: "CONFLICTS", value: 38, subLabel: "", subValue: "2.7%", color: "text-t-red" },
  { label: "UNRESOLVED", value: 34, subLabel: "", subValue: "2.7%", color: "text-t-amber" },
];

export default function VerificationPulse() {
  return (
    <div className="panel">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-t-border/50">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
            VERIFICATION PULSE
          </span>
          <span className="flex items-center gap-1 text-[8px] font-mono text-t-green">
            <span className="w-[4px] h-[4px] rounded-full bg-t-green live-pulse" />
            LIVE
          </span>
        </div>
      </div>
      <div className="grid grid-cols-5 divide-x divide-t-border/30">
        {PULSE_METRICS.map((metric) => (
          <div key={metric.label} className="px-3 py-2 text-center">
            <div className={`text-[18px] font-mono font-bold tabular-nums ${metric.color}`}>
              {metric.value.toLocaleString()}
            </div>
            <div className="text-[8px] font-mono text-t-muted uppercase tracking-wider mt-0.5">
              {metric.label}
            </div>
            {metric.subValue && (
              <div className="text-[8px] font-mono text-t-muted mt-0.5 tabular-nums">
                {metric.subLabel && <span>{metric.subLabel} </span>}
                <span className={metric.color === "text-t-primary" ? "text-t-green" : metric.color}>
                  {metric.subValue}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
