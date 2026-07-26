import { useEffect, useId, useRef, useState } from "react";
import type { VerifiedClaim } from "@finverify/core";
import { trustIcon, trustPalette } from "@finverify/core";
import { engine } from "@/engineInstance";
import { VerificationCard, deriveOverallStatus } from "@/ui/VerificationCard";

interface Props {
  /** Current plain-text content of the message. The orchestrator passes a
   *  fresh value in as the message streams; this component diffs against
   *  what it's already seen and only verifies claims it hasn't before —
   *  that's what makes verification "live" instead of "click and wait". */
  text: string;
}

export function InlineBadge({ text }: Props) {
  const [claims, setClaims] = useState<Map<string, VerifiedClaim>>(new Map());
  const [expanded, setExpanded] = useState(false);
  const [justCompleted, setJustCompleted] = useState(false);
  const sessionRef = useRef<ReturnType<typeof engine.createSession> | null>(null);
  const seenIdsRef = useRef<Set<string>>(new Set());
  const wasPendingRef = useRef(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelId = useId();

  if (!sessionRef.current) {
    sessionRef.current = engine.createSession();
  }

  useEffect(() => {
    const session = sessionRef.current!;
    // The engine's event bus is shared across every session; filter to
    // just this component's session id so concurrent messages' claims
    // never cross-update each other's badge.
    const unsubscribe = engine.on((event) => {
      if (event.sessionId !== session.id) return;
      if (event.type === "claim:updated") {
        setClaims((prev) => new Map(prev).set(event.claim.id, event.claim));
      }
    });
    return () => {
      unsubscribe();
      session.cancel();
    };
  }, []);

  useEffect(() => {
    const session = sessionRef.current;
    if (!session || session.isCancelled) return;

    const extracted = engine.detectClaims(text);
    const freshClaims = extracted.filter((c) => !seenIdsRef.current.has(c.id));
    if (freshClaims.length === 0) return;

    for (const c of freshClaims) seenIdsRef.current.add(c.id);
    setClaims((prev) => {
      const next = new Map(prev);
      for (const c of freshClaims) next.set(c.id, { ...c, status: "pending" });
      return next;
    });

    session.verify(freshClaims);
    // Deliberately only depends on `text` — extraction re-runs whenever the
    // orchestrator gives us new text (debounced upstream), but already-seen
    // claim ids are skipped via seenIdsRef, so this never re-verifies a
    // claim that hasn't changed.
  }, [text]);

  // Keyboard support: Escape closes the panel and returns focus to the
  // toggle button, matching the standard disclosure-widget pattern
  // (same behavior a native <details>/menu/dialog gives you for free).
  useEffect(() => {
    if (!expanded) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setExpanded(false);
        buttonRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [expanded]);

  const claimList = Array.from(claims.values());
  const overall = deriveOverallStatus(claimList);

  // One-shot "verification just completed" glow: fires the transition
  // from pending -> resolved, not on every re-render. Purely a display
  // affordance layered on top of state the effects above already produce.
  useEffect(() => {
    const isPending = overall.kind === "pending";
    if (wasPendingRef.current && !isPending) {
      setJustCompleted(true);
      const t = setTimeout(() => setJustCompleted(false), 900);
      return () => clearTimeout(t);
    }
    wasPendingRef.current = isPending;
  }, [overall.kind]);

  if (overall.kind === "empty") return null;

  const palette =
    overall.kind === "trust"
      ? trustPalette(overall.trust)
      : overall.kind === "hard-error"
        ? trustPalette("LOW")
        : trustPalette(overall.bestKnown ?? "N/A");

  const statusText =
    overall.kind === "pending"
      ? `FinVerify: verifying ${overall.done} of ${overall.total} claims`
      : overall.kind === "hard-error"
        ? `FinVerify: ${overall.total} claim${overall.total === 1 ? "" : "s"}, verification unavailable`
        : `FinVerify: ${overall.total} claim${overall.total === 1 ? "" : "s"}, ${overall.trust.toLowerCase()}${overall.hasOffline ? ", includes offline estimate" : ""
        }${overall.unavailable > 0 ? `, ${overall.unavailable} unavailable` : ""}`;

  return (
    <span className="fv-relative fv-inline-flex fv-items-center">
      <button
        ref={buttonRef}
        type="button"
        aria-label={statusText}
        aria-expanded={expanded}
        aria-controls={panelId}
        title="FinVerify — click to expand, Esc to close"
        onClick={() => setExpanded((v) => !v)}
        className={`fv-relative fv-flex fv-h-8 fv-w-8 fv-items-center fv-justify-center fv-rounded-md fv-border fv-border-transparent fv-transition-all fv-duration-150 hover:fv-border-t-border-accent hover:fv-bg-t-border active:fv-scale-90 motion-reduce:active:fv-scale-100 fv-outline-none focus-visible:fv-ring-2 focus-visible:fv-ring-white/70 focus-visible:fv-ring-offset-1 focus-visible:fv-ring-offset-t-bg ${expanded ? "fv-bg-t-border fv-border-t-border-accent" : ""
          }`}
        style={{ color: palette.text }}
      >
        <span className="fv-relative fv-flex fv-h-4 fv-w-4 fv-items-center fv-justify-center" aria-hidden="true">
          {/* One-shot completion ping, hidden for reduced-motion users */}
          {justCompleted && (
            <span
              className="fv-absolute fv-inline-flex fv-h-full fv-w-full fv-animate-ping fv-rounded-full motion-reduce:fv-hidden"
              style={{ background: palette.text, opacity: 0.4 }}
            />
          )}
          {overall.kind === "pending" ? (
            <span
              className="fv-h-3 fv-w-3 fv-animate-spin fv-rounded-full fv-border-2 motion-reduce:fv-animate-none"
              style={{ borderColor: palette.text, borderTopColor: "transparent" }}
            />
          ) : (
            <span
              className="fv-relative fv-flex fv-h-4 fv-w-4 fv-items-center fv-justify-center fv-rounded-full fv-text-[9px] fv-font-bold fv-transition-shadow fv-duration-200"
              style={{
                background: palette.bg,
                color: palette.text,
                boxShadow: `0 0 6px ${palette.text}`,
              }}
            >
              {overall.kind === "hard-error" ? "!" : trustIcon(overall.trust)}
            </span>
          )}
        </span>
      </button>

      {/* Visually hidden live region — screen readers hear trust-status
          changes (pending -> verified/flagged/warning/unavailable) without
          needing the panel expanded, matching what the visible icon
          already communicates sighted users. */}
      <span role="status" aria-live="polite" className="fv-sr-only">
        {statusText}
      </span>

      {expanded && (
        <div
          id={panelId}
          role="region"
          aria-label="FinVerify verification details"
          className="fv-absolute fv-left-0 fv-top-full fv-z-50 fv-animate-slide-up motion-reduce:fv-animate-none"
        >
          <VerificationCard claims={claimList} />
        </div>
      )}
    </span>
  );
}
