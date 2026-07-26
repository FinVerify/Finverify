import { TransportError } from "./transport.js";

const DEFAULT_MAX_RETRIES = 3;
const DEFAULT_BASE_DELAY_MS = 400;

export interface RetryOptions {
  maxRetries?: number;
  baseDelayMs?: number;
  signal?: AbortSignal;
}

function jitteredDelay(attempt: number, baseDelayMs: number): number {
  const exp = baseDelayMs * 2 ** attempt;
  const jitter = Math.random() * exp * 0.3;
  return exp + jitter;
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new TransportError("Aborted before backoff delay", false, true));
      return;
    }
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        reject(new TransportError("Aborted during backoff delay", false, true));
      },
      { once: true },
    );
  });
}

/**
 * Runs `attempt()` with exponential backoff + jitter. `attempt()` should
 * throw a `TransportError` to signal whether a failure is retryable;
 * anything else thrown is treated as non-retryable and rethrown
 * immediately. A `TransportError` with `cancelled: true` also aborts
 * retrying immediately regardless of `retryable`.
 */
export async function withRetry<T>(attempt: (attemptNumber: number) => Promise<T>, options: RetryOptions = {}): Promise<T> {
  const maxRetries = options.maxRetries ?? DEFAULT_MAX_RETRIES;
  const baseDelayMs = options.baseDelayMs ?? DEFAULT_BASE_DELAY_MS;

  for (let attemptNumber = 0; attemptNumber <= maxRetries; attemptNumber++) {
    if (options.signal?.aborted) {
      throw new TransportError("Cancelled", false, true);
    }
    try {
      return await attempt(attemptNumber);
    } catch (err) {
      const isTransportError = err instanceof TransportError;
      const cancelled = isTransportError && err.cancelled;
      const retryable = isTransportError ? err.retryable : true; // unknown errors: assume transient
      if (cancelled || !retryable || attemptNumber >= maxRetries) throw err;
      await sleep(jitteredDelay(attemptNumber, baseDelayMs), options.signal);
    }
  }
  throw new TransportError("Exhausted retries", false);
}
