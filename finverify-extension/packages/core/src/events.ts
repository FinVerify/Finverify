import type { VerifiedClaim } from "./types.js";

/**
 * Every state change the engine can produce, all tagged with the
 * `sessionId` they belong to. UI layers (React, a VS Code webview, an
 * Enterprise Dashboard) subscribe to these instead of the engine handing
 * back a promise-per-claim — that's what makes incremental/streaming
 * verification possible: a consumer can render partial state as events
 * arrive rather than waiting for one big batch to resolve.
 */
export type EngineEvent =
  | { type: "claims:detected"; sessionId: string; claims: VerifiedClaim[] }
  | { type: "claim:updated"; sessionId: string; claim: VerifiedClaim }
  | { type: "session:completed"; sessionId: string }
  | { type: "session:cancelled"; sessionId: string };

export type EngineEventListener = (event: EngineEvent) => void;

/** Minimal typed pub/sub. Deliberately not Node's EventEmitter (which
 *  isn't available in a browser content-script context without a
 *  polyfill) and not a third-party dependency — this is small enough
 *  that owning it outright is simpler than managing that dependency
 *  across every environment @finverify/core needs to run in. */
export class EventBus {
  private readonly listeners = new Set<EngineEventListener>();

  on(listener: EngineEventListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  emit(event: EngineEvent): void {
    for (const listener of this.listeners) {
      listener(event);
    }
  }
}
