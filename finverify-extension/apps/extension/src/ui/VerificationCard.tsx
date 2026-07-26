import { useState } from "react";
import type { TrustScore, VerifiedClaim } from "@finverify/core";
import { formatValue, trustIcon, trustLabel, trustPalette } from "@finverify/core";

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
  if (verified.length === 0) return null;
  if (verified.some((c) => c.result?.trust_score === "LOW")) return "LOW";
  if (verified.some((c) => c.result?.trust_score === "MEDIUM")) return "MEDIUM";
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

interface AnalystSummary {
  total: number;
  verifiedClean: number;
  corrected: number;
  offline: number;
  unavailable: number;
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

function deriveAnalystSummary(claims: VerifiedClaim[]): AnalystSummary {
  const verified = claims.filter((c) => c.status === "verified" && c.result);
  const corrected = verified.filter((c) => !!c.result?.correction_applied).length;
  const offline = verified.filter((c) => !!c.error).length;
  const unavailable = claims.filter((c) => c.status === "error").length;
  const confidencePercent = verified.length
    ? Math.round(verified.reduce((sum, c) => sum + trustWeight(c.result!.trust_score), 0) / verified.length)
    : 0;

  return {
    total: claims.length,
    verifiedClean: verified.length - corrected,
    corrected,
    offline,
    unavailable,
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

/* ------------------------------------------------------------------ *
 * Main card
 * ------------------------------------------------------------------ */

export function VerificationCard({ claims }: Props) {
  const overall = deriveOverallStatus(claims);
  const [showRaw, setShowRaw] = useState(false);

  if (overall.kind === "empty") {
    return (
      <div className="fv-mt-2 fv-w-[560px] fv-max-w-[92vw] fv-rounded-xl fv-border fv-border-t-border fv-bg-t-bg fv-px-4 fv-py-4 fv-font-mono fv-text-xs fv-text-t-secondary">
        No financial claims detected in this response.
      </div>
    );
  }

  const palette =
    overall.kind === "trust"
      ? trustPalette(overall.trust)
      : overall.kind === "hard-error"
        ? trustPalette("LOW")
        : trustPalette(overall.bestKnown ?? "N/A");

  const summary = deriveAnalystSummary(claims);
  const verifiedClaims = claims.filter((c) => c.status === "verified" && c.result);
  const materialCorrections = verifiedClaims.filter(isMaterialCorrection);
  const normalizedOnly = verifiedClaims.filter(
    (c) => c.result?.correction_applied && !isMaterialCorrection(c)
  );
  const flaggedForReview = verifiedClaims.filter(
    (c) => c.result?.trust_score === "LOW" || isMaterialCorrection(c)
  );
  const hardErrorClaims = claims.filter((c) => c.status === "error");
  const metricClaims = verifiedClaims.slice(0, 6);

  return (
    <div
      className="fv-mt-2 fv-w-[560px] fv-max-w-[92vw] fv-overflow-hidden fv-rounded-xl fv-border fv-font-mono fv-text-xs fv-shadow-[0_12px_40px_rgba(0,0,0,0.45)] fv-animate-fade-in motion-reduce:fv-animate-none"
      style={{ borderColor: palette.border, background: "#0a0a0a" }}
    >
      {/* Header ------------------------------------------------------ */}
      <div className="fv-flex fv-items-center fv-justify-between fv-gap-3 fv-border-b fv-border-t-border fv-px-4 fv-py-3.5">
        <div className="fv-flex fv-min-w-0 fv-items-center fv-gap-3">
          <span
            className="fv-flex fv-h-7 fv-w-7 fv-shrink-0 fv-items-center fv-justify-center fv-rounded-full fv-text-xs fv-font-bold"
            style={{ background: palette.bg, color: palette.text }}
            aria-hidden="true"
          >
            {overall.kind === "pending" ? (
              <Ring color={palette.text} size="fv-h-3.5 fv-w-3.5" />
            ) : overall.kind === "hard-error" ? (
              "!"
            ) : (
              trustIcon(overall.trust)
            )}
          </span>
          <div className="fv-min-w-0">
            <div className="fv-truncate fv-text-[13px] fv-font-bold fv-leading-tight fv-tracking-[0.01em] fv-text-t-primary">
              FinVerify Analysis
            </div>
            <div className="fv-truncate fv-text-[10.5px] fv-leading-tight fv-text-t-secondary">
              {overall.kind === "pending"
                ? `Verifying claim ${overall.done} of ${overall.total}…`
                : overall.kind === "hard-error"
                  ? "Verification unavailable"
                  : `${claims.length} claim${claims.length === 1 ? "" : "s"} reviewed`}
            </div>
          </div>
        </div>
        <span
          className="fv-shrink-0 fv-rounded-full fv-px-3 fv-py-1 fv-text-[10px] fv-font-bold fv-tracking-wide"
          style={{ background: palette.bg, color: palette.text }}
        >
          {overall.kind === "pending"
            ? "IN PROGRESS"
            : overall.kind === "hard-error"
              ? "UNAVAILABLE"
              : trustLabel(overall.trust)}
        </span>
      </div>

      {/* Progress bar — only while claims are still resolving -------- */}
      {overall.kind === "pending" && (
        <div className="fv-h-0.5 fv-w-full fv-bg-t-border" aria-hidden="true">
          <div
            className="fv-h-full fv-transition-all fv-duration-300 motion-reduce:fv-transition-none"
            style={{
              width: `${(overall.done / overall.total) * 100}%`,
              background: overall.bestKnown ? trustPalette(overall.bestKnown).text : "#888888",
            }}
          />
        </div>
      )}

      {/* Hero confidence — the number a person should read within the
          first five seconds, given top billing above everything else. */}
      {overall.kind === "trust" && (
        <div className="fv-border-b fv-border-t-border fv-bg-t-surface fv-px-4 fv-py-3.5">
          <ConfidenceMeter percent={summary.confidencePercent} trust={overall.trust} />
        </div>
      )}

      <div className="fv-max-h-[68vh] fv-overflow-y-auto fv-px-4 fv-py-3.5">
        {/* SECTION 1 — Analyst summary --------------------------------- */}
        <section className="fv-mb-4">
          <SectionLabel>Analyst summary</SectionLabel>
          <div
            className="fv-rounded-xl fv-border-l-2 fv-bg-t-surface fv-px-3.5 fv-py-3"
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
                  {flaggedForReview.length === 0 && summary.unavailable === 0
                    ? "No material discrepancies detected."
                    : materialCorrections.length > 0
                      ? `${materialCorrections.length} value${materialCorrections.length === 1 ? "" : "s"} differed materially from what was reported.`
                      : ""}
                </>
              )}
            </p>
          </div>
        </section>

        {/* SECTION 2 — Key financial metrics ---------------------------- */}
        {metricClaims.length > 0 && (
          <section className="fv-mb-4">
            <SectionLabel>Key financial metrics</SectionLabel>
            <div className="fv-grid fv-grid-cols-2 fv-gap-2">
              {metricClaims.map((claim) => (
                <MetricCard key={claim.id} claim={claim} />
              ))}
            </div>
          </section>
        )}

        {/* SECTION 3 — Corrections & normalizations ---------------------- */}
        {(materialCorrections.length > 0 || normalizedOnly.length > 0) && (
          <section className="fv-mb-4">
            <SectionLabel>Corrections &amp; normalizations</SectionLabel>
            <div className="fv-space-y-1.5">
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
          <div className="fv-rounded-xl fv-border fv-border-t-border fv-bg-t-surface fv-px-3.5 fv-py-2.5 fv-text-[11px] fv-leading-relaxed fv-text-t-secondary">
            Each claim is checked with FinVerify's deterministic verification logic — no
            model-generated scoring.{" "}
            {verifiedClaims.some((c) => c.result?.question) && (
              <>Where available, the specific check performed is shown on each metric above.</>
            )}
          </div>
        </section>

        {/* SECTION 5 — Potential issues ----------------------------------- */}
        {(flaggedForReview.length > 0 || hardErrorClaims.length > 0) && (
          <section className="fv-mb-4">
            <SectionLabel>Potential issues</SectionLabel>
            <div className="fv-space-y-1.5">
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

function MetricCard({ claim }: { claim: VerifiedClaim }) {
  const result = claim.result!;
  const isOffline = !!claim.error;
  const palette = trustPalette(result.trust_score);

  return (
    <div
      className={`fv-group fv-flex fv-flex-col fv-gap-2 fv-rounded-xl fv-border fv-bg-t-surface fv-px-3 fv-py-2.5 fv-transition-all fv-duration-150 hover:fv-bg-t-border/40 ${
        isOffline ? "fv-border-dashed fv-border-t-border-accent" : "fv-border-t-border hover:fv-border-t-border-accent"
      }`}
      title={isOffline ? "Backend unreachable — showing offline estimate" : undefined}
    >
      <div className="fv-flex fv-items-start fv-justify-between fv-gap-2">
        <span className="fv-truncate fv-text-[11px] fv-font-semibold fv-leading-tight fv-text-t-primary">
          {claim.match}
        </span>
        <span
          className="fv-flex fv-shrink-0 fv-items-center fv-gap-1 fv-rounded-full fv-px-1.5 fv-py-0.5 fv-text-[9px] fv-font-bold"
          style={{ background: palette.bg, color: palette.text }}
        >
          {trustIcon(result.trust_score)} {isOffline ? "OFFLINE" : "VERIFIED"}
        </span>
      </div>

      {/* Verified value reads as the primary number; the LLM's original
          value is demoted to a small strikethrough-free reference so the
          eye lands on what was actually confirmed. */}
      <div className="fv-flex fv-items-baseline fv-justify-between fv-gap-2">
        <div className="fv-min-w-0">
          <div className="fv-text-[9px] fv-uppercase fv-tracking-wide fv-text-t-muted">Verified</div>
          <div
            className="fv-truncate fv-font-mono fv-text-[15px] fv-font-bold fv-tabular-nums fv-leading-tight"
            style={{ color: palette.text }}
          >
            {formatValue(result.verified_value, result.question)}
          </div>
        </div>
        <div className="fv-shrink-0 fv-text-right">
          <div className="fv-text-[9px] fv-uppercase fv-tracking-wide fv-text-t-muted">LLM</div>
          <div className="fv-font-mono fv-text-[10.5px] fv-tabular-nums fv-text-t-secondary">
            {formatValue(result.raw_value, result.question)}
          </div>
        </div>
      </div>

      <div className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-border-t fv-border-t-border fv-pt-1.5 fv-text-[9.5px] fv-text-t-muted">
        <span>Confidence: {trustLabel(result.trust_score)}</span>
        {result.correction_applied && <span className="fv-truncate fv-text-t-amber">{result.correction_applied}</span>}
      </div>
      {result.question && (
        <div className="fv-truncate fv-text-[9.5px] fv-text-t-muted">Checked via: {result.question}</div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Section 3 — corrections & normalizations
 * ------------------------------------------------------------------ */

function CorrectionRow({ claim, material }: { claim: VerifiedClaim; material: boolean }) {
  const result = claim.result!;
  const palette = trustPalette(material ? result.trust_score : "N/A");

  return (
    <div className="fv-rounded-xl fv-border fv-border-t-border fv-bg-t-surface fv-px-3 fv-py-2 fv-transition-colors fv-duration-150 hover:fv-border-t-border-accent">
      <div className="fv-flex fv-items-center fv-justify-between fv-gap-2">
        <span className="fv-truncate fv-text-[11px] fv-text-t-primary">{claim.match}</span>
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
      <div className="fv-mt-1 fv-truncate fv-text-[9.5px] fv-text-t-muted">
        {material
          ? `${result.correction_applied} — reported value differed from verification.`
          : `${result.correction_applied} — formatting difference only, no financial discrepancy.`}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Section 5 — potential issues
 * ------------------------------------------------------------------ */

function IssueRow({ claim }: { claim: VerifiedClaim }) {
  if (claim.status === "error" || !claim.result) {
    return (
      <div
        className="fv-flex fv-flex-col fv-gap-0.5 fv-rounded-xl fv-border fv-border-dashed fv-px-3 fv-py-2"
        style={{ borderColor: trustPalette("LOW").border }}
      >
        <div className="fv-flex fv-items-center fv-justify-between fv-gap-2">
          <span className="fv-truncate fv-text-[11px] fv-text-t-primary">{claim.match}</span>
          <span
            className="fv-shrink-0 fv-rounded-full fv-px-1.5 fv-py-0.5 fv-text-[9px] fv-font-bold"
            style={{ background: trustPalette("LOW").bg, color: trustPalette("LOW").text }}
          >
            ! UNAVAILABLE
          </span>
        </div>
        <span className="fv-truncate fv-text-[10px] fv-text-t-secondary">{claim.error ?? "Verification failed"}</span>
      </div>
    );
  }

  const result = claim.result;
  const palette = trustPalette(result.trust_score);
  return (
    <div className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-rounded-xl fv-border fv-border-t-border fv-px-3 fv-py-2 fv-transition-colors fv-duration-150 hover:fv-border-t-border-accent">
      <div className="fv-min-w-0">
        <span className="fv-truncate fv-text-[11px] fv-text-t-primary">{claim.match}</span>
        <div className="fv-truncate fv-text-[9.5px] fv-text-t-muted">
          Differs by {Math.abs(result.delta_pct).toFixed(1)}% — confirm against the source.
        </div>
      </div>
      <span
        className="fv-shrink-0 fv-rounded-full fv-px-1.5 fv-py-0.5 fv-text-[9px] fv-font-bold"
        style={{ background: palette.bg, color: palette.text }}
      >
        {trustIcon(result.trust_score)} {result.trust_score}
      </span>
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
  const hoverTitle = `raw ${result.raw_value} \u2192 verified ${result.verified_value}${
    result.correction_applied ? ` (${result.correction_applied})` : ""
  }${isOffline ? " — backend unreachable, showing offline estimate" : ""}`;

  return (
    <li
      className={`fv-flex fv-flex-col fv-gap-0.5 fv-rounded fv-px-1.5 fv-py-1 ${
        isOffline ? "fv-border fv-border-dashed fv-border-t-border-accent" : ""
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
          raw {formatValue(result.raw_value, result.question)} →{" "}
          <span style={{ color: palette.text }}>{formatValue(result.verified_value, result.question)}</span>
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
