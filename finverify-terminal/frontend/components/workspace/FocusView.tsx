"use client";

import React, { useState, useEffect } from "react";
import EarningsVerification from "@/components/EarningsVerification";
import MetricPanel from "@/components/MetricPanel";
import GlobalTransactionMonitor from "@/components/workspace/GlobalTransactionMonitor";
import VerificationPulse from "@/components/workspace/VerificationPulse";
import RecentVerificationActivity from "@/components/workspace/RecentVerificationActivity";
import NeedsAttention from "@/components/workspace/NeedsAttention";
import VerificationCoverage from "@/components/workspace/VerificationCoverage";
import LiveVerificationTrace from "@/components/workspace/LiveVerificationTrace";
import CommandBar from "@/components/workspace/CommandBar";
import {
  getFundamentals,
  type FundamentalsResponse,
  type FundamentalMetric,
} from "@/lib/api";

/**
 * FocusView — Center column, fills entire center.
 * Two states: Default (verification intelligence workspace) and Company (selectedSymbol set).
 * Per §6 of UI_IMPLEMENTATION_PLAN.md, enhanced per target screenshot.
 *
 * Default state now shows:
 * 1. Global Transaction Monitor (reduced height)
 * 2. Verification Pulse
 * 3. Three-panel intelligence row (Recent Activity, Needs Attention, Coverage)
 * 4. Live Verification Trace
 * 5. Command Bar
 */

type FocusTab =
  | "integrity"
  | "verification"
  | "financials"
  | "evidence"
  | "timeline"
  | "filings";

const TAB_LABELS: { key: FocusTab; label: string }[] = [
  { key: "integrity", label: "INTEGRITY" },
  { key: "verification", label: "VERIFICATION" },
  { key: "financials", label: "FINANCIALS" },
  { key: "evidence", label: "EVIDENCE" },
  { key: "timeline", label: "TIMELINE" },
  { key: "filings", label: "FILINGS" },
];

/* ── Trust Badge (reused from EarningsVerification pattern) ── */
function TrustBadge({ trust }: { trust: string }) {
  const cls =
    trust === "HIGH"
      ? "bg-t-green/10 text-t-green border-t-green/20"
      : trust === "MEDIUM"
      ? "bg-t-amber/10 text-t-amber border-t-amber/20"
      : "bg-t-red/10 text-t-red border-t-red/20";
  return (
    <span className={`text-[8px] font-mono font-bold px-1.5 py-0.5 rounded border ${cls}`}>
      {trust}
    </span>
  );
}

/* ── Integrity Score Band ── */
function getIntegrityBand(score: number): { label: string; color: string; glow: string } {
  if (score >= 80) return { label: "HIGH", color: "text-t-green", glow: "glow-green" };
  if (score >= 50) return { label: "MEDIUM", color: "text-t-amber", glow: "glow-amber" };
  return { label: "LOW", color: "text-t-red", glow: "glow-red" };
}

/* ── Evidence Panel (FundamentalCard adapted from EarningsVerification) ── */
function EvidencePanel({ symbol }: { symbol: string }) {
  const [fundamentals, setFundamentals] = useState<FundamentalsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getFundamentals(symbol)
      .then(setFundamentals)
      .catch(() => setFundamentals(null))
      .finally(() => setLoading(false));
  }, [symbol]);

  const METRIC_LABELS: Record<string, string> = {
    net_income: "NET INCOME", revenue: "REVENUE", total_assets: "TOTAL ASSETS",
    eps_basic: "EPS (BASIC)", eps_diluted: "EPS (DILUTED)",
    operating_income: "OPERATING INCOME", gross_profit: "GROSS PROFIT",
    cost_of_revenue: "COST OF REVENUE", stockholders_equity: "STOCKHOLDERS' EQUITY",
  };

  const formatValue = (v: number) => {
    if (Math.abs(v) >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
    if (Math.abs(v) >= 1e9) return `$${(v / 1e9).toFixed(2)}B`;
    if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(1)}M`;
    if (Math.abs(v) >= 100) return `$${v.toFixed(2)}`;
    return v.toFixed(4);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span className="text-[10px] font-mono text-t-muted animate-pulse">
          Fetching SEC filing data for {symbol}...
        </span>
      </div>
    );
  }

  if (!fundamentals) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <span className="text-[10px] font-mono text-t-muted">
          No SEC filing data available for {symbol}
        </span>
      </div>
    );
  }

  return (
    <div className="p-2 grid grid-cols-2 lg:grid-cols-3 gap-1.5">
      {fundamentals.metrics.map((m: FundamentalMetric, i: number) => (
        <div key={m.metric_name || i} className="panel p-2 transition-all duration-300 hover:bg-white/[0.02]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[8px] font-mono font-bold text-t-secondary uppercase tracking-wider">
              {METRIC_LABELS[m.metric_name] || m.metric_name.toUpperCase()}
            </span>
            <TrustBadge trust={m.dvl_trust} />
          </div>
          <div className={`text-[14px] font-mono font-bold tabular-nums ${
            m.dvl_trust === "HIGH" ? "text-t-green" : m.dvl_trust === "MEDIUM" ? "text-t-amber" : "text-t-red"
          }`}>
            {formatValue(m.verified_value)}
          </div>
          <div className="flex items-center gap-1.5 mt-0.5 text-[7px] font-mono text-t-muted">
            <span>{m.period}</span>
            <span>•</span>
            <span>{m.filing_date}</span>
            {m.dvl_rule && <><span>•</span><span className="text-t-amber">{m.dvl_rule}</span></>}
          </div>
        </div>
      ))}
    </div>
  );
}

/* ── Demo integrity data ── */
const DEMO_INTEGRITY: Record<string, number> = {
  AAPL: 87, TSLA: 61, JPM: 78, NVDA: 92, MSFT: 85, GS: 74,
  COIN: 45, INTC: 53,
};

const COMPANY_NAMES: Record<string, string> = {
  AAPL: "Apple Inc.", TSLA: "Tesla Inc.", JPM: "JPMorgan Chase & Co.",
  NVDA: "NVIDIA Corporation", MSFT: "Microsoft Corporation",
  GS: "Goldman Sachs Group Inc.", COIN: "Coinbase Global Inc.",
  INTC: "Intel Corporation",
};

/* ── Main FocusView Component ── */
interface FocusViewProps {
  selectedSymbol: string | null;
  onDeselect: () => void;
  onSelectSymbol?: (symbol: string) => void;
}

export default function FocusView({ selectedSymbol, onDeselect, onSelectSymbol }: FocusViewProps) {
  const [activeTab, setActiveTab] = useState<FocusTab>("integrity");

  // Reset to integrity tab when symbol changes
  useEffect(() => {
    if (selectedSymbol) setActiveTab("integrity");
  }, [selectedSymbol]);

  // ── Default State (no selection) — Enhanced verification workspace ──
  if (!selectedSymbol) {
    return (
      <div className="flex flex-col h-full min-h-0">
        {/* Global Transaction Monitor — reduced height */}
        <div className="panel flex-shrink-0" style={{ height: "clamp(200px, 38vh, 320px)" }}>
          <GlobalTransactionMonitor onSelectSymbol={onSelectSymbol || (() => {})} />
        </div>

        {/* Scrollable verification intelligence area */}
        <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-[6px] mt-[6px]">
          {/* Verification Pulse */}
          <VerificationPulse />

          {/* Three-panel intelligence row */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-[6px]" style={{ minHeight: "160px" }}>
            <RecentVerificationActivity />
            <NeedsAttention />
            <VerificationCoverage />
          </div>

          {/* Live Verification Trace */}
          <LiveVerificationTrace />
        </div>

        {/* Command Bar */}
        <div className="flex-shrink-0 mt-[6px]">
          <CommandBar onSelectSymbol={onSelectSymbol || (() => {})} />
        </div>
      </div>
    );
  }

  // ── Company-Selected State ──
  const integrityScore = DEMO_INTEGRITY[selectedSymbol] ?? 65;
  const band = getIntegrityBand(integrityScore);
  const companyName = COMPANY_NAMES[selectedSymbol] ?? selectedSymbol;

  return (
    <div className="panel flex flex-col h-full min-h-0">
      {/* Company Header — always visible */}
      <div className={`px-3 py-2 border-b border-t-border flex items-center justify-between ${band.glow}`}>
        <div className="flex items-center gap-3">
          <button
            onClick={onDeselect}
            className="text-[9px] font-mono text-t-muted hover:text-t-secondary transition-colors"
            title="Back to overview"
          >
            ✕
          </button>
          <div>
            <div className="text-[12px] font-mono font-bold text-t-primary">
              {companyName}
              <span className="text-t-secondary ml-2">({selectedSymbol})</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-mono text-t-muted uppercase">Integrity:</span>
          <span className={`text-[22px] font-mono font-bold tabular-nums ${band.color}`}>
            {integrityScore}
          </span>
          <span className={`text-[8px] font-mono font-bold px-1.5 py-0.5 rounded border ${
            band.label === "HIGH"
              ? "bg-t-green/10 text-t-green border-t-green/20"
              : band.label === "MEDIUM"
              ? "bg-t-amber/10 text-t-amber border-t-amber/20"
              : "bg-t-red/10 text-t-red border-t-red/20"
          }`}>
            {band.label}
          </span>
          <span className="text-[8px] font-mono text-t-amber border border-t-amber/20 bg-t-amber/[0.04] px-1 py-0.5 rounded">
            DEMO
          </span>
        </div>
      </div>

      {/* Tab Strip */}
      <div className="flex border-b border-t-border">
        {TAB_LABELS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex-1 py-1.5 text-[9px] font-mono font-bold uppercase tracking-wider transition-colors ${
              activeTab === key
                ? "text-t-green border-b border-t-green bg-white/[0.02]"
                : "text-t-muted hover:text-t-secondary"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {activeTab === "integrity" && (
          <IntegrityTab symbol={selectedSymbol} score={integrityScore} />
        )}
        {activeTab === "verification" && (
          <EarningsVerification symbol={selectedSymbol} />
        )}
        {activeTab === "financials" && (
          <MetricPanel symbol={selectedSymbol} />
        )}
        {activeTab === "evidence" && (
          <EvidencePanel symbol={selectedSymbol} />
        )}
        {activeTab === "timeline" && (
          <TimelinePlaceholder symbol={selectedSymbol} />
        )}
        {activeTab === "filings" && (
          <FilingsPlaceholder symbol={selectedSymbol} />
        )}
      </div>
    </div>
  );
}

/* ── Integrity Tab (§6.4.1) ── */
function IntegrityTab({ symbol, score }: { symbol: string; score: number }) {
  // Demo breakdown — Consistency 40%, SEC Agreement 30%, DVL Confidence 30%
  const consistency = Math.round(score * 0.85 + Math.random() * 10);
  const secAgreement = Math.round(score * 0.9 + Math.random() * 8);
  const dvlConfidence = Math.round(score * 1.1 - Math.random() * 5);

  return (
    <div className="p-3 space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-[9px] font-mono text-t-muted uppercase tracking-wider">COMPOSITE SCORE BREAKDOWN</span>
        <span className="text-[8px] font-mono text-t-amber border border-t-amber/20 bg-t-amber/[0.04] px-1 py-0.5 rounded">
          DEMO DATA
        </span>
      </div>

      {/* Score bars */}
      {[
        { label: "Consistency", weight: "40%", value: Math.min(consistency, 100), color: "bg-t-green" },
        { label: "SEC Agreement", weight: "30%", value: Math.min(secAgreement, 100), color: "bg-t-cyan" },
        { label: "DVL Confidence", weight: "30%", value: Math.min(dvlConfidence, 100), color: "bg-t-blue" },
      ].map(({ label, weight, value, color }) => (
        <div key={label} className="space-y-1">
          <div className="flex items-center justify-between text-[9px] font-mono">
            <span className="text-t-secondary">{label} <span className="text-t-muted">({weight})</span></span>
            <span className={`font-bold ${value >= 80 ? "text-t-green" : value >= 50 ? "text-t-amber" : "text-t-red"}`}>
              {value}
            </span>
          </div>
          <div className="h-[4px] bg-t-border rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${color} transition-all duration-300`}
              style={{ width: `${value}%` }}
            />
          </div>
        </div>
      ))}

      {/* Explanation */}
      <div className="panel p-2.5 bg-[#0d0d0d] mt-2">
        <div className="text-[10px] font-mono text-t-secondary leading-relaxed">
          {score >= 80
            ? `${symbol} shows strong consistency across all verification dimensions. No significant discrepancies detected.`
            : score >= 50
            ? `${symbol} has moderate integrity. Some verification signals require attention — check the Verification tab for flagged claims.`
            : `${symbol} shows significant discrepancies. Multiple flagged claims detected — review the Verification and Evidence tabs.`
          }
        </div>
      </div>
    </div>
  );
}

/* ── Timeline Placeholder (§6.4.5) ── */
function TimelinePlaceholder({ symbol }: { symbol: string }) {
  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="text-center">
        <div className="text-[10px] font-mono text-t-muted leading-relaxed">
          No historical data yet — Integrity Score history for {symbol} begins accumulating from today.
        </div>
        <div className="text-[9px] font-mono text-t-muted/60 mt-2">
          Timeline will show integrity score trends with discrepancy annotations once historical data is available.
        </div>
      </div>
    </div>
  );
}

/* ── Filings Placeholder (§6.4.6) ── */
function FilingsPlaceholder({ symbol }: { symbol: string }) {
  const demoFilings = [
    { type: "10-Q", date: "2024-07-28", risk: false },
    { type: "8-K", date: "2024-07-15", risk: true },
    { type: "10-K", date: "2024-02-01", risk: false },
  ];

  return (
    <div className="p-2">
      <div className="flex items-center gap-2 px-2 py-1.5">
        <span className="text-[9px] font-mono text-t-muted uppercase tracking-wider">
          SEC FILINGS — {symbol}
        </span>
        <span className="text-[8px] font-mono text-t-amber border border-t-amber/20 bg-t-amber/[0.04] px-1 py-0.5 rounded">
          DEMO DATA
        </span>
      </div>
      {demoFilings.map((f, i) => (
        <div key={i} className="flex items-center justify-between px-2 py-1.5 border-b border-t-border/30 text-[10px] font-mono hover:bg-white/[0.02] transition-colors">
          <div className="flex items-center gap-2">
            {f.risk && <span className="text-t-red">🚩</span>}
            <span className="text-t-primary font-bold">{f.type}</span>
          </div>
          <span className="text-t-muted">{f.date}</span>
        </div>
      ))}
    </div>
  );
}
