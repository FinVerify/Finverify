import { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { VerifiedClaim } from "@finverify/core";
import { deriveSemanticOverall, formatSemanticSummary, semanticIcon, semanticLabel, semanticPalette } from "@finverify/core";
import { engine } from "@/engineInstance";
import { VerificationCard, deriveOverallStatus } from "@/ui/VerificationCard";

interface Props {
  /** Current plain-text content of the message. The orchestrator passes a
   *  fresh value in as the message streams; this component diffs against
   *  what it's already seen and only verifies claims it hasn't before —
   *  that's what makes verification "live" instead of "click and wait". */
  text: string;
  modelSource: string;
}

export function InlineBadge({ text, modelSource }: Props) {
  const [claims, setClaims] = useState<Map<string, VerifiedClaim>>(new Map());
  const [expanded, setExpanded] = useState(false);
  const [justCompleted, setJustCompleted] = useState(false);
  const sessionRef = useRef<ReturnType<typeof engine.createSession> | null>(null);
  const seenIdsRef = useRef<Set<string>>(new Set());
  const wasPendingRef = useRef(false);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const panelId = useId();

  // Floating-panel position, computed relative to the button and clamped
  // to the viewport. Kept in state (rather than left as a plain absolute
  // child) because the panel now renders through a portal into
  // document.body — necessary so ChatGPT's message container can no
  // longer clip it — and a portal has no positional relationship to the
  // button unless we compute one ourselves.
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null);

  const updatePosition = useCallback(() => {
    const btn = buttonRef.current;
    if (!btn) return;
    const buttonRect = btn.getBoundingClientRect();
    const margin = 8;
    const panelWidth = panelRef.current?.offsetWidth ?? 560;
    const panelHeight = panelRef.current?.offsetHeight ?? 0;

    // Horizontal: prefer left-aligned with the button, but never let the
    // panel run past the right edge (or, on narrow viewports, the left).
    let left = buttonRect.left;
    const maxLeft = window.innerWidth - panelWidth - margin;
    left = Math.min(left, Math.max(margin, maxLeft));
    left = Math.max(left, margin);

    // Vertical: prefer below the button; flip above it if there isn't
    // room below, then fall back to clamping within the viewport if
    // neither side has room (e.g. a very short viewport).
    let top = buttonRect.bottom + margin;
    const fitsBelow = top + panelHeight <= window.innerHeight - margin;
    if (!fitsBelow) {
      const topAbove = buttonRect.top - panelHeight - margin;
      top = topAbove >= margin ? topAbove : Math.max(margin, window.innerHeight - panelHeight - margin);
    }

    setCoords({ top, left });
  }, []);

  if (!sessionRef.current) {
    sessionRef.current = engine.createSession({ modelSource });
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

  // Position the floating panel the instant it opens, then keep it pinned
  // to the button as the page scrolls or resizes. Capture-phase scroll
  // listening also catches scrolling inside ChatGPT's own message
  // container, not just the window itself.
  useLayoutEffect(() => {
    if (!expanded) {
      setCoords(null);
      return;
    }
    updatePosition();
    window.addEventListener("scroll", updatePosition, true);
    window.addEventListener("resize", updatePosition);
    return () => {
      window.removeEventListener("scroll", updatePosition, true);
      window.removeEventListener("resize", updatePosition);
    };
  }, [expanded, updatePosition]);

  // A portal-rendered panel sits outside the badge's normal DOM subtree,
  // so a click anywhere outside it (or the toggle button) should close
  // it, the way any other detached popover behaves.
  useEffect(() => {
    if (!expanded) return;
    const onPointerDown = (e: MouseEvent) => {
      const target = e.target as Node;
      if (panelRef.current?.contains(target) || buttonRef.current?.contains(target)) return;
      setExpanded(false);
    };
    document.addEventListener("mousedown", onPointerDown, true);
    return () => document.removeEventListener("mousedown", onPointerDown, true);
  }, [expanded]);

  const claimList = Array.from(claims.values());
  // Semantic state (VERIFIED/CONTRADICTED/UNVERIFIED/VERIFICATION UNAVAILABLE)
  // drives the marker's color, icon, and headline label — this is the
  // evidentiary finding the productization spec's states map to.
  // `deriveOverallStatus` (trust-score based) is kept only for the
  // secondary "confidence" detail folded into the aria-label below and
  // for offline-estimate detection; it is never the primary signal.
  const semantic = deriveSemanticOverall(claimList);
  const overall = deriveOverallStatus(claimList);

  // One-shot "verification just completed" glow: fires the transition
  // from pending -> resolved, not on every re-render. Purely a display
  // affordance layered on top of state the effects above already produce.
  useEffect(() => {
    const isPending = semantic.kind === "pending";
    if (wasPendingRef.current && !isPending) {
      setJustCompleted(true);
      const t = setTimeout(() => setJustCompleted(false), 900);
      return () => clearTimeout(t);
    }
    wasPendingRef.current = isPending;
  }, [semantic.kind]);

  if (semantic.kind === "empty") return null;

  const palette =
    semantic.kind === "resolved" && semantic.headline
      ? semanticPalette(semantic.headline)
      : semantic.kind === "unavailable"
        ? semanticPalette("unavailable")
        : { bg: "rgba(136,136,136,0.1)", border: "#888888", text: "#888888" };

  // The trailing "(confidence: high/medium/low)" clause is deliberately
  // kept even though the headline itself is now the semantic label — it
  // preserves the trust-score detail as secondary information (never the
  // centerpiece) rather than dropping it outright.
  const confidenceSuffix = overall.kind === "trust" ? ` (confidence: ${overall.trust.toLowerCase()})` : "";
  const statusText =
    semantic.kind === "pending"
      ? `FinVerify: verifying ${semantic.summary.total - semantic.summary.pending} of ${semantic.summary.total} claims`
      : semantic.kind === "unavailable"
        ? `FinVerify: ${semantic.summary.total} claim${semantic.summary.total === 1 ? "" : "s"}, verification unavailable`
        : `FinVerify: ${semantic.summary.total} claim${semantic.summary.total === 1 ? "" : "s"}, ${formatSemanticSummary(semantic.summary)}${confidenceSuffix}${overall.kind === "trust" && overall.hasOffline ? ", includes offline estimate" : ""
        }`;

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
        className={`fv-relative fv-flex fv-h-7 fv-items-center fv-gap-1.5 fv-rounded-full fv-border fv-border-t-border fv-bg-t-bg fv-px-2.5 fv-font-mono fv-transition-all fv-duration-150 hover:fv-border-t-border-accent hover:fv-bg-t-surface active:fv-scale-95 motion-reduce:active:fv-scale-100 fv-outline-none focus-visible:fv-ring-2 focus-visible:fv-ring-white/70 focus-visible:fv-ring-offset-1 focus-visible:fv-ring-offset-t-bg ${expanded ? "fv-bg-t-surface fv-border-t-border-accent" : ""
          }`}
        style={{ color: palette.text }}
      >
        <span className="fv-relative fv-flex fv-h-3.5 fv-w-3.5 fv-shrink-0 fv-items-center fv-justify-center" aria-hidden="true">
          {/* One-shot completion ping, hidden for reduced-motion users */}
          {justCompleted && (
            <span
              className="fv-absolute fv-inline-flex fv-h-full fv-w-full fv-animate-ping fv-rounded-full motion-reduce:fv-hidden"
              style={{ background: palette.text, opacity: 0.4 }}
            />
          )}
          {semantic.kind === "pending" ? (
            <span
              className="fv-h-3 fv-w-3 fv-animate-spin fv-rounded-full fv-border-2 motion-reduce:fv-animate-none"
              style={{ borderColor: palette.text, borderTopColor: "transparent" }}
            />
          ) : (
            <span
              className="fv-relative fv-flex fv-h-3.5 fv-w-3.5 fv-items-center fv-justify-center fv-rounded-full fv-text-[9px] fv-font-bold"
              style={{ background: palette.bg, color: palette.text }}
            >
              {semantic.kind === "unavailable" ? "!" : semanticIcon(semantic.headline!)}
            </span>
          )}
        </span>
        <span className="fv-text-[10px] fv-font-semibold fv-tracking-wide">
          {semantic.kind === "pending"
            ? `${semantic.summary.total - semantic.summary.pending}/${semantic.summary.total}`
            : semantic.kind === "unavailable"
              ? "UNAVAILABLE"
              : semantic.summary.total > 1
                ? formatSemanticSummary(semantic.summary)
                : semanticLabel(semantic.headline!)}
        </span>
      </button>

      {/* Visually hidden live region — screen readers hear verification-status
          changes (pending -> verified/contradicted/unverified/unavailable)
          without needing the panel expanded, matching what the visible icon
          already communicates sighted users. */}
      <span role="status" aria-live="polite" className="fv-sr-only">
        {statusText}
      </span>

      {expanded &&
        createPortal(
          <div
            ref={panelRef}
            id={panelId}
            role="region"
            aria-label="FinVerify verification details"
            className="fv-fixed fv-z-[2147483647] fv-animate-fade-in motion-reduce:fv-animate-none"
            style={{
              top: coords?.top ?? -9999,
              left: coords?.left ?? -9999,
              // Hide until the first real position is measured, so the
              // one-frame jump from the off-screen default never flashes.
              visibility: coords ? "visible" : "hidden",
            }}
          >
            <VerificationCard claims={claimList} />
          </div>,
          document.body
        )}
    </span>
  );
}
