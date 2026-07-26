import type { HealthStatus, V1VerifyRequest, V1VerifyResponse } from "./types.js";
import type { VerificationTransport } from "./transport.js";
import { TransportError } from "./transport.js";
import { withRetry } from "./retry.js";

const DEFAULT_TIMEOUT_MS = 10_000;

/** 5xx and 429 are worth retrying; other 4xx are not — retrying a
 *  malformed request just burns rate-limit budget for no benefit. */
function isRetryableStatus(status: number): boolean {
  return status === 429 || status >= 500;
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number, external?: AbortSignal): Promise<Response> {
  const controller = new AbortController();
  const onExternalAbort = () => controller.abort();
  external?.addEventListener("abort", onExternalAbort, { once: true });
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
    external?.removeEventListener("abort", onExternalAbort);
  }
}

export interface HttpTransportOptions {
  baseUrl?: string;
  timeoutMs?: number;
  maxRetries?: number;
}

/** Same backend, same base URL, as frontend/lib/api.ts and
 *  frontend/public/widget.js — every FinVerify client, whatever it is,
 *  talks to the same DVL API. */
const DEFAULT_BASE_URL = "https://aadi2026-finverify-api.hf.space";

export function createHttpTransport(options: HttpTransportOptions = {}): VerificationTransport {
  const baseUrl = options.baseUrl ?? DEFAULT_BASE_URL;
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const maxRetries = options.maxRetries;

  return {
    async verify(request: V1VerifyRequest, verifyOptions?: { signal?: AbortSignal }): Promise<V1VerifyResponse> {
      return withRetry(
        async () => {
          let res: Response;
          try {
            res = await fetchWithTimeout(
              `${baseUrl}/v1/verify`,
              { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(request) },
              timeoutMs,
              verifyOptions?.signal,
            );
          } catch (err) {
            const isAbort = err instanceof DOMException && err.name === "AbortError";
            if (isAbort && verifyOptions?.signal?.aborted) {
              throw new TransportError("Verification cancelled", false, true);
            }
            const message = err instanceof Error ? err.message : "Network error";
            throw new TransportError(message, true); // timeout or network error: retryable
          }

          if (!res.ok) {
            const body = await res.text();
            throw new TransportError(`HTTP ${res.status}: ${body.slice(0, 200)}`, isRetryableStatus(res.status));
          }
          return (await res.json()) as V1VerifyResponse;
        },
        { signal: verifyOptions?.signal, maxRetries },
      );
    },

    async checkHealth(): Promise<HealthStatus> {
      const res = await fetchWithTimeout(`${baseUrl}/health`, {}, 5_000);
      if (!res.ok) throw new TransportError(`HTTP ${res.status}`, isRetryableStatus(res.status));
      return (await res.json()) as HealthStatus;
    },
  };
}
