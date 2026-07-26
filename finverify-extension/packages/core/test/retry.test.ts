import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { withRetry } from "../src/retry.js";
import { TransportError } from "../src/transport.js";

describe("withRetry", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns the result immediately on first success, no retries", async () => {
    const attempt = vi.fn().mockResolvedValue("ok");
    const result = await withRetry(attempt);
    expect(result).toBe("ok");
    expect(attempt).toHaveBeenCalledTimes(1);
  });

  it("retries a retryable TransportError up to maxRetries, then succeeds", async () => {
    let calls = 0;
    const attempt = vi.fn(async () => {
      calls++;
      if (calls < 3) throw new TransportError("transient", true);
      return "recovered";
    });

    const promise = withRetry(attempt, { maxRetries: 5, baseDelayMs: 10 });
    await vi.runAllTimersAsync();
    const result = await promise;

    expect(result).toBe("recovered");
    expect(attempt).toHaveBeenCalledTimes(3);
  });

  it("does not retry a non-retryable TransportError and rejects immediately", async () => {
    const attempt = vi.fn(async () => {
      throw new TransportError("bad request", false);
    });

    await expect(withRetry(attempt, { maxRetries: 5 })).rejects.toThrow("bad request");
    expect(attempt).toHaveBeenCalledTimes(1);
  });

  it("stops retrying immediately on a cancelled TransportError even if marked retryable", async () => {
    const attempt = vi.fn(async () => {
      throw new TransportError("cancelled mid-flight", true, true);
    });

    await expect(withRetry(attempt, { maxRetries: 5 })).rejects.toThrow("cancelled mid-flight");
    expect(attempt).toHaveBeenCalledTimes(1);
  });

  it("gives up after exhausting maxRetries and rethrows the last error", async () => {
    const attempt = vi.fn(async () => {
      throw new TransportError("still failing", true);
    });

    const promise = withRetry(attempt, { maxRetries: 2, baseDelayMs: 10 });
    const assertion = expect(promise).rejects.toThrow("still failing");
    await vi.runAllTimersAsync();
    await assertion;
    expect(attempt).toHaveBeenCalledTimes(3); // initial + 2 retries
  });

  it("treats a thrown error that isn't a TransportError as retryable", async () => {
    let calls = 0;
    const attempt = vi.fn(async () => {
      calls++;
      if (calls < 2) throw new Error("plain network error");
      return "ok";
    });

    const promise = withRetry(attempt, { maxRetries: 3, baseDelayMs: 10 });
    await vi.runAllTimersAsync();
    expect(await promise).toBe("ok");
    expect(attempt).toHaveBeenCalledTimes(2);
  });

  it("rejects immediately if the signal is already aborted before the first attempt", async () => {
    const controller = new AbortController();
    controller.abort();
    const attempt = vi.fn().mockResolvedValue("should not run");

    await expect(withRetry(attempt, { signal: controller.signal })).rejects.toThrow(/cancelled/i);
    expect(attempt).not.toHaveBeenCalled();
  });

  it("aborts an in-progress backoff delay when the signal fires during the wait", async () => {
    const controller = new AbortController();
    let calls = 0;
    const attempt = vi.fn(async () => {
      calls++;
      throw new TransportError("transient", true);
    });

    const promise = withRetry(attempt, { maxRetries: 5, baseDelayMs: 1000, signal: controller.signal });
    const assertion = expect(promise).rejects.toThrow(/aborted/i);

    // Let the first attempt run and start its backoff sleep, then abort
    // mid-delay rather than letting the timer fire naturally.
    await vi.advanceTimersByTimeAsync(0);
    controller.abort();
    await vi.runAllTimersAsync();
    await assertion;
    expect(calls).toBe(1);
  });
});
