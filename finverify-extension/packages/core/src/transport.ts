import type { HealthStatus, V1VerifyRequest, V1VerifyResponse } from "./types.js";

/**
 * How the engine reaches the actual verification backend. This is the
 * seam that makes the engine work identically inside a browser extension
 * (which must proxy network calls through a background worker to avoid
 * host-page CSP) and inside a VS Code extension/Desktop app/CLI/agent
 * (which can usually just call `fetch` directly).
 *
 * The engine (`engine.ts`/`session.ts`) only ever talks to this
 * interface — it has no idea whether `verify()` ends up going through
 * `chrome.runtime.sendMessage` or a direct HTTP call.
 */
export interface VerificationTransport {
  verify(request: V1VerifyRequest, options?: { signal?: AbortSignal }): Promise<V1VerifyResponse>;
  checkHealth?(): Promise<HealthStatus>;
}

export class TransportError extends Error {
  constructor(
    message: string,
    public readonly retryable: boolean,
    public readonly cancelled = false,
  ) {
    super(message);
    this.name = "TransportError";
  }
}
