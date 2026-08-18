import { useState } from "react";
import type { TrustScore, VerifiedClaim, ResolvedSemanticState } from "@finverify/core";
import {
  formatValue,
  trustIcon,
  trustLabel,
  trustPalette,
  claimSemanticState,
  deriveSemanticOverall,
  formatSemanticSummary,
  formatClaimSetShareText,
  semanticExplanation,
  semanticIcon,
  semanticLabel,
  semanticPalette,
} from "@finverify/core";

interface Props {
  claims: VerifiedClaim[];
}

/* ------------------------------------------------------------------ *
 * Shared status derivation — single source of truth for "what's the
 * headline state of this claim set", used by both VerificationCard and
 * InlineBadge so the two never disagree. Pure derivation over data the
 * engine has already produced; no engine/session/transport calls here.
 * (Unchanged — presentation redesign only touches what's rendered below.)
 * ------------------------------------------------------------------ */

export type OverallStatus =
  | { kind: "empty" }
  | { kind: "pending"; done: number; total: number; bestKnown: TrustScore | null }
  | { kind: "hard-error"; total: number }
  | { kind: "trust"; trust: TrustScore; hasOffline: boolean; unavailable: number; total: number };

function worstTrustOf(verified: VerifiedClaim[]): TrustScore | null {
  const corroborated = verified.filter((c) => c.result?.verification_status !== "unverified" && !c.error);
  if (corroborated.length === 0) return null;
  if (corroborated.some((c) => c.result?.trust_score === "LOW")) return "LOW";
  if (corroborated.some((c) => c.result?.trust_score === "MEDIUM")) return "MEDIUM";
  return "HIGH";
}

export function deriveOverallStatus(claims: VerifiedClaim[]): OverallStatus {
  if (claims.length === 0) return { kind: "empty" };

  const pending = claims.filter((c) => c.status === "pending");
  const hardErrors = claims.filter((c) => c.status === "error");
  const verified = claims.filter((c) => c.status === "verified" && c.result);

  if (pending.length > 0) {
    return {
      kind: "pending",
      done: claims.length - pending.length,
      total: claims.length,
      bestKnown: worstTrustOf(verified),
    };
  }
  if (hardErrors.length === claims.length) {
    return { kind: "hard-error", total: claims.length };
  }
  return {
    kind: "trust",
    trust: worstTrustOf(verified) ?? "N/A",
    hasOffline: verified.some((c) => !!c.error),
    unavailable: hardErrors.length,
    total: claims.length,
  };
}

/* ------------------------------------------------------------------ *
 * Analyst summary — a second pure aggregation over the same already-
 * verified data, in the same spirit as deriveOverallStatus above. This
 * only rolls up numbers that already exist on each claim (trust_score,
 * correction_applied, error) into report-level stats; it does not
 * recompute, re-verify, or touch anything the engine produced.
 * ------------------------------------------------------------------ */

export interface AnalystSummary {
  total: number;
  verifiedClean: number;
  corrected: number;
  offline: number;
  unavailable: number;
  corroborated: VerifiedClaim[];
  contradictedCount: number;
  uncorroboratedCount: number;
  confidencePercent: number;
}

function trustWeight(t: TrustScore): number {
  if (t === "HIGH") return 100;
  if (t === "MEDIUM") return 60;
  return 20; // LOW
}

function confidenceWord(pct: number): "High" | "Moderate" | "Low" {
  if (pct >= 85) return "High";
  if (pct >= 55) return "Moderate";
  return "Low";
}

export function deriveAnalystSummary(claims: VerifiedClaim[]): AnalystSummary {
  const verified = claims.filter((c) => c.status === "verified" && c.result);
  const corroborated = verified.filter((c) => c.result?.verification_status !== "unverified" && !c.error);
  const contradictedCount = corroborated.filter((c) => c.result?.verification_status === "contradicted").length;
  const uncorroboratedCount = verified.filter((c) => c.result?.verification_status === "unverified").length;
  const corrected = corroborated.filter((c) => !!c.result?.correction_applied).length;
  const offline = verified.filter((c) => !!c.error).length;
  const unavailable = claims.filter((c) => c.status === "error").length;
  const confidencePercent = corroborated.length
    ? Math.round(corroborated.reduce((sum, c) => sum + (c.result!.confidence != null ? c.result!.confidence * 100 : trustWeight(c.result!.trust_score)), 0) / corroborated.length)
    : 0;
  // "Matched verification exactly" must exclude contradicted claims — a
  // contradiction is corroborated (independent evidence exists) but is
  // never a clean match, regardless of whether a correction was also
  // applied. Derived directly rather than via `corroborated.length -
  // corrected`, which incorrectly let a contradicted-and-uncorrected
  // claim count as verifiedClean.
  const verifiedClean = corroborated.filter(
    (c) => c.result?.verification_status !== "contradicted" && !c.result?.correction_applied
  ).length;

  return {
    total: claims.length,
    verifiedClean,
    corrected,
    offline,
    unavailable,
    corroborated,
    contradictedCount,
    uncorroboratedCount,
    confidencePercent,
  };
}

/* A "material" correction is one where the normalized value actually
 * moved the number in a way that could change how it reads — as opposed
 * to a cosmetic formatting fix (e.g. "391" -> "391.0B"). Same threshold
 * the original card used for showing the delta at all. */
function isMaterialCorrection(claim: VerifiedClaim): boolean {
  return !!claim.result?.correction_applied && Math.abs(claim.result.delta_pct) > 0.05;
}

/* ------------------------------------------------------------------ *
 * Primitives
 * ------------------------------------------------------------------ */

function Ring({ color, size = "fv-h-3 fv-w-3" }: { color: string; size?: string }) {
  return (
    <span
      className={`${size} fv-shrink-0 fv-rounded-full fv-border-2 fv-animate-spin motion-reduce:fv-animate-none`}
      style={{ borderColor: color, borderTopColor: "transparent" }}
      aria-hidden="true"
    />
  );
}

/* Hero confidence stat — a terminal-style segmented gauge paired with a
 * large tabular-nums percentage, rather than a circular "AI dashboard"
 * donut. This is the number a reader should land on first; everything
 * else on the card supports it. */
function ConfidenceMeter({ percent, trust }: { percent: number; trust: TrustScore | "N/A" }) {
  const filled = Math.round((percent / 100) * 14);
  const color = trustPalette(trust === "N/A" ? "N/A" : trust).text;
  return (
    <div className="fv-flex fv-items-center fv-gap-4">
      <div className="fv-flex fv-shrink-0 fv-items-baseline fv-gap-0.5" style={{ color }}>
        <span className="fv-font-mono fv-text-[26px] fv-font-bold fv-leading-none fv-tabular-nums">{percent}</span>
        <span className="fv-text-xs fv-font-bold">%</span>
      </div>
      <div className="fv-flex fv-min-w-0 fv-flex-1 fv-flex-col fv-gap-1.5">
        <div className="fv-flex fv-items-center fv-gap-[3px]" aria-hidden="true">
          {Array.from({ length: 14 }).map((_, i) => (
            <span
              key={i}
              className="fv-h-2.5 fv-flex-1 fv-rounded-sm fv-transition-colors fv-duration-300"
              style={{ background: i < filled ? color : "#1e1e1e" }}
            />
          ))}
        </div>
        <span className="fv-text-[10px] fv-font-bold fv-uppercase fv-tracking-[0.14em]" style={{ color }}>
          {confidenceWord(percent)} confidence
        </span>
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="fv-mb-2 fv-flex fv-items-center fv-gap-2 fv-text-[10px] fv-font-bold fv-uppercase fv-tracking-[0.14em] fv-text-t-muted">
      {children}
    </div>
  );
}

/* A small pill for a single claim's semantic finding — the primary,
 * evidence-first signal, distinct from (and rendered ahead of) the
 * trust-score detail used elsewhere on the card. */
function SemanticBadge({ state }: { state: ResolvedSemanticState }) {
  const palette = semanticPalette(state);
  return (
    <span
      className="fv-inline-flex fv-shrink-0 fv-items-center fv-gap-1 fv-rounded-full fv-px-1.5 fv-py-0.5 fv-text-[9px] fv-font-bold fv-tracking-wide"
      style={{ background: palette.bg, color: palette.text, border: `1px solid ${palette.border}` }}
    >
      {semanticIcon(state)} {semanticLabel(state)}
    </span>
  );
}

/* ------------------------------------------------------------------ *
 * Claim breakdown — one row per claim, each with its own independent
 * VERIFIED / CONTRADICTED / UNVERIFIED / VERIFICATION UNAVAILABLE
 * finding. This is the card's evidence-first hero section: unrelated
 * claims are never merged into a single score here.
 * ------------------------------------------------------------------ */

function ClaimBreakdownRow({ claim }: { claim: VerifiedClaim }) {
  const state = claimSemanticState(claim);

  if (state === "pending" || state === "cancelled") {
    return (
      <li className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-py-2 fv-text-t-secondary">
        <span className="fv-truncate fv-text-[11.5px]">{claim.match}</span>
        {state === "pending" ? (
          <Ring color="#888888" />
        ) : (
          <span aria-hidden="true">⊘</span>
        )}
      </li>
    );
  }

  if (state === "unavailable") {
    return (
      <li className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-py-2" title={claim.error ?? "Verification failed"}>
        <span className="fv-truncate fv-text-[11.5px] fv-text-t-primary">{claim.match}</span>
        <SemanticBadge state="unavailable" />
      </li>
    );
  }

  const result = claim.result!;
  return (
    <li className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-py-2" title={semanticExplanation(state) ?? undefined}>
      <span className="fv-truncate fv-text-[11.5px] fv-text-t-primary">{claim.match}</span>
      <div className="fv-flex fv-shrink-0 fv-items-center fv-gap-2">
        <span className="fv-font-mono fv-text-[10px] fv-tabular-nums fv-text-t-secondary">
          {formatValue(result.raw_value, result.question)}
          {/* CONTRADICTED must show the actual primary-source evidence
              value, never re-echo the claim as if it were independent
              confirmation. If the backend didn't attach an evidence_value
              (e.g. it couldn't be positively tied to this claim), fall
              back to the textual finding instead of inventing a number. */}
          {state === "contradicted" && result.evidence_value != null && (
            <>
              <span aria-hidden="true"> → </span>
              <span style={{ color: semanticPalette(state).text }}>{formatValue(result.evidence_value, result.question)}</span>
            </>
          )}
        </span>
        <SemanticBadge state={state} />
      </div>
    </li>
  );
}

/* ------------------------------------------------------------------ *
 * Main card
 * ------------------------------------------------------------------ */

export function VerificationCard({ claims }: Props) {
  const overall = deriveOverallStatus(claims);
  const semantic = deriveSemanticOverall(claims);
  const [showRaw, setShowRaw] = useState(false);
  const [showAllMetrics, setShowAllMetrics] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  if (semantic.kind === "empty") {
    return (
      <div className="fv-mt-2 fv-w-[560px] fv-max-w-[92vw] fv-rounded-xl fv-border fv-border-t-border fv-bg-t-bg fv-px-4 fv-py-4 fv-font-mono fv-text-xs fv-text-t-secondary">
        No financial claims detected in this response.
      </div>
    );
  }

  // Semantic state (VERIFIED/CONTRADICTED/UNVERIFIED/VERIFICATION
  // UNAVAILABLE) drives the header, border, and pill — the evidence-first
  // finding is the headline. Trust-score-derived `overall` is kept only
  // for the confidence meter, shown further down as secondary detail,
  // never the centerpiece.
  const palette =
    semantic.kind === "resolved" && semantic.headline
      ? semanticPalette(semantic.headline)
      : semantic.kind === "unavailable"
        ? semanticPalette("unavailable")
        : trustPalette(overall.kind === "pending" ? (overall.bestKnown ?? "N/A") : "N/A");

  const summary = deriveAnalystSummary(claims);
  const verifiedClaims = claims.filter((c) => c.status === "verified" && c.result);
  const materialCorrections = verifiedClaims.filter(isMaterialCorrection);
  const normalizedOnly = verifiedClaims.filter(
    (c) => c.result?.correction_applied && !isMaterialCorrection(c)
  );
  const flaggedForReview = verifiedClaims.filter(
    (c) => c.result?.verification_status === "contradicted" || isMaterialCorrection(c)
  );
  /* Claims flagged for review purely because the verifier couldn't
   * corroborate them (trust_score === "LOW") *without* a material
   * correction being involved — e.g. no matching evidence tier, so the
   * value reads back as "matched" the model's own number exactly, but
   * that "match" was never checked against anything external. Without
   * this, a response can show a low overall confidence percentage while
   * the analyst-summary paragraph says nothing about why — see the
   * comment at the summary's trailing sentence below. */
  const lowConfidenceUncorrected = summary.uncorroboratedCount;
  const hardErrorClaims = claims.filter((c) => c.status === "error");
  const METRIC_PREVIEW_COUNT = 6;
  const visibleMetrics = showAllMetrics ? verifiedClaims : verifiedClaims.slice(0, METRIC_PREVIEW_COUNT);
  const remainingMetricsCount = verifiedClaims.length - METRIC_PREVIEW_COUNT;

  async function handleCopy() {
    const text = formatClaimSetShareText(claims);
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
    setTimeout(() => setCopyState("idle"), 1800);
  }

  return (
    <div
      className="fv-mt-2 fv-w-[560px] fv-max-w-[92vw] fv-overflow-hidden fv-rounded-xl fv-border fv-font-mono fv-text-xs fv-shadow-[0_12px_40px_rgba(0,0,0,0.45)] fv-animate-fade-in motion-reduce:fv-animate-none"
      style={{ borderColor: palette.border, background: "#0a0a0a" }}
    >
      {/* Header — semantic state (VERIFIED/CONTRADICTED/UNVERIFIED/
          VERIFICATION UNAVAILABLE) is the authoritative headline; trust
          score never overrides it here. ---------------------------- */}
      <div className="fv-flex fv-items-center fv-justify-between fv-gap-3 fv-border-b fv-border-t-border fv-px-4 fv-py-3.5">
        <div className="fv-flex fv-min-w-0 fv-items-center fv-gap-3">
          <span
            className="fv-flex fv-h-7 fv-w-7 fv-shrink-0 fv-items-center fv-justify-center fv-rounded-full fv-text-xs fv-font-bold"
            style={{ background: palette.bg, color: palette.text }}
            aria-hidden="true"
          >
            {semantic.kind === "pending" ? (
              <Ring color={palette.text} size="fv-h-3.5 fv-w-3.5" />
            ) : semantic.kind === "unavailable" ? (
              "!"
            ) : (
              semanticIcon(semantic.headline!)
            )}
          </span>
          <div className="fv-min-w-0">
            <div className="fv-truncate fv-text-[13px] fv-font-bold fv-leading-tight fv-tracking-[0.01em] fv-text-t-primary">
              FinVerify Analysis
            </div>
            <div className="fv-truncate fv-text-[10.5px] fv-leading-tight fv-text-t-secondary">
              {semantic.kind === "pending"
                ? `Verifying claim ${semantic.summary.total - semantic.summary.pending} of ${semantic.summary.total}…`
                : semantic.kind === "unavailable"
                  ? "Verification unavailable"
                  : `${claims.length} claim${claims.length === 1 ? "" : "s"} reviewed`}
            </div>
          </div>
        </div>
        <span
          className="fv-shrink-0 fv-rounded-full fv-px-3 fv-py-1 fv-text-[10px] fv-font-bold fv-tracking-wide"
          style={{ background: palette.bg, color: palette.text }}
        >
          {semantic.kind === "pending"
            ? "IN PROGRESS"
            : semantic.kind === "unavailable"
              ? "UNAVAILABLE"
              : semanticLabel(semantic.headline!)}
        </span>
      </div>

      {/* Progress bar — only while claims are still resolving -------- */}
      {semantic.kind === "pending" && (
        <div className="fv-h-0.5 fv-w-full fv-bg-t-border" aria-hidden="true">
          <div
            className="fv-h-full fv-transition-all fv-duration-300 motion-reduce:fv-transition-none"
            style={{
              width: `${((semantic.summary.total - semantic.summary.pending) / semantic.summary.total) * 100}%`,
              background: overall.kind === "pending" && overall.bestKnown ? trustPalette(overall.bestKnown).text : "#888888",
            }}
          />
        </div>
      )}

      {/* VERIFICATION UNAVAILABLE — a technical failure (no result at
          all). Kept visually and textually distinct from UNVERIFIED,
          which means the check succeeded but found no independent
          evidence. -------------------------------------------------- */}
      {semantic.kind === "unavailable" && (
        <div className="fv-border-b fv-border-t-border fv-bg-t-surface fv-px-4 fv-py-3.5">
          <div className="fv-text-[13px] fv-font-bold" style={{ color: palette.text }}>
            VERIFICATION UNAVAILABLE
          </div>
          <p className="fv-mt-1 fv-text-[11px] fv-leading-relaxed fv-text-t-secondary">
            {semanticExplanation("unavailable")}
          </p>
        </div>
      )}

      {/* Claim breakdown — the evidence-first hero. Each claim keeps its
          own independent VERIFIED / CONTRADICTED / UNVERIFIED /
          VERIFICATION UNAVAILABLE finding; nothing here is blended into
          a single score. ---------------------------------------------- */}
      {semantic.kind === "resolved" && (
        <div className="fv-border-b fv-border-t-border fv-bg-t-surface fv-px-4 fv-py-3.5">
          {semantic.summary.total > 1 && (
            <div className="fv-mb-2 fv-text-[10.5px] fv-font-semibold fv-tracking-wide fv-text-t-secondary">
              {formatSemanticSummary(semantic.summary)}
            </div>
          )}
          <ul className="fv-divide-y fv-divide-t-border">
            {claims.map((claim) => (
              <ClaimBreakdownRow key={claim.id} claim={claim} />
            ))}
          </ul>
          {semantic.headline === "unverified" && semantic.summary.contradicted === 0 && (
            <p className="fv-mt-2 fv-text-[10.5px] fv-leading-relaxed fv-text-t-secondary">
              {semanticExplanation("unverified")}
            </p>
          )}
        </div>
      )}

      {/* Hero confidence — secondary supporting detail underneath the
          semantic breakdown above, never the primary finding. Only
          rendered once corroborated evidence actually exists — no
          confidence is manufactured for claims that were never checked
          against anything external. */}
      {overall.kind === "trust" && summary.corroborated.length > 0 && (
        <div className="fv-border-b fv-border-t-border fv-px-4 fv-py-3">
          <div className="fv-mb-1.5 fv-text-[9.5px] fv-font-bold fv-uppercase fv-tracking-[0.14em] fv-text-t-muted">
            Trust score (secondary — not a verification finding)
          </div>
          <ConfidenceMeter percent={summary.confidencePercent} trust={overall.trust} />
        </div>
      )}

      {/* Share / export — an explicit user action, never automatic, and
          built only from fields the API actually returned. ----------- */}
      {semantic.kind !== "pending" && (
        <div className="fv-flex fv-items-center fv-justify-end fv-border-b fv-border-t-border fv-bg-t-surface fv-px-4 fv-py-2">
          <button
            type="button"
            onClick={handleCopy}
            className="fv-rounded-lg fv-border fv-border-t-border fv-px-2.5 fv-py-1 fv-text-[10px] fv-font-semibold fv-text-t-secondary fv-transition-colors fv-duration-150 hover:fv-border-t-border-accent hover:fv-text-t-primary fv-outline-none focus-visible:fv-ring-2 focus-visible:fv-ring-white/70"
          >
            {copyState === "copied" ? "Copied ✓" : copyState === "failed" ? "Copy failed" : "Copy verification"}
          </button>
        </div>
      )}

      <div className="fv-max-h-[68vh] fv-overflow-y-auto fv-px-4 fv-py-3.5">
        {/* SECTION 1 — Analyst summary --------------------------------- */}
        <section className="fv-mb-4">
          <SectionLabel>Analyst summary</SectionLabel>
          <div
            className="fv-rounded-xl fv-border-l-2 fv-bg-t-surface fv-px-3.5 fv-py-2.5"
            style={{ borderLeftColor: palette.text }}
          >
            <p className="fv-text-[12px] fv-leading-relaxed fv-text-t-primary">
              {overall.kind === "pending" ? (
                <>
                  Reviewing <span className="fv-font-bold">{summary.total}</span> financial claim
                  {summary.total === 1 ? "" : "s"} in this response.
                </>
              ) : overall.kind === "hard-error" ? (
                <>
                  Verification could not be completed for any of the{" "}
                  <span className="fv-font-bold">{summary.total}</span> claim
                  {summary.total === 1 ? "" : "s"} detected.
                </>
              ) : (
                <>
                  This response contains <span className="fv-font-bold">{summary.total}</span>{" "}
                  financial claim{summary.total === 1 ? "" : "s"}.{" "}
                  {summary.verifiedClean > 0 && (
                    <>
                      <span className="fv-font-bold">{summary.verifiedClean}</span> matched verification
                      exactly.{" "}
                    </>
                  )}
                  {summary.corroborated.length > 0 && (
                    <><span className="fv-font-bold">{summary.corroborated.length}</span> independently corroborated. </>
                  )}
                  {summary.contradictedCount > 0 && (
                    <><span className="fv-font-bold">{summary.contradictedCount}</span> contradicted. </>
                  )}
                  {summary.uncorroboratedCount > 0 && (
                    <><span className="fv-font-bold">{summary.corroborated.length} of {summary.total}</span> independently corroborated; <span className="fv-font-bold">{summary.uncorroboratedCount}</span> unverified. No independent evidence available. </>
                  )}
                  {summary.corrected > 0 && (
                    <>
                      <span className="fv-font-bold">{summary.corrected}</span> required a normalization
                      or correction.{" "}
                    </>
                  )}
                  {summary.unavailable > 0 && (
                    <>
                      <span className="fv-font-bold">{summary.unavailable}</span> could not be checked.{" "}
                    </>
                  )}
                  {summary.offline > 0 && <>Some values are offline estimates pending a live backend. </>}
                  {/* Every branch below must produce text. The old version fell
                   * through to "" whenever claims were flagged for review purely
                   * for low trust with no material correction (e.g. no
                   * corroborating evidence tier available) — that's exactly the
                   * case where the confidence meter reads LOW while this
                   * paragraph, left silent, implied everything was fine. */}
                  {flaggedForReview.length === 0 && summary.unavailable === 0
                    ? "No material discrepancies detected."
                    : materialCorrections.length > 0 && lowConfidenceUncorrected > 0
                      ? `${materialCorrections.length} value${materialCorrections.length === 1 ? "" : "s"} differed materially from what was reported, and ${lowConfidenceUncorrected} more matched the reported figure but could not be corroborated against verified evidence.`
                      : materialCorrections.length > 0
                        ? `${materialCorrections.length} value${materialCorrections.length === 1 ? "" : "s"} differed materially from what was reported.`
                        : lowConfidenceUncorrected > 0
                          ? `${lowConfidenceUncorrected} value${lowConfidenceUncorrected === 1 ? "" : "s"} could not be independently corroborated.`
                          : "No material discrepancies detected among the claims that could be checked."}
                </>
              )}
            </p>
          </div>
        </section>

        {/* SECTION 2 — Key financial metrics ---------------------------- */}
        {visibleMetrics.length > 0 && (
          <section className="fv-mb-4">
            <SectionLabel>Key financial metrics</SectionLabel>
            <div className="fv-divide-y fv-divide-t-border fv-rounded-xl fv-border fv-border-t-border fv-bg-t-surface fv-px-3">
              {visibleMetrics.map((claim) => (
                <MetricRow key={claim.id} claim={claim} />
              ))}
            </div>
            {remainingMetricsCount > 0 && (
              <button
                type="button"
                onClick={() => setShowAllMetrics((v) => !v)}
                className="fv-mt-1.5 fv-w-full fv-rounded-lg fv-px-2 fv-py-1.5 fv-text-left fv-text-[10.5px] fv-font-semibold fv-text-t-secondary fv-transition-colors fv-duration-150 hover:fv-text-t-primary fv-outline-none focus-visible:fv-ring-2 focus-visible:fv-ring-white/70"
              >
                {showAllMetrics ? "Show fewer metrics" : `View remaining ${remainingMetricsCount} metrics`}
              </button>
            )}
          </section>
        )}

        {/* SECTION 3 — Corrections & normalizations ---------------------- */}
        {(materialCorrections.length > 0 || normalizedOnly.length > 0) && (
          <section className="fv-mb-4">
            <SectionLabel>Corrections &amp; normalizations</SectionLabel>
            <div className="fv-divide-y fv-divide-t-border fv-rounded-xl fv-border fv-border-t-border fv-bg-t-surface fv-px-3">
              {materialCorrections.map((claim) => (
                <CorrectionRow key={claim.id} claim={claim} material />
              ))}
              {normalizedOnly.map((claim) => (
                <CorrectionRow key={claim.id} claim={claim} material={false} />
              ))}
            </div>
          </section>
        )}

        {/* SECTION 4 — Methodology (evidence, without inventing sources) - */}
        <section className="fv-mb-4">
          <SectionLabel>Methodology</SectionLabel>
          <p className="fv-px-0.5 fv-text-[10.5px] fv-leading-relaxed fv-text-t-muted">
            Checked with FinVerify's deterministic verification logic — no model-generated scoring.
            {verifiedClaims.some((c) => c.result?.question) && " Hover a metric above for the specific check performed."}
          </p>
        </section>

        {/* SECTION 5 — Potential issues ----------------------------------- */}
        {(flaggedForReview.length > 0 || hardErrorClaims.length > 0) && (
          <section className="fv-mb-4">
            <SectionLabel>Potential issues</SectionLabel>
            <div className="fv-divide-y fv-divide-t-border fv-rounded-xl fv-border fv-border-t-border fv-bg-t-surface fv-px-3">
              {flaggedForReview.map((claim) => (
                <IssueRow key={claim.id} claim={claim} />
              ))}
              {hardErrorClaims.map((claim) => (
                <IssueRow key={claim.id} claim={claim} />
              ))}
            </div>
          </section>
        )}

        {/* SECTION 6 — Raw claims, collapsed by default -------------------- */}
        <section>
          <button
            type="button"
            onClick={() => setShowRaw((v) => !v)}
            aria-expanded={showRaw}
            className="fv-flex fv-w-full fv-items-center fv-justify-between fv-rounded-xl fv-border fv-border-t-border fv-bg-t-surface fv-px-3.5 fv-py-2.5 fv-text-[11px] fv-font-semibold fv-text-t-secondary fv-transition-colors hover:fv-border-t-border-accent hover:fv-text-t-primary fv-outline-none focus-visible:fv-ring-2 focus-visible:fv-ring-white/70"
          >
            <span>
              {showRaw ? "Hide" : "Show"} all {claims.length} extracted claim{claims.length === 1 ? "" : "s"}
            </span>
            <span className={`fv-transition-transform fv-duration-150 ${showRaw ? "fv-rotate-180" : ""}`} aria-hidden="true">
              ⌄
            </span>
          </button>
          {showRaw && (
            <ul
              className="fv-mt-2 fv-max-h-64 fv-space-y-2 fv-overflow-y-auto fv-rounded-xl fv-border fv-border-t-border fv-bg-t-surface fv-px-3 fv-py-2.5 fv-pr-1"
              aria-label="All extracted claims"
            >
              {claims.map((claim) => (
                <ClaimRow key={claim.id} claim={claim} />
              ))}
            </ul>
          )}
        </section>

        <div className="fv-mt-4 fv-flex fv-items-center fv-justify-between fv-border-t fv-border-t-border fv-pt-3 fv-text-[9px] fv-text-t-muted">
          <span>{overall.kind === "trust" && overall.hasOffline ? "Includes offline estimate(s)" : "\u00A0"}</span>
          <a
            href="https://finverify-llm.vercel.app"
            target="_blank"
            rel="noopener noreferrer"
            className="fv-rounded fv-font-semibold fv-text-t-green fv-no-underline fv-outline-none focus-visible:fv-ring-2 focus-visible:fv-ring-t-green focus-visible:fv-ring-offset-1 focus-visible:fv-ring-offset-t-bg"
          >
            Powered by FinVerify
          </a>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Section 2 — a single metric card
 * ------------------------------------------------------------------ */

function MetricRow({ claim }: { claim: VerifiedClaim }) {
  const result = claim.result!;
  const isOffline = !!claim.error;
  const palette = trustPalette(result.trust_score);
  const state = claimSemanticState(claim);
  // CONTRADICTED must render the actual primary-source evidence value,
  // never `verified_value` (which still echoes the claim on a
  // contradiction). No evidence_value available -> omit the second value
  // rather than fabricate one.
  const contradictedWithoutEvidence = state === "contradicted" && result.evidence_value == null;
  const displayValue = state === "contradicted" ? result.evidence_value : result.verified_value;

  const detail = [
    `Confidence: ${trustLabel(result.trust_score)}.`,
    result.correction_applied ? `${result.correction_applied}.` : null,
    result.question ? `Checked via: ${result.question}` : null,
    isOffline ? "Backend unreachable — showing an offline estimate." : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div
      className="fv-flex fv-items-center fv-justify-between fv-gap-3 fv-py-2 fv-transition-colors fv-duration-150 hover:fv-bg-t-border/30"
      title={detail}
    >
      <div className="fv-flex fv-min-w-0 fv-items-center fv-gap-2">
        <span
          className="fv-h-1.5 fv-w-1.5 fv-shrink-0 fv-rounded-full"
          style={{ background: palette.text }}
          aria-hidden="true"
        />
        <span className="fv-truncate fv-text-[11.5px] fv-text-t-primary">{claim.match}</span>
        {result.correction_applied && (
          <span className="fv-shrink-0 fv-text-[10px] fv-font-bold fv-text-t-amber" aria-hidden="true">
            *
          </span>
        )}
        {isOffline && (
          <span className="fv-shrink-0 fv-rounded fv-border fv-border-t-border-accent fv-px-1 fv-py-0.5 fv-text-[8px] fv-font-bold fv-tracking-wide fv-text-t-secondary">
            OFFLINE
          </span>
        )}
      </div>
      <div className="fv-flex fv-shrink-0 fv-items-baseline fv-gap-2">
        <span className="fv-font-mono fv-text-[10.5px] fv-tabular-nums fv-text-t-muted">
          {formatValue(result.raw_value, result.question)}
        </span>
        {!contradictedWithoutEvidence && (
          <span
            className="fv-font-mono fv-text-[14px] fv-font-bold fv-tabular-nums"
            style={{ color: palette.text }}
          >
            {formatValue(displayValue, result.question)}
          </span>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Section 3 — corrections & normalizations
 * ------------------------------------------------------------------ */

function CorrectionRow({ claim, material }: { claim: VerifiedClaim; material: boolean }) {
  const result = claim.result!;
  const palette = trustPalette(material ? result.trust_score : "N/A");
  const detail = material
    ? `${result.correction_applied} — reported value differed from verification.`
    : `${result.correction_applied} — formatting difference only, no financial discrepancy.`;

  return (
    <div className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-py-2 fv-transition-colors fv-duration-150 hover:fv-bg-t-border/30" title={detail}>
      <span className="fv-truncate fv-text-[11.5px] fv-text-t-primary">{claim.match}</span>
      <div className="fv-flex fv-shrink-0 fv-items-center fv-gap-2">
        <span className="fv-flex fv-items-center fv-gap-1 fv-font-mono fv-text-[10px] fv-tabular-nums fv-text-t-secondary">
          {formatValue(result.raw_value, result.question)}
          <span aria-hidden="true">→</span>
          <span className="fv-font-semibold" style={{ color: palette.text }}>
            {formatValue(result.verified_value, result.question)}
          </span>
          {Math.abs(result.delta_pct) > 0.05 && (
            <span className="fv-text-t-muted">
              (Δ{result.delta_pct > 0 ? "+" : ""}
              {result.delta_pct.toFixed(1)}%)
            </span>
          )}
        </span>
        <span
          className="fv-shrink-0 fv-rounded-full fv-px-1.5 fv-py-0.5 fv-text-[9px] fv-font-bold"
          style={{ background: palette.bg, color: palette.text }}
        >
          {material ? "CORRECTED" : "NORMALIZED"}
        </span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Section 5 — potential issues
 * ------------------------------------------------------------------ */

function IssueRow({ claim }: { claim: VerifiedClaim }) {
  if (claim.status === "error" || !claim.result) {
    const low = trustPalette("LOW");
    return (
      <div
        className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-py-2 fv-transition-colors fv-duration-150 hover:fv-bg-t-border/30"
        title={claim.error ?? "Verification failed"}
      >
        <span className="fv-truncate fv-text-[11.5px] fv-text-t-primary">{claim.match}</span>
        <span
          className="fv-shrink-0 fv-rounded-full fv-px-1.5 fv-py-0.5 fv-text-[9px] fv-font-bold"
          style={{ background: low.bg, color: low.text }}
        >
          ! UNAVAILABLE
        </span>
      </div>
    );
  }

  const result = claim.result;
  const palette = trustPalette(result.trust_score);
  return (
    <div
      className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-py-2 fv-transition-colors fv-duration-150 hover:fv-bg-t-border/30"
      title={`Differs by ${Math.abs(result.delta_pct).toFixed(1)}% from the reported value — confirm against the source.`}
    >
      <span className="fv-truncate fv-text-[11.5px] fv-text-t-primary">{claim.match}</span>
      <div className="fv-flex fv-shrink-0 fv-items-center fv-gap-2">
        <span className="fv-font-mono fv-text-[10px] fv-tabular-nums fv-text-t-muted">
          Δ{Math.abs(result.delta_pct).toFixed(1)}%
        </span>
        <span
          className="fv-shrink-0 fv-rounded-full fv-px-1.5 fv-py-0.5 fv-text-[9px] fv-font-bold"
          style={{ background: palette.bg, color: palette.text }}
        >
          {trustIcon(result.trust_score)} {result.trust_score}
        </span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Section 6 — raw claim row (unchanged behavior, restyled to match)
 * ------------------------------------------------------------------ */

function ClaimRow({ claim }: { claim: VerifiedClaim }) {
  // Pending — lightweight skeleton instead of a bare spinner+text pair.
  if (claim.status === "pending") {
    return (
      <li className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-text-t-secondary">
        <span className="fv-flex fv-min-w-0 fv-flex-col fv-gap-1">
          <span className="fv-truncate">{claim.match}</span>
          <span className="fv-h-1 fv-w-16 fv-animate-pulse fv-rounded-full fv-bg-t-border motion-reduce:fv-animate-none" />
        </span>
        <Ring color="#888888" />
        <span className="fv-sr-only">Verifying</span>
      </li>
    );
  }

  // Cancelled — session moved on before this claim resolved.
  if (claim.status === "cancelled") {
    return (
      <li className="fv-flex fv-items-center fv-justify-between fv-text-t-muted">
        <span className="fv-truncate">{claim.match}</span>
        <span aria-hidden="true">⊘</span>
        <span className="fv-sr-only">Verification cancelled</span>
      </li>
    );
  }

  // Hard error — no plugin / no offline fallback, so there is no result
  // to render.
  if (claim.status === "error" || !claim.result) {
    return (
      <li
        className="fv-flex fv-flex-col fv-gap-0.5 fv-rounded fv-border fv-border-dashed fv-px-1.5 fv-py-1"
        style={{ borderColor: trustPalette("LOW").border }}
        title={claim.error}
      >
        <div className="fv-flex fv-items-center fv-justify-between fv-gap-2">
          <span className="fv-truncate fv-text-t-primary">{claim.match}</span>
          <span
            className="fv-shrink-0 fv-rounded fv-px-1.5 fv-py-0.5 fv-text-[9px] fv-font-bold"
            style={{ background: trustPalette("LOW").bg, color: trustPalette("LOW").text }}
          >
            ! UNAVAILABLE
          </span>
        </div>
        <span className="fv-truncate fv-text-[10px] fv-text-t-secondary">
          {claim.error ?? "Verification failed"}
        </span>
      </li>
    );
  }

  // Verified — either a normal online result or an offline fallback
  // estimate (claim.error set alongside a result). These look
  // deliberately different so users never mistake one for the other.
  const result = claim.result;
  const isOffline = !!claim.error;
  const palette = trustPalette(result.trust_score);
  const state = claimSemanticState(claim);
  // CONTRADICTED must show the actual primary-source evidence value, not
  // `verified_value` (which still echoes the claim on a contradiction).
  const contradictedWithoutEvidence = state === "contradicted" && result.evidence_value == null;
  const displayValue = state === "contradicted" ? result.evidence_value : result.verified_value;
  const hoverTitle = `raw ${result.raw_value} \u2192 ${state === "contradicted" ? "evidence" : "verified"} ${displayValue ?? "unavailable"}${result.correction_applied ? ` (${result.correction_applied})` : ""
    }${isOffline ? " — backend unreachable, showing offline estimate" : ""}`;

  return (
    <li
      className={`fv-flex fv-flex-col fv-gap-0.5 fv-rounded fv-px-1.5 fv-py-1 ${isOffline ? "fv-border fv-border-dashed fv-border-t-border-accent" : ""
        }`}
      title={hoverTitle}
    >
      <div className="fv-flex fv-items-center fv-justify-between fv-gap-2">
        <span className="fv-truncate fv-text-t-primary">{claim.match}</span>
        <span className="fv-flex fv-shrink-0 fv-items-center fv-gap-1">
          {isOffline && (
            <span
              className="fv-rounded fv-border fv-border-t-border-accent fv-px-1 fv-py-0.5 fv-text-[8px] fv-font-bold fv-tracking-wide fv-text-t-secondary"
              title="Backend unreachable — showing a locally-estimated value"
            >
              OFFLINE
            </span>
          )}
          <span
            className="fv-rounded fv-px-1.5 fv-py-0.5 fv-text-[9px] fv-font-bold"
            style={{ background: palette.bg, border: `1px solid ${palette.border}`, color: palette.text }}
          >
            {trustIcon(result.trust_score)} {result.trust_score}
          </span>
        </span>
      </div>
      <div className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-text-[10px] fv-text-t-secondary">
        <span className="fv-truncate">
          raw {formatValue(result.raw_value, result.question)}
          {!contradictedWithoutEvidence && (
            <>
              {" "}
              →{" "}
              <span style={{ color: palette.text }}>{formatValue(displayValue, result.question)}</span>
            </>
          )}
        </span>
        {result.correction_applied && (
          <span className="fv-shrink-0 fv-text-t-amber">
            {result.correction_applied}
            {Math.abs(result.delta_pct) > 0.05 && (
              <span className="fv-ml-1 fv-text-t-muted">
                (Δ {result.delta_pct > 0 ? "+" : ""}
                {result.delta_pct.toFixed(1)}%)
              </span>
            )}
          </span>
        )}
      </div>
    </li>
  );
}
