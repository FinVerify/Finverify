import type { ExtractedClaim, V1VerifyResponse, VerifiedClaim } from "./types.js";
import type { VerificationTransport } from "./transport.js";
import { TransportError } from "./transport.js";
import type { PluginRegistry } from "./plugins/registry.js";
import type { VerifierPlugin } from "./plugins/types.js";
import type { EventBus } from "./events.js";
import { trustPalette } from "./trust.js";

let sessionCounter = 0;

interface DedupEntry {
  promise: Promise<V1VerifyResponse>;
  expiresAt: number;
}

export interface SessionDeps {
  registry: PluginRegistry;
  transport: VerificationTransport;
  bus: EventBus;
  dedupCache: Map<string, DedupEntry>;
  dedupTtlMs: number;
  concurrency: number;
}

/**
 * One verification pass, cancellable as a unit — create one per logical
 * unit of work (e.g. one chat message) so leaving/regenerating it can
 * cleanly cancel everything it started without affecting anything else.
 *
 * Domain-agnostic on purpose: a session verifying a mix of finance and
 * (eventually) healthcare claims in the same text works with zero special
 * casing here — `verifyOne` looks up the owning plugin per-claim via
 * `claim.domain` and calls that plugin's `buildQuestion`/`offlineFallback`.
 */
export class VerificationSession {
  readonly id: string;
  private cancelled = false;
  /** Only abort controllers this session actually *created* (i.e. it was
   *  the one that populated a fresh dedup cache entry) — see the doc
   *  comment on `getOrCreateDeduped` for why a session must never hold a
   *  controller for a request some *other* session's claim is also
   *  depending on. */
  private ownedControllers = new Set<AbortController>();

  constructor(private readonly deps: SessionDeps) {
    this.id = `session_${Date.now()}_${sessionCounter++}`;
  }

  get isCancelled(): boolean {
    return this.cancelled;
  }

  cancel(): void {
    if (this.cancelled) return;
    this.cancelled = true;
    for (const controller of this.ownedControllers) controller.abort();
    this.ownedControllers.clear();
    this.deps.bus.emit({ type: "session:cancelled", sessionId: this.id });
  }

  /** Convenience: detect claims via the registry and verify them in one call. */
  async detectAndVerify(text: string, pluginIds?: string[]): Promise<void> {
    const claims = this.deps.registry.detectAll(text, pluginIds);
    await this.verify(claims);
  }

  /** Verifies a pre-extracted claim list. Emits `claims:detected` with all
   *  claims marked pending immediately, then one `claim:updated` per claim
   *  as each resolves, then `session:completed` (skipped if cancelled). */
  async verify(claims: ExtractedClaim[]): Promise<void> {
    if (claims.length === 0 || this.cancelled) return;

    const pending: VerifiedClaim[] = claims.map((c) => ({ ...c, status: "pending" }));
    this.deps.bus.emit({ type: "claims:detected", sessionId: this.id, claims: pending });

    let cursor = 0;
    const worker = async (): Promise<void> => {
      while (!this.cancelled) {
        const index = cursor++;
        if (index >= claims.length) return;
        await this.verifyOne(claims[index]);
      }
    };

    const poolSize = Math.max(1, Math.min(this.deps.concurrency, claims.length));
    await Promise.all(Array.from({ length: poolSize }, () => worker()));

    if (!this.cancelled) {
      this.deps.bus.emit({ type: "session:completed", sessionId: this.id });
    }
  }

  private async verifyOne(claim: ExtractedClaim): Promise<void> {
    const plugin = this.deps.registry.get(claim.domain);
    if (!plugin) {
      this.emitUpdate({ ...claim, status: "error", error: `No plugin registered for domain "${claim.domain}"` });
      return;
    }

    const question = plugin.buildQuestion(claim);
    const { promise, controller } = this.getOrCreateDeduped(question, claim.raw_value);
    if (controller) this.ownedControllers.add(controller);

    try {
      const result = await promise;
      if (this.cancelled) return; // a stale result for a session that's moved on
      this.emitUpdate({ ...claim, status: "verified", result });
    } catch (err) {
      if (this.cancelled || (err instanceof TransportError && err.cancelled)) {
        this.emitUpdate({ ...claim, status: "cancelled" });
        return;
      }
      this.emitFallback(claim, plugin, question, err);
    } finally {
      if (controller) this.ownedControllers.delete(controller);
    }
  }

  private emitFallback(claim: ExtractedClaim, plugin: VerifierPlugin, question: string, err: unknown): void {
    const errorMessage = err instanceof Error ? err.message : "Verification failed";
    if (!plugin.offlineFallback) {
      this.emitUpdate({ ...claim, status: "error", error: errorMessage });
      return;
    }
    const fallback = plugin.offlineFallback(question, claim.raw_value);
    this.emitUpdate({
      ...claim,
      status: "verified",
      error: errorMessage,
      result: {
        question,
        raw_value: claim.raw_value,
        verified_value: fallback.verified_value,
        correction_applied: fallback.correction_applied,
        trust_score: fallback.trust_score,
        trust_color: trustPalette(fallback.trust_score).text,
        delta_pct: 0,
        dvl_version: "client-fallback",
        timestamp: new Date().toISOString(),
      },
    });
  }

  private emitUpdate(claim: VerifiedClaim): void {
    this.deps.bus.emit({ type: "claim:updated", sessionId: this.id, claim });
  }

  /**
   * Request dedup, engine-wide (shared across every session via
   * `deps.dedupCache`) — not session-scoped, since the whole point is
   * that a claim in message A and an identical claim in message B (or
   * the same message re-verified) share one network call.
   *
   * This is exactly why `controller` is only returned on a cache MISS:
   * if session A cancels and happens to be the one holding the
   * controller for a request session B's claim is also awaiting,
   * aborting it would silently break session B. Only the session that
   * actually created the request may cancel it; every other consumer of
   * a deduped promise can only stop caring about the result locally
   * (handled by the `this.cancelled` check after `await promise`) while
   * the underlying request runs to completion regardless.
   */
  private getOrCreateDeduped(question: string, rawValue: number): { promise: Promise<V1VerifyResponse>; controller: AbortController | null } {
    const key = `${question}|${rawValue}`;
    const now = Date.now();
    const cached = this.deps.dedupCache.get(key);
    if (cached && cached.expiresAt > now) {
      return { promise: cached.promise, controller: null };
    }

    const controller = new AbortController();
    const promise = this.deps.transport.verify({ question, raw_value: rawValue }, { signal: controller.signal });
    this.deps.dedupCache.set(key, { promise, expiresAt: now + this.deps.dedupTtlMs });
    return { promise, controller };
  }
}
