import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { createHttpTransport } from "../src/http-transport.js";
import { TransportError } from "../src/transport.js";

/** A fetch mock that behaves like the real thing with respect to
 *  AbortSignal: if the passed signal is (or becomes) aborted, it rejects
 *  with a DOMException named "AbortError", matching real fetch behavior. */
function fetchRespectingAbort(handler: (input: string, init: RequestInit) => Promise<Response> | Response): typeof fetch {
  return vi.fn(async (input: any, init: any = {}) => {
    const signal: AbortSignal | undefined = init.signal;
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");

    return new Promise<Response>((resolve, reject) => {
      const onAbort = () => reject(new DOMException("Aborted", "AbortError"));
      signal?.addEventListener("abort", onAbort, { once: true });
      Promise.resolve(handler(input, init)).then(
        (res) => {
          signal?.removeEventListener("abort", onAbort);
          resolve(res);
        },
        (err) => {
          signal?.removeEventListener("abort", onAbort);
          reject(err);
        },
      );
    });
  }) as unknown as typeof fetch;
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("createHttpTransport", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it("verify() returns the parsed response on a 200", async () => {
    const body = {
      question: "q",
      raw_value: 1,
      verified_value: 1,
      correction_applied: null,
      trust_score: "HIGH",
      trust_color: "#0f8",
      delta_pct: 0,
      dvl_version: "v1",
      timestamp: "t",
    };
    vi.stubGlobal("fetch", fetchRespectingAbort(() => jsonResponse(body)));

    const transport = createHttpTransport({ maxRetries: 0 });
    const result = await transport.verify({ question: "q", raw_value: 1 });
    expect(result).toEqual(body);
  });

  it("retries on a 500 and eventually succeeds", async () => {
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      fetchRespectingAbort(() => {
        calls++;
        if (calls < 2) return jsonResponse({ error: "boom" }, 500);
        return jsonResponse({ question: "q", raw_value: 1, verified_value: 1, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v1", timestamp: "t" });
      }),
    );

    const transport = createHttpTransport({ maxRetries: 3 });
    const promise = transport.verify({ question: "q", raw_value: 1 });
    await vi.runAllTimersAsync();
    const result = await promise;
    expect(calls).toBe(2);
    expect(result.verified_value).toBe(1);
  });

  it("does not retry a 400 and rejects with a non-retryable TransportError", async () => {
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      fetchRespectingAbort(() => {
        calls++;
        return jsonResponse({ error: "bad request" }, 400);
      }),
    );

    const transport = createHttpTransport({ maxRetries: 3 });
    await expect(transport.verify({ question: "q", raw_value: 1 })).rejects.toThrow(/HTTP 400/);
    expect(calls).toBe(1);
  });

  it("retries on a 429 (rate limited)", async () => {
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      fetchRespectingAbort(() => {
        calls++;
        if (calls < 2) return jsonResponse({ error: "rate limited" }, 429);
        return jsonResponse({ question: "q", raw_value: 1, verified_value: 1, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v1", timestamp: "t" });
      }),
    );

    const transport = createHttpTransport({ maxRetries: 3 });
    const promise = transport.verify({ question: "q", raw_value: 1 });
    await vi.runAllTimersAsync();
    await expect(promise).resolves.toMatchObject({ verified_value: 1 });
    expect(calls).toBe(2);
  });

  it("propagates cancellation via an externally-supplied AbortSignal without retrying", async () => {
    vi.stubGlobal(
      "fetch",
      fetchRespectingAbort(() => new Promise<Response>(() => {})), // never resolves on its own
    );

    const controller = new AbortController();
    const transport = createHttpTransport({ maxRetries: 5 });
    const promise = transport.verify({ question: "q", raw_value: 1 }, { signal: controller.signal });

    const assertion = expect(promise).rejects.toThrow(/cancelled/i);
    await vi.advanceTimersByTimeAsync(0);
    controller.abort();
    await vi.runAllTimersAsync();
    await assertion;
  });

  it("times out and treats it as a retryable network-level failure", async () => {
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      fetchRespectingAbort(() => {
        calls++;
        if (calls === 1) return new Promise<Response>(() => {}); // hangs forever -> internal timeout fires
        return jsonResponse({ question: "q", raw_value: 1, verified_value: 1, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v1", timestamp: "t" });
      }),
    );

    const transport = createHttpTransport({ timeoutMs: 50, maxRetries: 2 });
    const promise = transport.verify({ question: "q", raw_value: 1 });
    await vi.runAllTimersAsync();
    const result = await promise;
    expect(result.verified_value).toBe(1);
    expect(calls).toBe(2);
  });

  it("checkHealth returns the parsed health status on success", async () => {
    vi.stubGlobal("fetch", fetchRespectingAbort(() => jsonResponse({ status: "ok", dvl: "online", llm: "online", model: "m" })));
    const transport = createHttpTransport();
    await expect(transport.checkHealth!()).resolves.toEqual({ status: "ok", dvl: "online", llm: "online", model: "m" });
  });

  it("checkHealth rejects with a TransportError on a non-2xx response", async () => {
    vi.stubGlobal("fetch", fetchRespectingAbort(() => jsonResponse({}, 503)));
    const transport = createHttpTransport();
    await expect(transport.checkHealth!()).rejects.toBeInstanceOf(TransportError);
  });
});
