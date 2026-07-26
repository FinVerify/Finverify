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


function Ring({ color, size = "fv-h-3 fv-w-3" }: { color: string; size?: string }) {
  return (
    <span
      className={`${size} fv-shrink-0 fv-rounded-full fv-border-2 fv-animate-spin motion-reduce:fv-animate-none`}
      style={{ borderColor: color, borderTopColor: "transparent" }}
      aria-hidden="true"
    />
  );
}

export function VerificationCard({ claims }: Props) {
  const overall = deriveOverallStatus(claims);

  if (overall.kind === "empty") {
    return (
      <div className="fv-mt-2 fv-w-80 fv-rounded-lg fv-border fv-border-t-border fv-bg-t-bg fv-px-3 fv-py-3 fv-font-mono fv-text-xs fv-text-t-secondary">
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

  return (
    <div
      className="fv-mt-2 fv-w-80 fv-overflow-hidden fv-rounded-lg fv-border fv-font-mono fv-text-xs fv-animate-fade-in motion-reduce:fv-animate-none"
      style={{ borderColor: palette.border, background: "#0a0a0a" }}
    >
      {/* Header ------------------------------------------------------ */}
      <div className="fv-flex fv-items-center fv-justify-between fv-gap-2 fv-px-3 fv-py-2">
        <span className="fv-flex fv-min-w-0 fv-items-center fv-gap-2">
          <span
            className="fv-flex fv-h-4 fv-w-4 fv-shrink-0 fv-items-center fv-justify-center fv-rounded-full fv-text-[10px] fv-font-bold"
            style={{ background: palette.bg, color: palette.text }}
            aria-hidden="true"
          >
            {overall.kind === "pending" ? (
              <Ring color={palette.text} size="fv-h-2.5 fv-w-2.5" />
            ) : overall.kind === "hard-error" ? (
              "!"
            ) : (
              trustIcon(overall.trust)
            )}
          </span>
          <span className="fv-truncate fv-font-bold fv-tracking-wide" style={{ color: palette.text }}>
            {overall.kind === "pending"
              ? `VERIFYING… (${overall.done}/${overall.total})`
              : overall.kind === "hard-error"
                ? "UNAVAILABLE"
                : `DVL ${trustLabel(overall.trust)}`}
          </span>
        </span>
        <span className="fv-shrink-0 fv-text-t-secondary">
          {overall.kind === "trust" && overall.unavailable > 0
            ? `${overall.total - overall.unavailable}/${overall.total} claims`
            : `${claims.length} claim${claims.length === 1 ? "" : "s"}`}
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

      {/* Claim list — capped height so long responses stay usable ---- */}
      <div className="fv-border-t fv-border-t-border fv-px-3 fv-py-2">
        <ul
          className="fv-max-h-64 fv-space-y-2 fv-overflow-y-auto fv-pr-1"
          aria-label="Verified claims"
        >
          {claims.map((claim) => (
            <ClaimRow key={claim.id} claim={claim} />
          ))}
        </ul>
        <div className="fv-mt-2 fv-flex fv-items-center fv-justify-between fv-border-t fv-border-t-border fv-pt-2 fv-text-[9px] fv-text-t-muted">
          <span>
            {overall.kind === "trust" && overall.hasOffline ? "Includes offline estimate(s)" : "\u00A0"}
          </span>
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
  // to render. Previously this branch fell through to `claim.result!`
  // and threw; now it gets its own honest treatment.
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
  // estimate (claim.error set alongside a result). These now look
  // deliberately different so users never mistake one for the other.
  const result = claim.result;
  const isOffline = !!claim.error;
  const palette = trustPalette(result.trust_score);
  const hoverTitle = `raw ${result.raw_value} \u2192 verified ${result.verified_value}${result.correction_applied ? ` (${result.correction_applied})` : ""
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
