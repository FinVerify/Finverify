"use client";
import React from "react";
import type { BatchEvidence } from "@/lib/api";

interface Props {
  evidence: BatchEvidence[];
  isDegraded?: boolean;
}

export default function EvidenceRetrievedPanel({ evidence, isDegraded }: Props) {
  if (isDegraded) {
    return (
      <div className="panel" style={{ borderLeft: "3px solid #888" }}>
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <span className="text-t-muted text-[10px] font-bold">③</span>
            <span className="label text-t-muted">EVIDENCE RETRIEVED</span>
          </div>
          <span className="text-[9px] font-mono text-t-muted">NOT PERFORMED</span>
        </div>
        <div className="px-3 py-2">
          <div className="text-[10px] font-mono text-t-muted">
            Evidence retrieval not available in degraded mode.
          </div>
        </div>
      </div>
    );
  }

  // Find SEC evidence (primary/secondary), vs model_input evidence
  const secEvidence = evidence.filter((e) => e.source.kind === "primary_filing" || e.source.kind === "secondary");
  const hasPrimaryEvidence = secEvidence.length > 0;
  const primarySource = secEvidence[0] || evidence[0];

  return (
    <div className="panel" style={{ borderLeft: `3px solid ${hasPrimaryEvidence ? "#00ff88" : "#fbbf24"}` }}>
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <span className={`${hasPrimaryEvidence ? "text-t-green" : "text-t-amber"} text-[10px] font-bold`}>③</span>
          <span className={`label ${hasPrimaryEvidence ? "text-t-green" : "text-t-amber"}`}>EVIDENCE RETRIEVED</span>
        </div>
        <div className="flex items-center gap-2">
          {primarySource?.source?.url && (
            <a
              href={primarySource.source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[9px] font-mono text-t-cyan hover:underline"
            >
              VIEW SOURCE
            </a>
          )}
          <span className={`text-[9px] font-mono ${hasPrimaryEvidence ? "text-t-green" : "text-t-amber"}`}>
            {hasPrimaryEvidence ? "OK ✓" : "MODEL ONLY"}
          </span>
        </div>
      </div>
      <div className="px-3 py-2 space-y-2">
        {primarySource && (
          <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-[10px] font-mono">
            <span className="text-t-muted">Source</span>
            <span className="text-t-primary">{primarySource.source.name}</span>
            {primarySource.source.kind && (
              <>
                <span className="text-t-muted">Document</span>
                <span className="text-t-secondary">{primarySource.source.kind.replace(/_/g, " ")}</span>
              </>
            )}
            {primarySource.source.retrieved_at && (
              <>
                <span className="text-t-muted">Filing Date</span>
                <span className="text-t-secondary">
                  {new Date(primarySource.source.retrieved_at).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </>
            )}
            {primarySource.period && (
              <>
                <span className="text-t-muted">Period Covered</span>
                <span className="text-t-secondary">{primarySource.period}</span>
              </>
            )}
          </div>
        )}

        {/* Evidence count */}
        {evidence.length > 1 && (
          <div className="text-[9px] font-mono text-t-muted pt-1 border-t border-t-border/30">
            {evidence.length} evidence entries retrieved
            {secEvidence.length > 0 && ` (${secEvidence.length} from SEC EDGAR)`}
          </div>
        )}

        {evidence.length === 0 && (
          <div className="text-[10px] font-mono text-t-muted">
            No evidence was retrieved for this claim.
          </div>
        )}
      </div>
    </div>
  );
}
