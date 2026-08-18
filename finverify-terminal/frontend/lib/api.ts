/**
 * FinVerify Terminal — API Client
 * ================================
 * Typed fetch wrappers for the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://aadi2026-finverify-api.hf.space";
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || API_BASE.replace(/^http/, "ws");

/* ─── Types ─── */

export interface CorrectionEntry {
  rule: string;
  before: number;
  after: number;
  description: string;
}

export interface QueryResponse {
  question: string;
  raw_text: string | null;
  raw_number: number | null;
  verified_number: number | null;
  correction_log: CorrectionEntry[];
  trust_score: string;
  trust_color: string;
  display_value: string;
  mode?: string;
  verified?: boolean;
}

export interface SampleQuery {
  question: string;
  actual: number | null;
  category: string | null;
}

export interface HealthStatus {
  status: string;
  model: string;
}

export interface MarketQuote {
  symbol: string;
  price: number;
  prev_close: number;
  change: number;
  change_pct: number;
  volume: number;
  market_cap: number;
  stale?: boolean;
  display_name?: string;
}

export interface MetricResult {
  symbol: string;
  metric: string;
  label: string;
  raw_value: number | null;
  question_text: string;
  verified_value: number | null;
  correction_log: CorrectionEntry[];
  trust_score: string;
  trust_color: string;
  stale?: boolean;
}

/* ─── Batch Verify Types (wired to /v1/verify/batch) ─── */

export interface BatchClaimEntity {
  name: string;
  ticker: string | null;
  cik: string | null;
  lei: string | null;
}

export interface BatchClaimMetric {
  name: string;
  canonical_name: string | null;
  unit: string | null;
}

export interface BatchEvidenceSource {
  name: string;
  kind: string;
  authority: number;
  url: string | null;
  retrieved_at: string | null;
}

export interface BatchEvidence {
  source: BatchEvidenceSource;
  claim: string;
  value: number | null;
  excerpt: string | null;
  period: string | null;
  locator: string | null;
  entity: string | null;
}

export interface BatchCalculation {
  name: string;
  expression: string | null;
  inputs: Record<string, unknown>;
  output: number | null;
  passed: boolean;
  details: string | null;
}

export interface BatchTrustScore {
  label: string;
  score: number | null;
  color: string;
  reasons: string[];
  status: string; // "verified" | "contradicted" | "unverified" | "pending" | "error"
}

export interface BatchCorrectionEntry {
  rule: string;
  before: number;
  after: number;
  description?: string;
}

export interface BatchClaim {
  question: string;
  raw_value: number | null;
  raw_text: string | null;
  actual_value: number | null;
  entity: BatchClaimEntity | null;
  metric: BatchClaimMetric | null;
  period: string | null;
  period_struct: unknown | null;
  model_source: string | null;
  entity_hint: string | null;
  metric_hint: string | null;
  period_hint: string | null;
  context_text: string | null;
  metadata: Record<string, unknown>;
  accounting_basis: string | null;
  scope: string | null;
  value_role: string | null;
  temporal_frame: string | null;
}

export interface BatchConstraintOutcome {
  target: string;
  status: string; // "verified" | "violation" | "indeterminate" | "derivable" | "not_applicable"
  formula: string;
  dependencies: Record<string, number>;
  expected?: number | null;
  actual?: number | null;
  reason?: string | null;
}

export interface BatchConstraintResult {
  status: string; // "consistent" | "inconsistent" | "indeterminate" | "not_evaluated"
  coverage: {
    loaded: number;
    verified: number;
    violated: number;
    indeterminate: number;
    derivable: number;
    not_applicable: number;
  };
  consistent: boolean | null;
  outcomes: BatchConstraintOutcome[];
  violations: Array<{
    metric: string;
    expected: number;
    actual: number;
    formula: string;
    dependencies: Record<string, number>;
  }>;
  indeterminate: string[];
  indeterminate_reasons: Record<string, string>;
}

export interface BatchVerificationResult {
  claim: BatchClaim;
  verified_value: number | null;
  correction_log: BatchCorrectionEntry[];
  evidence: BatchEvidence[];
  calculations: BatchCalculation[];
  trust_score: BatchTrustScore;
  constraint_result: BatchConstraintResult | null;
  mode: string;
  verified: boolean;
}

export interface BatchVerifyResponse {
  results: BatchVerificationResult[];
  constraint_result: BatchConstraintResult | null;
}

/**
 * Full verification result returned by verifyClaimFull().
 * Contains the single result plus the batch-level constraint_result.
 */
export interface FullVerificationResult {
  result: BatchVerificationResult;
  batchConstraintResult: BatchConstraintResult | null;
  latencyMs: number;
}

/* ─── DVL API Calls ─── */

export async function queryLLM(
  question: string,
  context?: string
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, context }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Query failed (${res.status}): ${err}`);
  }
  return res.json();
}

export async function verifyNumber(
  question: string,
  rawNumber: number
): Promise<QueryResponse> {
  const res = await fetch(`${API_BASE}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, raw_number: rawNumber }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Verify failed (${res.status}): ${err}`);
  }
  return res.json();
}

/**
 * Full claim verification via POST /v1/verify/batch with a single claim.
 * Returns the rich VerificationResult plus batch-level constraint info.
 * Measures real frontend round-trip latency via performance.now().
 */
export async function verifyClaimFull(
  question: string,
  rawValue: number,
  opts?: {
    entity?: string;
    ticker?: string;
    metric?: string;
    period?: string;
  }
): Promise<FullVerificationResult> {
  const t0 = performance.now();
  const res = await fetch(`${API_BASE}/v1/verify/batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      claims: [
        {
          question,
          raw_value: rawValue,
          entity: opts?.entity || null,
          ticker: opts?.ticker || null,
          metric: opts?.metric || null,
          period: opts?.period || null,
        },
      ],
      include_constraints: true,
    }),
  });
  const latencyMs = performance.now() - t0;

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Batch verify failed (${res.status}): ${err}`);
  }

  const data: BatchVerifyResponse = await res.json();
  if (!data.results || data.results.length === 0) {
    throw new Error("Batch verify returned no results");
  }

  return {
    result: data.results[0],
    batchConstraintResult: data.constraint_result,
    latencyMs,
  };
}

export async function checkHealth(): Promise<HealthStatus> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: controller.signal });
    if (!res.ok) throw new Error("Backend unreachable");
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

export async function getSampleQueries(): Promise<SampleQuery[]> {
  const res = await fetch(`${API_BASE}/sample-queries`);
  if (!res.ok) throw new Error("Failed to fetch sample queries");
  return res.json();
}

/* ─── Market API Calls ─── */

export async function getMarketQuotes(symbols?: string[]): Promise<MarketQuote[]> {
  const params = symbols ? `?symbols=${symbols.join(",")}` : "";
  const res = await fetch(`${API_BASE}/market/quotes${params}`);
  if (!res.ok) throw new Error("Failed to fetch quotes");
  return res.json();
}

export async function getMarketIndices(): Promise<MarketQuote[]> {
  const res = await fetch(`${API_BASE}/market/indices`);
  if (!res.ok) throw new Error("Failed to fetch indices");
  return res.json();
}

export async function getVerifiedMetric(symbol: string, metric: string): Promise<MetricResult> {
  const res = await fetch(`${API_BASE}/market/verified-metrics?symbol=${symbol}&metric=${metric}`);
  if (!res.ok) throw new Error("Failed to fetch metric");
  return res.json();
}

export async function getAllMetrics(symbol: string): Promise<MetricResult[]> {
  const res = await fetch(`${API_BASE}/market/all-metrics?symbol=${symbol}`);
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

/* ─── Fundamentals (SEC EDGAR) ─── */

export interface FundamentalMetric {
  ticker: string;
  metric_name: string;
  raw_value: number;
  verified_value: number;
  period: string;
  filing_date: string;
  source_url: string;
  dvl_trust: string;
  dvl_color: string;
  dvl_rule: string | null;
  correction_log?: Array<{ rule: string; before: number; after: number }>;
}

export interface FundamentalsResponse {
  ticker: string;
  source: string;
  metrics_count: number;
  metrics: FundamentalMetric[];
}

export async function getFundamentals(ticker: string): Promise<FundamentalsResponse> {
  const res = await fetch(`${API_BASE}/v1/fundamentals/${ticker.toUpperCase()}`);
  if (!res.ok) throw new Error(`Failed to fetch fundamentals for ${ticker}`);
  return res.json();
}

/* ─── Earnings Verification (Transcripts) ─── */

export interface EarningsClaim {
  sentence: string;
  raw_value: number;
  claim_type: string;
  match: string;
  question: string;
  verified_value: number;
  dvl_rule: string | null;
  dvl_analysis: string;
  trust_score: string;
  trust_color: string;
  flagged: boolean;
  bps_original?: number;
  scale_label?: string;
}

export interface EarningsReport {
  ticker: string;
  total_claims: number;
  flagged_count: number;
  flag_rate: number;
  trust_breakdown: {
    high: number;
    medium: number;
    low: number;
  };
  flags: EarningsClaim[];
  all_claims: EarningsClaim[];
  source: string;
  generated_at: string;
}

export async function getEarningsVerification(ticker: string): Promise<EarningsReport> {
  const res = await fetch(`${API_BASE}/v1/earnings/${ticker.toUpperCase()}`);
  if (!res.ok) throw new Error(`Failed to fetch earnings for ${ticker}`);
  return res.json();
}

/* ─── WebSocket ─── */

export function createMarketWebSocket(
  onMessage: (quotes: MarketQuote[]) => void,
  onError?: (err: Event) => void,
): WebSocket | null {
  try {
    const ws = new WebSocket(`${WS_BASE}/ws/market`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (Array.isArray(data)) {
          onMessage(data);
        }
      } catch { /* ignore parse errors */ }
    };
    ws.onerror = (e) => onError?.(e);
    return ws;
  } catch {
    return null;
  }
}

/* ─── Query History (Session 12A — Supabase persistence) ─── */

export interface HistoryRecord {
  id?: string;
  user_id: string;
  question: string;
  raw_value: number | null;
  verified_value: number | null;
  trust: string;
  display_value: string;
  correction_log: CorrectionEntry[];
  timestamp?: string;
}

export async function saveToHistory(
  userId: string,
  result: QueryResponse,
): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/v1/history`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: userId,
        question: result.question,
        raw_value: result.raw_number,
        verified_value: result.verified_number,
        trust: result.trust_score,
        display_value: result.display_value,
        correction_log: result.correction_log,
      }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    return data.saved === true;
  } catch {
    return false;
  }
}

export async function getHistory(
  userId: string,
  limit: number = 20,
  trustFilter?: string,
): Promise<HistoryRecord[]> {
  try {
    const params = new URLSearchParams({ limit: String(limit) });
    if (trustFilter && trustFilter !== "ALL") {
      params.set("trust", trustFilter);
    }
    const res = await fetch(`${API_BASE}/v1/history/${userId}?${params}`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.entries || [];
  } catch {
    return [];
  }
}

export async function clearHistoryRemote(userId: string): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/v1/history/${userId}`, {
      method: "DELETE",
    });
    if (!res.ok) return false;
    const data = await res.json();
    return data.cleared === true;
  } catch {
    return false;
  }
}
