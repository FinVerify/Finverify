import type { ExtractedClaim, HealthStatus, V1VerifyResponse } from "./types.js";
import type { VerificationTransport } from "./transport.js";
import type { VerifierPlugin } from "./plugins/types.js";
import { PluginRegistry } from "./plugins/registry.js";
import { EventBus, type EngineEvent, type EngineEventListener } from "./events.js";
import { VerificationSession } from "./session.js";

export interface VerificationEngineConfig {
  /** How the engine reaches the verification backend. Required — the
   *  engine has no default transport, since "how do I reach the network"
   *  is inherently environment-specific (browser extension vs. Node). */
  transport: VerificationTransport;
  /** Domain plugins active from construction. More can be added later via
   *  `registerPlugin()` — e.g. an Enterprise Dashboard might start with
   *  just `financePlugin` and let an admin enable `healthcarePlugin`
   *  later without restarting anything. */
  plugins?: VerifierPlugin[];
  /** Default concurrency for sessions that don't override it. */
  concurrency?: number;
  /** How long a deduped request stays cached engine-wide. */
  dedupTtlMs?: number;
}

const DEFAULT_CONCURRENCY = 3;
const DEFAULT_DEDUP_TTL_MS = 5 * 60_000;

/**
 * The engine is deliberately small: plugin registry + event bus + shared
 * dedup cache + session factory. All the actual verification-run logic
 * (batching, cancellation, dedup ownership, offline fallback) lives in
 * `VerificationSession` — the engine's job is just to hand out
 * consistently-configured sessions and give consumers one place to
 * subscribe to every session's events.
 */
export class VerificationEngine {
  private readonly registry = new PluginRegistry();
  private readonly bus = new EventBus();
  private readonly dedupCache: Map<string, { promise: Promise<V1VerifyResponse>; expiresAt: number }> = new Map();
  private readonly transport: VerificationTransport;
  private readonly defaultConcurrency: number;
  private readonly dedupTtlMs: number;

  constructor(config: VerificationEngineConfig) {
    this.transport = config.transport;
    this.defaultConcurrency = config.concurrency ?? DEFAULT_CONCURRENCY;
    this.dedupTtlMs = config.dedupTtlMs ?? DEFAULT_DEDUP_TTL_MS;
    for (const plugin of config.plugins ?? []) this.registry.register(plugin);
  }

  registerPlugin(plugin: VerifierPlugin): void {
    this.registry.register(plugin);
  }

  unregisterPlugin(pluginId: string): void {
    this.registry.unregister(pluginId);
  }

  listPlugins(): VerifierPlugin[] {
    return this.registry.list();
  }

  /** Subscribe to every event from every session this engine creates.
   *  Returns an unsubscribe function. */
  on(listener: EngineEventListener): () => void {
    return this.bus.on(listener);
  }

  /** Runs every registered plugin (or a specific subset by id) over
   *  `text`. Pure/synchronous — no network involved; call `createSession()`
   *  + `session.verify(claims)` to actually verify what this finds. */
  detectClaims(text: string, pluginIds?: string[]): ExtractedClaim[] {
    return this.registry.detectAll(text, pluginIds);
  }

  /** Creates a new cancellable verification session. Create one per
   *  logical unit of work (one chat message, one document, one cell
   *  range) so cancelling it can't affect anything else. */
  createSession(options: { concurrency?: number; modelSource?: string } = {}): VerificationSession {
    return new VerificationSession({
      registry: this.registry,
      transport: this.transport,
      bus: this.bus,
      dedupCache: this.dedupCache,
      dedupTtlMs: this.dedupTtlMs,
      concurrency: options.concurrency ?? this.defaultConcurrency,
      modelSource: options.modelSource,
    });
  }

  async checkHealth(): Promise<HealthStatus> {
    if (!this.transport.checkHealth) {
      throw new Error("This engine's transport does not implement checkHealth().");
    }
    return this.transport.checkHealth();
  }
}

export type { EngineEvent, EngineEventListener };
