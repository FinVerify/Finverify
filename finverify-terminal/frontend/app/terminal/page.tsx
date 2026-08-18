"use client";
import React, { useState, useCallback } from "react";
import QueryInput from "@/components/QueryInput";
import TerminalPanel from "@/components/TerminalPanel";
import TrustScore from "@/components/TrustScore";
import DVLReport from "@/components/DVLReport";
import VerificationPipelineStrip, { type PipelineStageId, type StageStatus } from "@/components/VerificationPipelineStrip";
import ClaimParsedPanel from "@/components/ClaimParsedPanel";
import EntityResolvedPanel from "@/components/EntityResolvedPanel";
import EvidenceRetrievedPanel from "@/components/EvidenceRetrievedPanel";
import CalculationPanel from "@/components/CalculationPanel";
import ConstraintsPanel from "@/components/ConstraintsPanel";
import { verifyClaimFull, verifyNumber, queryLLM, type QueryResponse, type FullVerificationResult, type BatchVerificationResult } from "@/lib/api";
import { useConnection } from "@/lib/connection";
import { addToHistory } from "@/lib/history";

/* ── Client-side DVL fallback ── */
const RATIO_KW = ["ratio","percentage","percent","rate","margin","return","yield","growth","change","increase","decrease","loss"];
const ADVISORY_KW = ["should i","recommend","advice","invest in","buy or sell","good investment","better stock","where should"];
function isAdvisoryQuery(q: string): boolean { return ADVISORY_KW.some((kw) => q.toLowerCase().includes(kw)); }

function clientDVL(question: string, raw: number): QueryResponse {
  const isRatio = RATIO_KW.some((kw) => question.toLowerCase().includes(kw));
  let value = raw;
  const log: QueryResponse["correction_log"] = [];
  if (isRatio) {
    if (Math.abs(value) > 100) { const c = value / 100; log.push({ rule: "scale_div100", before: value, after: c, description: "Percentage-decimal confusion" }); value = c; }
    else if (Math.abs(value) < 1) { const c = value * 100; log.push({ rule: "scale_mul100", before: value, after: c, description: "Percentage-decimal confusion" }); value = c; }
  }
  let trust: string, trustColor: string;
  if (log.length === 0) { trust = "HIGH"; trustColor = "#00ff88"; }
  else { trust = "MEDIUM"; trustColor = "#fbbf24"; }
  const display = isRatio ? `${value.toFixed(2)}%` : Math.abs(value) > 1e6 ? value.toLocaleString() : value.toFixed(4);
  return { question, raw_text: `LLM output: ${raw}`, raw_number: raw, verified_number: value, correction_log: log, trust_score: trust, trust_color: trustColor, display_value: display, mode: "numerical", verified: true };
}

const DEMO_NUMS: Record<string, number> = {
  "YoY operating margin change?": 0.1240, "CET1 ratio Q4 2022?": 10.935,
  "Net income increase YoY?": 1250000, "Revenue growth rate?": 8.14,
  "HTM securities decrease?": -34.11, "Class A shares outstanding change?": 104.0,
};

/* ── Claim text parser — extracts numeric value + hints from free text ── */
const ENTITY_PATTERNS: Record<string, { name: string; ticker: string }> = {
  "tesla": { name: "Tesla, Inc.", ticker: "TSLA" },
  "apple": { name: "Apple Inc.", ticker: "AAPL" },
  "jpmorgan": { name: "JPMorgan Chase & Co.", ticker: "JPM" },
  "microsoft": { name: "Microsoft Corporation", ticker: "MSFT" },
  "google": { name: "Alphabet Inc.", ticker: "GOOGL" },
  "alphabet": { name: "Alphabet Inc.", ticker: "GOOGL" },
  "amazon": { name: "Amazon.com, Inc.", ticker: "AMZN" },
  "nvidia": { name: "NVIDIA Corporation", ticker: "NVDA" },
  "meta": { name: "Meta Platforms, Inc.", ticker: "META" },
};

const METRIC_PATTERNS: [RegExp, string][] = [
  [/operating\s*margin/i, "Operating Margin"],
  [/profit\s*margin/i, "Profit Margin"],
  [/net\s*margin/i, "Net Margin"],
  [/gross\s*margin/i, "Gross Margin"],
  [/revenue\s*growth/i, "Revenue Growth"],
  [/eps|earnings\s*per\s*share/i, "EPS"],
  [/net\s*income/i, "Net Income"],
  [/revenue/i, "Revenue"],
  [/cet1\s*ratio/i, "CET1 Ratio"],
  [/operating\s*income/i, "Operating Income"],
  [/return\s*on\s*equity|roe/i, "ROE"],
  [/return\s*on\s*assets|roa/i, "ROA"],
];

const PERIOD_RE = /(?:Q[1-4]\s*(?:FY\s*)?\d{4}|FY\s*\d{4}|\d{4}\s*Q[1-4]|(?:Q[1-4])\s+\d{4})/i;

interface ParsedClaim {
  rawValue: number;
  entity?: string;
  ticker?: string;
  metric?: string;
  period?: string;
}

function parseClaimText(text: string): ParsedClaim {
  // Extract numeric value — look for numbers with optional %, $, commas, decimals, negative
  // Patterns: "16.9%", "$1,572M", "-10.44pp", "0.169", "1250000", "16.9 percent"
  const numPatterns = [
    /(-?\$?[\d,]+\.?\d*)\s*(?:%|percent|pct|pp|percentage)/i,  // percentage values
    /(-?\$?[\d,]+\.?\d*)\s*(?:billion|B)\b/i,  // billions
    /(-?\$?[\d,]+\.?\d*)\s*(?:million|M)\b/i,  // millions
    /(?:was|is|at|of|approximately|about|roughly|around|reached|reported)\s+(-?\$?[\d,]+\.?\d*)/i,  // "was 16.9"
    /(-?\d+\.\d+)/,  // decimal numbers
    /(-?\d{1,})/,  // integers
  ];

  let rawValue = 0;
  for (const pat of numPatterns) {
    const m = text.match(pat);
    if (m) {
      const numStr = (m[1] || m[0]).replace(/[$,]/g, "");
      const parsed = parseFloat(numStr);
      if (!isNaN(parsed)) {
        rawValue = parsed;
        break;
      }
    }
  }

  // Extract entity
  const lower = text.toLowerCase();
  let entity: string | undefined;
  let ticker: string | undefined;
  for (const [key, val] of Object.entries(ENTITY_PATTERNS)) {
    if (lower.includes(key)) {
      entity = val.name;
      ticker = val.ticker;
      break;
    }
  }
  // Also check for ticker symbols like "TSLA", "AAPL"
  if (!ticker) {
    const tickerMatch = text.match(/\b([A-Z]{2,5})\b/);
    if (tickerMatch) {
      const found = Object.values(ENTITY_PATTERNS).find(v => v.ticker === tickerMatch[1]);
      if (found) { entity = found.name; ticker = found.ticker; }
    }
  }

  // Extract metric
  let metric: string | undefined;
  for (const [pat, name] of METRIC_PATTERNS) {
    if (pat.test(text)) { metric = name; break; }
  }

  // Extract period
  let period: string | undefined;
  const periodMatch = text.match(PERIOD_RE);
  if (periodMatch) { period = periodMatch[0]; }

  return { rawValue, entity, ticker, metric, period };
}

type RightTab = "session" | "errors" | "stats";
interface SessionEvent { id: string; time: string; event: string; detail: string; }

function AdvisoryState({ onSelect }: { onSelect: (q: string) => void }) {
  const suggestions = ["What was Tesla's profit margin?","What was Apple's YoY revenue growth?","What was JPMorgan's CET1 ratio?"];
  return (
    <div className="panel border-l-2 border-t-amber">
      <div className="px-3 py-3">
        <div className="flex items-center gap-2 mb-2"><span className="text-t-amber text-[12px]">⚠</span><span className="text-[11px] font-mono font-bold text-t-amber">ADVISORY QUERY DETECTED</span></div>
        <div className="text-[10px] font-mono text-t-secondary mb-3 leading-relaxed">This system verifies <span className="text-t-green">numerical</span> financial outputs, not investment recommendations.</div>
        <div className="flex flex-wrap gap-1">{suggestions.map((q) => (<button key={q} onClick={() => onSelect(q)} className="text-[9px] font-mono px-2 py-1 rounded border border-t-cyan/20 text-t-cyan hover:bg-t-cyan/5 transition-colors">{q}</button>))}</div>
      </div>
    </div>
  );
}

/* Convert legacy QueryResponse to BatchVerificationResult shape for degraded mode */
function legacyToBatch(res: QueryResponse): BatchVerificationResult {
  return {
    claim: { question: res.question, raw_value: res.raw_number, raw_text: res.raw_text, actual_value: null, entity: null, metric: null, period: null, period_struct: null, model_source: null, entity_hint: null, metric_hint: null, period_hint: null, context_text: null, metadata: {}, accounting_basis: null, scope: null, value_role: null, temporal_frame: null },
    verified_value: res.verified_number, correction_log: res.correction_log.map(c => ({ rule: c.rule, before: c.before, after: c.after, description: c.description })),
    evidence: [], calculations: [{ name: "client_dvl", expression: null, inputs: { raw_value: res.raw_number ?? 0 }, output: res.verified_number, passed: true, details: null }],
    trust_score: { label: res.trust_score, score: null, color: res.trust_color, reasons: [], status: "unverified" },
    constraint_result: null, mode: res.mode || "numerical", verified: res.verified ?? false,
  };
}

export default function VerifyPage() {
  const [fullResult, setFullResult] = useState<FullVerificationResult | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [legacyResult, setLegacyResult] = useState<QueryResponse | null>(null);
  const [isDegraded, setIsDegraded] = useState(false);
  const [history, setHistory] = useState<QueryResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [advisoryDetected, setAdvisoryDetected] = useState(false);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [sessionEvents, setSessionEvents] = useState<SessionEvent[]>([]);
  const [rightTab, setRightTab] = useState<RightTab>("session");
  const [stageStatuses, setStageStatuses] = useState<Record<PipelineStageId, StageStatus>>({ claim_parsed: "idle", entity_resolved: "idle", evidence_retrieved: "idle", calculation: "idle", constraints: "idle", result: "idle" });
  const [pastQueries, setPastQueries] = useState<Array<{ question: string; trust: string; latency: string }>>([]);
  const { backendOnline } = useConnection();

  const logEvent = useCallback((event: string, detail: string) => {
    const time = new Date().toLocaleTimeString([], { hour12: false });
    setSessionEvents((events) => [...events, { id: `${Date.now()}-${event}`, time, event, detail }].slice(-50));
  }, []);

  const resetPipeline = useCallback(() => {
    setStageStatuses({ claim_parsed: "idle", entity_resolved: "idle", evidence_retrieved: "idle", calculation: "idle", constraints: "idle", result: "idle" });
  }, []);

  /* Staggered visual reveal of pipeline stages from completed data */
  const revealPipeline = useCallback((result: BatchVerificationResult, batchCR: import("@/lib/api").BatchConstraintResult | null, isDeg: boolean) => {
    const stages: PipelineStageId[] = ["claim_parsed", "entity_resolved", "evidence_retrieved", "calculation", "constraints", "result"];
    const getStatus = (id: PipelineStageId): StageStatus => {
      if (isDeg) {
        if (id === "entity_resolved" || id === "evidence_retrieved" || id === "constraints") return "degraded";
        if (id === "claim_parsed" || id === "calculation" || id === "result") return "complete";
        return "na";
      }
      if (id === "constraints") {
        const cr = result.constraint_result || batchCR;
        return cr ? (cr.status === "consistent" ? "complete" : cr.status === "inconsistent" ? "error" : "na") : "na";
      }
      return "complete";
    };

    stages.forEach((stage, i) => {
      setTimeout(() => {
        setStageStatuses(prev => ({ ...prev, [stage]: getStatus(stage) }));
      }, i * 120);
    });
  }, []);

  const handleSubmit = useCallback(async (question: string) => {
    setAdvisoryDetected(false);
    if (isAdvisoryQuery(question)) { setAdvisoryDetected(true); return; }
    setIsLoading(true); setError(null); setFullResult(null); setLegacyResult(null); setIsDegraded(false); setLatencyMs(null);
    resetPipeline();
    logEvent("QUERY RECEIVED", question);

    const knownDemo = DEMO_NUMS[question];
    try {
      if (backendOnline && !knownDemo) {
        // Full pipeline via /v1/verify/batch
        // Parse numeric value + hints from the user's free-text claim
        const parsed = parseClaimText(question);
        logEvent("CLAIM PARSED", `value=${parsed.rawValue} entity=${parsed.entity || '—'} metric=${parsed.metric || '—'}`);
        try {
          const full = await verifyClaimFull(question, parsed.rawValue, {
            entity: parsed.entity,
            ticker: parsed.ticker,
            metric: parsed.metric,
            period: parsed.period,
          });
          setFullResult(full); setLatencyMs(full.latencyMs); setIsDegraded(false);
          revealPipeline(full.result, full.batchConstraintResult, false);
          logEvent("VERIFICATION COMPLETED", `trust: ${full.result.trust_score.label}`);
          setPastQueries(prev => [{ question, trust: full.result.trust_score.label, latency: `${(full.latencyMs / 1000).toFixed(2)}s` }, ...prev].slice(0, 10));
          // Also save to legacy history for report export
          const legacyRes: QueryResponse = { question, raw_text: null, raw_number: full.result.claim.raw_value, verified_number: full.result.verified_value, correction_log: full.result.correction_log.map(c => ({ rule: c.rule, before: c.before, after: c.after, description: c.description || "" })), trust_score: full.result.trust_score.label, trust_color: full.result.trust_score.color, display_value: full.result.verified_value?.toString() || "—", mode: full.result.mode, verified: full.result.verified };
          setHistory(h => [legacyRes, ...h].slice(0, 20));
          try { addToHistory(legacyRes); } catch { /* ignore */ }
        } catch {
          // Backend online but batch failed — try /query fallback
          try {
            const res = await queryLLM(question);
            if (res.mode === "dvl_only" && res.trust_score === "N/A") { setError("LLM is currently unavailable."); setIsLoading(false); return; }
            setLegacyResult(res); setIsDegraded(false);
            const batchResult = legacyToBatch(res);
            setFullResult({ result: batchResult, batchConstraintResult: null, latencyMs: 0 });
            revealPipeline(batchResult, null, false);
            setHistory(h => [res, ...h].slice(0, 20));
            try { addToHistory(res); } catch { /* ignore */ }
          } catch { setError("Backend request failed. Try a demo query."); }
        }
      } else if (knownDemo !== undefined) {
        // Known demo query
        logEvent("CLAIM PARSED", "fixed demo claim");
        const t0 = performance.now();
        let res: QueryResponse;
        if (backendOnline) {
          try { res = await verifyNumber(question, knownDemo); } catch { res = clientDVL(question, knownDemo); setIsDegraded(true); }
        } else { res = clientDVL(question, knownDemo); setIsDegraded(true); }
        const elapsed = performance.now() - t0;
        setLatencyMs(elapsed); setLegacyResult(res);
        const batchResult = legacyToBatch(res);
        setFullResult({ result: batchResult, batchConstraintResult: null, latencyMs: elapsed });
        revealPipeline(batchResult, null, !backendOnline);
        logEvent("VERIFICATION COMPLETED", res.display_value);
        setHistory(h => [res, ...h].slice(0, 20));
        setPastQueries(prev => [{ question, trust: res.trust_score, latency: `${(elapsed / 1000).toFixed(2)}s` }, ...prev].slice(0, 10));
        try { addToHistory(res); } catch { /* ignore */ }
      } else if (!backendOnline) {
        setError("Backend is offline. Custom queries require the FinVerify API. Try a demo query instead.");
      }
    } catch (e) { setError(e instanceof Error ? e.message : "Unknown error"); }
    finally { setIsLoading(false); }
  }, [backendOnline, logEvent, resetPipeline, revealPipeline]);

  const batchResult = fullResult?.result ?? null;
  const hasResult = batchResult !== null;
  const errorEntries = history.filter(r => r.correction_log.length > 0);
  const totalCorrections = history.reduce((s, r) => s + r.correction_log.length, 0);
  const highTrust = history.filter(r => r.trust_score === "HIGH").length;
  const avgTrust = history.length > 0 ? Math.round((highTrust / history.length) * 100) : 0;

  return (
    <>
      {/* Header bar */}
      <section className="px-3 py-2 max-w-[1920px] mx-auto w-full">
        <div className="panel px-4 py-2.5 flex flex-wrap items-center justify-between gap-3" style={{ borderColor: "rgba(0,255,136,0.12)" }}>
          <div>
            <h1 className="text-[12px] font-mono font-bold text-t-green tracking-wider">DETERMINISTIC VERIFICATION ENGINE</h1>
            <p className="text-[9px] font-mono text-t-secondary">We independently verify numerical claims using public sources, deterministic rules, and financial constraints.</p>
          </div>
          <div className="flex items-center gap-6 text-[10px] font-mono">
            <div className="hidden lg:flex items-center gap-1.5"><span className="text-t-muted">SYSTEM HEALTH</span><span className={`w-[5px] h-[5px] rounded-full ${backendOnline ? "bg-t-green" : "bg-t-red"}`} /><span className={backendOnline ? "text-t-green" : "text-t-red"}>{backendOnline ? "ALL SYSTEMS OPERATIONAL" : "DEGRADED"}</span></div>
          </div>
        </div>
      </section>

      {/* Four-column workbench */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-[22%_30%_26%_22%] gap-2 px-3 pb-3 max-w-[1920px] mx-auto w-full" style={{ minHeight: "calc(100vh - 130px)" }}>

        {/* ── Column 1: INPUT ── */}
        <div className="flex flex-col min-h-0">
          <QueryInput onSubmit={handleSubmit} isLoading={isLoading} latencyMs={latencyMs} />
        </div>

        {/* ── Column 2: VERIFICATION PIPELINE ── */}
        <div className="flex flex-col gap-2 min-h-0 overflow-y-auto">
          {advisoryDetected && <AdvisoryState onSelect={(q) => { setAdvisoryDetected(false); handleSubmit(q); }} />}

          <VerificationPipelineStrip stageStatuses={stageStatuses} activeStage={isLoading ? "claim_parsed" : null} />

          {/* Pipeline stage panels */}
          {hasResult && (
            <div className="space-y-2">
              {stageStatuses.claim_parsed !== "idle" && <ClaimParsedPanel claim={batchResult.claim} isDegraded={isDegraded} />}
              {stageStatuses.entity_resolved !== "idle" && <EntityResolvedPanel entity={batchResult.claim.entity} isDegraded={isDegraded} />}
              {stageStatuses.evidence_retrieved !== "idle" && <EvidenceRetrievedPanel evidence={batchResult.evidence} isDegraded={isDegraded} />}
              {stageStatuses.calculation !== "idle" && <CalculationPanel calculations={batchResult.calculations} correctionLog={batchResult.correction_log} isDegraded={isDegraded} />}
              {stageStatuses.constraints !== "idle" && <ConstraintsPanel constraintResult={batchResult.constraint_result} batchConstraintResult={fullResult?.batchConstraintResult ?? null} isDegraded={isDegraded} />}
              {stageStatuses.result !== "idle" && <TerminalPanel result={batchResult} latencyMs={latencyMs} isLoading={false} isDegraded={isDegraded} />}
            </div>
          )}

          {/* Loading state */}
          {isLoading && !hasResult && (
            <div className="panel p-6 text-center"><div className="text-t-amber text-[11px] font-mono font-bold animate-pulse">VERIFICATION IN PROGRESS...</div><div className="text-t-muted text-[9px] font-mono mt-1">Querying verification engine</div></div>
          )}

          {/* Idle state */}
          {!hasResult && !isLoading && !advisoryDetected && (
            <div className="panel p-6 text-center"><div className="text-t-muted text-[10px] font-mono">Enter a financial claim above to begin verification</div></div>
          )}

          {error && <div className="panel p-2 border-l-2 border-t-red"><div className="text-t-red text-[10px] font-mono">{error}</div></div>}

          {history.length > 0 && <div className="flex justify-end"><DVLReport entries={history} /></div>}
        </div>

        {/* ── Column 3: VERIFICATION SUMMARY ── */}
        <div className="flex flex-col gap-2 min-h-0 overflow-y-auto">
          {hasResult ? (
            <TrustScore result={batchResult} />
          ) : (
            <div className="panel flex-1"><div className="panel-header"><span className="label">VERIFICATION SUMMARY</span></div><div className="p-4 text-center text-t-muted text-[10px] font-mono">Run a verification to see summary</div></div>
          )}

          {/* Quick Actions */}
          <div className="panel">
            <div className="panel-header"><span className="label text-t-muted">QUICK ACTIONS</span></div>
            <div className="px-3 py-2 grid grid-cols-2 gap-2">
              <button disabled className="text-[9px] font-mono px-2 py-1.5 rounded border border-t-border text-t-muted/40 cursor-not-allowed">Analyze 10-K Filing</button>
              <button disabled className="text-[9px] font-mono px-2 py-1.5 rounded border border-t-border text-t-muted/40 cursor-not-allowed">Extract from PDF</button>
              <button disabled className="text-[9px] font-mono px-2 py-1.5 rounded border border-t-border text-t-muted/40 cursor-not-allowed">Compare Periods</button>
              <button onClick={() => { setFullResult(null); setLegacyResult(null); setError(null); resetPipeline(); setLatencyMs(null); setIsDegraded(false); }} className="text-[9px] font-mono px-2 py-1.5 rounded border border-t-green/30 text-t-green hover:bg-t-green/5 transition-colors">New Verification</button>
            </div>
          </div>
        </div>

        {/* ── Column 4: SESSION ACTIVITY ── */}
        <div className="flex flex-col min-h-0">
          <div className="panel flex-1 flex flex-col min-h-0">
            <div className="flex border-b border-t-border">
              {(["session","errors","stats"] as RightTab[]).map((tab) => (
                <button key={tab} onClick={() => setRightTab(tab)} className={`flex-1 py-1.5 text-[10px] font-mono font-bold uppercase tracking-wider transition-colors ${rightTab === tab ? "text-t-green border-b border-t-green bg-white/[0.02]" : "text-t-muted hover:text-t-secondary"}`}>
                  {tab === "session" ? "LIVE LOG" : tab === "errors" ? `EVENTS` : "ERRORS"}
                  {tab === "errors" && errorEntries.length > 0 && <span className="ml-1 text-t-amber">({errorEntries.length})</span>}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto p-2">
              {rightTab === "session" && (
                <div className="space-y-0.5">
                  {sessionEvents.length === 0 && <div className="text-t-muted text-[10px] font-mono text-center py-6">No terminal events yet — execute a query to begin</div>}
                  {sessionEvents.map((entry) => (
                    <div key={entry.id} className="animate-fade-in flex items-start gap-2 px-1 py-1 border-b border-t-border/20">
                      <span className="text-[8px] text-t-muted font-mono shrink-0">[{entry.time}]</span>
                      <span className="w-[4px] h-[4px] rounded-full bg-t-green shrink-0 mt-1 live-pulse" />
                      <span className="text-[8px] text-t-green font-mono shrink-0">{entry.event}</span>
                      <span className="text-[8px] text-t-secondary font-mono truncate">{entry.detail}</span>
                    </div>
                  ))}
                </div>
              )}
              {rightTab === "errors" && (
                <div className="space-y-0.5">
                  {errorEntries.length === 0 && <div className="text-t-muted text-[10px] font-mono text-center py-6">No corrections applied yet</div>}
                  {errorEntries.map((h, i) => (
                    <div key={i} className="px-2 py-1.5 flex items-center gap-2 text-[9px] font-mono">
                      <span className="w-[5px] h-[5px] rounded-full shrink-0 bg-t-amber" />
                      <span className="text-t-secondary truncate flex-1">{h.question.length > 30 ? h.question.slice(0, 30) + "..." : h.question}</span>
                      <span className="text-t-amber shrink-0">{h.correction_log.length} fix{h.correction_log.length > 1 ? "es" : ""}</span>
                    </div>
                  ))}
                </div>
              )}
              {rightTab === "stats" && (
                <div className="space-y-2 pt-2">
                  <div className="panel p-3 text-center"><div className="text-xl font-bold font-mono text-t-blue">{history.length}</div><div className="text-[9px] text-t-muted font-mono uppercase tracking-wider">Queries</div></div>
                  <div className="panel p-3 text-center"><div className="text-xl font-bold font-mono text-t-amber">{totalCorrections}</div><div className="text-[9px] text-t-muted font-mono uppercase tracking-wider">Corrections</div></div>
                  <div className="panel p-3 text-center"><div className="text-xl font-bold font-mono text-t-green">{avgTrust}%</div><div className="text-[9px] text-t-muted font-mono uppercase tracking-wider">High Trust</div></div>
                </div>
              )}
            </div>

            {/* Past Queries */}
            {pastQueries.length > 0 && (
              <div className="border-t border-t-border p-2">
                <div className="text-[9px] font-mono text-t-muted uppercase tracking-wider mb-1">PAST QUERIES (THIS SESSION)</div>
                <div className="space-y-0.5 max-h-[120px] overflow-y-auto">
                  {pastQueries.map((pq, i) => (
                    <div key={i} className="flex items-center gap-2 text-[8px] font-mono">
                      <span className="text-t-secondary truncate flex-1">{pq.question.slice(0, 35)}...</span>
                      <span className="text-t-muted shrink-0">{pq.latency}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
