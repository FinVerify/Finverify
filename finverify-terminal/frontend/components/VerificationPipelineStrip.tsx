"use client";
import React from "react";

export type PipelineStageId =
  | "claim_parsed"
  | "entity_resolved"
  | "evidence_retrieved"
  | "calculation"
  | "constraints"
  | "result";

interface StageConfig {
  id: PipelineStageId;
  num: number;
  label: string;
}

const STAGES: StageConfig[] = [
  { id: "claim_parsed", num: 1, label: "CLAIM PARSED" },
  { id: "entity_resolved", num: 2, label: "ENTITY RESOLVED" },
  { id: "evidence_retrieved", num: 3, label: "EVIDENCE RETRIEVED" },
  { id: "calculation", num: 4, label: "CALCULATION" },
  { id: "constraints", num: 5, label: "CONSTRAINTS" },
  { id: "result", num: 6, label: "RESULT" },
];

export type StageStatus = "idle" | "active" | "complete" | "error" | "na" | "degraded";

interface Props {
  stageStatuses: Record<PipelineStageId, StageStatus>;
  activeStage: PipelineStageId | null;
  onStageClick?: (stage: PipelineStageId) => void;
}

function getStageColor(status: StageStatus): string {
  switch (status) {
    case "complete": return "#00ff88";
    case "active": return "#fbbf24";
    case "error": return "#f87171";
    case "na": return "#888888";
    case "degraded": return "#f59e0b";
    default: return "#333333";
  }
}

function getStageIcon(status: StageStatus): string {
  switch (status) {
    case "complete": return "✓";
    case "active": return "›";
    case "error": return "✗";
    case "na": return "—";
    case "degraded": return "⚠";
    default: return "·";
  }
}

export default function VerificationPipelineStrip({ stageStatuses, activeStage, onStageClick }: Props) {
  return (
    <div className="panel">
      <div className="panel-header">
        <span className="label text-t-cyan">VERIFICATION PIPELINE</span>
      </div>
      <div className="px-3 py-2.5">
        {/* Pipeline nodes with connecting lines */}
        <div className="flex items-center justify-between gap-0">
          {STAGES.map((stage, i) => {
            const status = stageStatuses[stage.id];
            const color = getStageColor(status);
            const isActive = activeStage === stage.id;

            return (
              <React.Fragment key={stage.id}>
                <button
                  onClick={() => onStageClick?.(stage.id)}
                  className="flex flex-col items-center gap-1 group cursor-pointer relative"
                  style={{ minWidth: 0, flex: "0 0 auto" }}
                >
                  {/* Node circle */}
                  <div
                    className={`w-[28px] h-[28px] rounded-full border-2 flex items-center justify-center text-[10px] font-mono font-bold transition-all duration-300 ${
                      isActive ? "live-pulse" : ""
                    }`}
                    style={{
                      borderColor: color,
                      background: status === "complete" ? `${color}15` : status === "active" ? `${color}10` : "transparent",
                      color: color,
                      boxShadow: status === "complete" || isActive ? `0 0 8px ${color}30` : "none",
                    }}
                  >
                    {status === "idle" ? stage.num : getStageIcon(status)}
                  </div>
                  {/* Label */}
                  <span
                    className="text-[7px] font-mono font-bold tracking-wider uppercase whitespace-nowrap"
                    style={{ color: status === "idle" ? "#555" : color }}
                  >
                    {stage.label}
                  </span>
                </button>
                {/* Connecting line */}
                {i < STAGES.length - 1 && (
                  <div
                    className="flex-1 h-[2px] mx-1 transition-colors duration-300"
                    style={{
                      background:
                        stageStatuses[STAGES[i + 1].id] !== "idle"
                          ? `linear-gradient(90deg, ${getStageColor(status)}, ${getStageColor(stageStatuses[STAGES[i + 1].id])})`
                          : status !== "idle"
                            ? `linear-gradient(90deg, ${color}, #222)`
                            : "#1e1e1e",
                      minWidth: "12px",
                    }}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
