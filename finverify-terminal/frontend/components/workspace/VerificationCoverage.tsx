"use client";

import React from "react";
import AccessibleScore from "./AccessibleScore";

/**
 * VerificationCoverage — Table showing per-company verification coverage.
 * Per target screenshot — compact table with company, verified, corrected, conflicts, trust score.
 */

interface CoverageRow {
  company: string;
  verified: number;
  corrected: number;
  conflicts: number;
  trustScore: number;
}

const DEMO_COVERAGE: CoverageRow[] = [
  { company: "NVIDIA", verified: 142, corrected: 3, conflicts: 0, trustScore: 98.2 },
  { company: "Apple", verified: 138, corrected: 2, conflicts: 0, trustScore: 97.1 },
  { company: "Microsoft", verified: 111, corrected: 1, conflicts: 0, trustScore: 98.0 },
  { company: "JPMorgan", verified: 184, corrected: 5, conflicts: 1, trustScore: 97.3 },
  { company: "Amazon", verified: 96, corrected: 3, conflicts: 1, trustScore: 96.1 },
  { company: "Tesla", verified: 87, corrected: 8, conflicts: 3, trustScore: 91.5 },
  { company: "Meta", verified: 89, corrected: 4, conflicts: 2, trustScore: 93.4 },
];

function getTrustColor(score: number): string {
  if (score >= 97) return "text-t-green";
  if (score >= 93) return "text-t-amber";
  return "text-t-red";
}

function getTrustLevel(score: number): string {
  if (score >= 97) return "high";
  if (score >= 93) return "medium";
  return "low";
}

export default function VerificationCoverage() {
  return (
    <div className="panel flex flex-col h-full min-h-0">
      <div className="flex items-center justify-between px-2 py-1.5 border-b border-t-border/50">
        <span className="text-[9px] font-mono font-bold text-t-secondary uppercase tracking-wider">
          VERIFICATION COVERAGE
        </span>
        <span className="text-[7px] font-mono text-t-muted">TOP COMPANIES</span>
      </div>

      <div className="flex-1 overflow-y-auto">
        <table className="w-full table-fixed text-[9px] font-mono">
          <caption className="sr-only">Verification coverage and trust scores for top companies</caption>
          <colgroup>
            <col />
            <col className="w-[50px]" />
            <col className="w-[55px]" />
            <col className="w-[55px]" />
            <col className="w-[60px]" />
          </colgroup>
          <thead className="text-[7px] text-t-muted uppercase tracking-wider border-b border-t-border/30">
            <tr>
              <th scope="col" className="px-2 py-1 text-left font-normal">COMPANY</th>
              <th scope="col" className="py-1 text-right font-normal">VERIFIED</th>
              <th scope="col" className="py-1 text-right font-normal">CORRECTED</th>
              <th scope="col" className="py-1 text-right font-normal">CONFLICTS</th>
              <th scope="col" className="pr-2 py-1 text-right font-normal">TRUST SCORE</th>
            </tr>
          </thead>
          <tbody>
            {DEMO_COVERAGE.map((row) => {
              const trustLevel = getTrustLevel(row.trustScore);

              return (
                <tr
                  key={row.company}
                  className="border-b border-t-border/10 last:border-b-0 hover:bg-white/[0.02] transition-colors"
                >
                  <th scope="row" className="px-2 py-1 text-left font-normal text-t-secondary truncate">
                    {row.company}
                  </th>
                  <td className="py-1 text-right text-t-primary tabular-nums">{row.verified}</td>
                  <td className={`py-1 text-right tabular-nums ${row.corrected > 4 ? "text-t-amber" : "text-t-muted"}`}>
                    {row.corrected}
                  </td>
                  <td className={`py-1 text-right tabular-nums ${row.conflicts > 0 ? "text-t-red" : "text-t-muted"}`}>
                    {row.conflicts}
                  </td>
                  <td className="pr-2 py-1 text-right">
                    <AccessibleScore
                      label={`${row.company} trust score`}
                      value={row.trustScore}
                      valueText={`${row.trustScore.toFixed(1)} percent, ${trustLevel} confidence`}
                      className={`inline-block font-bold tabular-nums ${getTrustColor(row.trustScore)}`}
                    >
                      {row.trustScore.toFixed(1)}%
                    </AccessibleScore>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="px-2 py-1 border-t border-t-border/50 text-center">
        <span className="text-[8px] font-mono text-t-muted hover:text-t-secondary cursor-pointer transition-colors">
          VIEW ALL COMPANIES →
        </span>
      </div>
    </div>
  );
}
