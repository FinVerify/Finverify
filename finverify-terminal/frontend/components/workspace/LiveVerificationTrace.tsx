"use client";

import React from "react";

/**
 * LiveVerificationTrace — Pipeline visualization showing claim verification flow.
 * CLAIM EXTRACTED → ENTITY RESOLVED → EVIDENCE RETRIEVED → CALCULATION RECONSTRUCTED → CONSTRAINTS CHECK → RESULT
 * Per target screenshot — terminal-style live trace with step details.
 */

interface TraceStep {
  label: string;
  detail: string;
  subDetail?: string;
  status: "complete" | "active" | "pending";
}

const DEMO_TRACE: { timestamp: string; company: string; claim: string; steps: TraceStep[] } = {
  timestamp: "23:18:32",
  company: "NVIDIA",
  claim: "Revenue $130.50 (FY2025)",
  steps: [
    { label: "CLAIM EXTRACTED", detail: "Revenue reported as", subDetail: "$130.16", status: "complete" },
    { label: "ENTITY RESOLVED", detail: "NVIDIA Corp. (NVDA)", subDetail: "Match: Revenue", status: "complete" },
    { label: "EVIDENCE RETRIEVED", detail: "SEC 10-K (2025)", subDetail: "Filed: 02/26/2025", status: "complete" },
    { label: "CALCULATION RECONSTRUCTED", detail: "130.08 (reported)", subDetail: "130.30 (calculated)", status: "complete" },
    { label: "CONSTRAINTS CHECK", detail: "All 4 constraints", subDetail: "PASSED", status: "complete" },
    { label: "RESULT", detail: "✓ VERIFIED", subDetail: "Trust: 98.2%", status: "complete" },
  ],
};

export default function LiveVerificationTrace() {
  return (
    <div className="panel">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-t-border/50">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
            LIVE VERIFICATION TRACE
          </span>
          <span className="flex items-center gap-1 text-[8px] font-mono text-t-green">
            <span className="w-[3px] h-[3px] rounded-full bg-t-green live-pulse" />
            LIVE
          </span>
        </div>
      </div>
      
      <div className="px-3 py-2">
        {/* Trace header with timestamp and claim info */}
        <div className="flex items-center gap-3 mb-2">
          <span className="text-[8px] font-mono text-t-muted tabular-nums">{DEMO_TRACE.timestamp}</span>
          <span className="text-[9px] font-mono font-bold text-t-primary">{DEMO_TRACE.company}</span>
          <span className="text-[8px] font-mono text-t-muted">{DEMO_TRACE.claim}</span>
        </div>

        {/* Pipeline steps */}
        <div className="flex items-start gap-0 overflow-x-auto">
          {DEMO_TRACE.steps.map((step, i) => (
            <div key={step.label} className="flex items-start min-w-0">
              {/* Step box */}
              <div className={`px-2 py-1.5 rounded border min-w-[120px] ${
                step.status === "complete" 
                  ? "border-t-green/20 bg-t-green/[0.03]"
                  : step.status === "active"
                  ? "border-t-amber/20 bg-t-amber/[0.03]"
                  : "border-t-border/30 bg-transparent"
              }`}>
                <div className={`text-[7px] font-mono font-bold uppercase tracking-wider mb-0.5 ${
                  step.status === "complete" ? "text-t-green" : 
                  step.status === "active" ? "text-t-amber" : "text-t-muted"
                }`}>
                  {step.label}
                </div>
                <div className="text-[8px] font-mono text-t-secondary truncate">{step.detail}</div>
                {step.subDetail && (
                  <div className={`text-[7px] font-mono mt-0.5 tabular-nums ${
                    step.label === "RESULT" ? "text-t-green font-bold" : "text-t-muted"
                  }`}>
                    {step.subDetail}
                  </div>
                )}
              </div>
              {/* Connector arrow */}
              {i < DEMO_TRACE.steps.length - 1 && (
                <div className="flex items-center px-1 pt-3 shrink-0">
                  <span className="text-[8px] text-t-green/40">→</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
