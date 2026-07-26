import { describe, it, expect, vi } from "vitest";
import { VerificationSession } from "../src/session.js";
import { PluginRegistry } from "../src/plugins/registry.js";
import { EventBus } from "../src/events.js";
import { TransportError } from "../src/transport.js";
import type { VerificationTransport } from "../src/transport.js";
import type { VerifierPlugin } from "../src/plugins/types.js";
import type { ExtractedClaim, V1VerifyResponse } from "../src/types.js";

function makeClaim(overrides: Partial<ExtractedClaim> = {}): ExtractedClaim {
  return {
    id: `id-${Math.random()}`,
    domain: "finance",
    sentence: "sentence",
    raw_value: 1,
    claim_type: "test",
    match: "1",
    offset: 0,
    ...overrides,
  };
}

function makeResponse(overrides: Partial<V1VerifyResponse> = {}): V1VerifyResponse {
  return {
    question: "q",
    raw_value: 1,
    verified_value: 1,
    correction_applied: null,
    trust_score: "HIGH",
    trust_color: "#0f8",
    delta_pct: 0,
    dvl_version: "test",
    timestamp: "t",
    ...overrides,
  };
}

const financePlugin: VerifierPlugin = {
  id: "finance",
  displayName: "Finance",
  detectClaims: () => [],
  buildQuestion: (claim) => `question-for-${claim.id}`,
  offlineFallback: (_q, rawValue) => ({ verified_value: rawValue, correction_applied: "fallback_applied", trust_score: "MEDIUM" }),
};

const pluginWithoutFallback: VerifierPlugin = {
  id: "no-fallback",
  displayName: "No Fallback",
  detectClaims: () => [],
  buildQuestion: () => "question",
};

interface Harness {
  session: VerificationSession;
  transport: VerificationTransport;
  events: any[];
  registry: PluginRegistry;
  dedupCache: Map<string, { promise: Promise<V1VerifyResponse>; expiresAt: number }>;
}

function makeHarness(options: {
  verifyImpl?: VerificationTransport["verify"];
  plugins?: VerifierPlugin[];
  concurrency?: number;
  dedupTtlMs?: number;
  sharedDedupCache?: Map<string, { promise: Promise<V1VerifyResponse>; expiresAt: number }>;
  sharedBus?: EventBus;
}): Harness {
  const registry = new PluginRegistry();
  for (const p of options.plugins ?? [financePlugin]) registry.register(p);

  const bus = options.sharedBus ?? new EventBus();
  const events: any[] = [];
  bus.on((e) => events.push(e));

  const dedupCache = options.sharedDedupCache ?? new Map();

  const transport: VerificationTransport = {
    verify: options.verifyImpl ?? (async (request) => makeResponse({ question: request.question, raw_value: request.raw_value, verified_value: request.raw_value })),
  };

  const session = new VerificationSession({
    registry,
    transport,
    bus,
    dedupCache,
    dedupTtlMs: options.dedupTtlMs ?? 5 * 60_000,
    concurrency: options.concurrency ?? 3,
  });

  return { session, transport, events, registry, dedupCache };
}

describe("VerificationSession", () => {
  it("verify() with an empty claim list does nothing and emits no events", async () => {
    const { session, events } = makeHarness({});
    await session.verify([]);
    expect(events).toEqual([]);
  });

  it("emits claims:detected with all claims pending, then claim:updated per claim, then session:completed", async () => {
    const { session, events } = makeHarness({});
    const claims = [makeClaim({ id: "a" }), makeClaim({ id: "b" })];
    await session.verify(claims);

    expect(events[0].type).toBe("claims:detected");
    expect(events[0].claims.map((c: any) => c.status)).toEqual(["pending", "pending"]);

    const updateEvents = events.filter((e) => e.type === "claim:updated");
    expect(updateEvents).toHaveLength(2);
    expect(updateEvents.every((e) => e.claim.status === "verified")).toBe(true);

    expect(events.at(-1).type).toBe("session:completed");
  });

  it("verifies all claims even with concurrency lower than the claim count", async () => {
    const { session, events } = makeHarness({ concurrency: 2 });
    const claims = Array.from({ length: 7 }, (_, i) => makeClaim({ id: `c${i}`, raw_value: i }));
    await session.verify(claims);

    const updateEvents = events.filter((e) => e.type === "claim:updated");
    expect(updateEvents).toHaveLength(7);
    expect(updateEvents.every((e) => e.claim.status === "verified")).toBe(true);
  });

  it("marks a claim as error (with message) when its domain has no registered plugin", async () => {
    const { session, events } = makeHarness({});
    await session.verify([makeClaim({ id: "orphan", domain: "nonexistent" })]);

    const update = events.find((e) => e.type === "claim:updated");
    expect(update.claim.status).toBe("error");
    expect(update.claim.error).toMatch(/no plugin registered/i);
  });

  it("falls back to the plugin's offlineFallback when the transport rejects, if one is provided", async () => {
    const { session, events } = makeHarness({
      verifyImpl: async () => {
        throw new TransportError("backend down", true);
      },
    });
    await session.verify([makeClaim({ id: "a", raw_value: 42 })]);

    const update = events.find((e) => e.type === "claim:updated");
    expect(update.claim.status).toBe("verified");
    expect(update.claim.error).toBe("backend down");
    expect(update.claim.result.correction_applied).toBe("fallback_applied");
    expect(update.claim.result.dvl_version).toBe("client-fallback");
  });

  it("marks a claim as error (not verified) when the transport rejects and the plugin has no offlineFallback", async () => {
    const { session, events } = makeHarness({
      plugins: [pluginWithoutFallback],
      verifyImpl: async () => {
        throw new TransportError("backend down", true);
      },
    });
    await session.verify([makeClaim({ id: "a", domain: "no-fallback" })]);

    const update = events.find((e) => e.type === "claim:updated");
    expect(update.claim.status).toBe("error");
    expect(update.claim.error).toBe("backend down");
    expect(update.claim.result).toBeUndefined();
  });

  it("dedups two claims that produce the same question and raw_value into a single transport call", async () => {
    const verifyImpl = vi.fn(async (request) => makeResponse({ question: request.question, raw_value: request.raw_value }));
    const plugin: VerifierPlugin = { ...financePlugin, buildQuestion: () => "same-question" };
    const { session, events } = makeHarness({ plugins: [plugin], verifyImpl });

    await session.verify([makeClaim({ id: "a", raw_value: 5 }), makeClaim({ id: "b", raw_value: 5 })]);

    expect(verifyImpl).toHaveBeenCalledTimes(1);
    const updates = events.filter((e) => e.type === "claim:updated");
    expect(updates).toHaveLength(2);
    expect(updates.every((u) => u.claim.status === "verified")).toBe(true);
  });

  it("does NOT dedup claims with the same raw_value but different questions (different claim_type)", async () => {
    const verifyImpl = vi.fn(async (request) => makeResponse({ question: request.question, raw_value: request.raw_value }));
    let callN = 0;
    const plugin: VerifierPlugin = { ...financePlugin, buildQuestion: () => `question-${callN++}` };
    const { session } = makeHarness({ plugins: [plugin], verifyImpl });

    await session.verify([makeClaim({ id: "a", raw_value: 5 }), makeClaim({ id: "b", raw_value: 5 })]);
    expect(verifyImpl).toHaveBeenCalledTimes(2);
  });

  it("shares a dedup cache entry across two different sessions", async () => {
    const verifyImpl = vi.fn(async (request) => makeResponse({ question: request.question, raw_value: request.raw_value }));
    const sharedDedupCache = new Map<string, { promise: Promise<V1VerifyResponse>; expiresAt: number }>();
    const plugin: VerifierPlugin = { ...financePlugin, buildQuestion: () => "same-question" };

    const h1 = makeHarness({ plugins: [plugin], verifyImpl, sharedDedupCache });
    const h2 = makeHarness({ plugins: [plugin], verifyImpl, sharedDedupCache });

    await Promise.all([h1.session.verify([makeClaim({ id: "a", raw_value: 9 })]), h2.session.verify([makeClaim({ id: "b", raw_value: 9 })])]);

    expect(verifyImpl).toHaveBeenCalledTimes(1);
  });

  it("cancel() marks the session cancelled and emits session:cancelled", async () => {
    const { session, events } = makeHarness({
      verifyImpl: (_req, options) =>
        new Promise((_resolve, reject) => {
          options?.signal?.addEventListener("abort", () => reject(new TransportError("cancelled", false, true)));
        }),
    });
    const claims = [makeClaim({ id: "a" })];
    const promise = session.verify(claims);
    await Promise.resolve();
    await Promise.resolve();
    session.cancel();
    await promise;

    expect(session.isCancelled).toBe(true);
    expect(events.some((e) => e.type === "session:cancelled")).toBe(true);
  });

  it("cancel() aborts the underlying transport call when this session created it (not deduped)", async () => {
    let capturedSignal: AbortSignal | undefined;
    const { session } = makeHarness({
      verifyImpl: (_req, options) => {
        capturedSignal = options?.signal;
        return new Promise((_resolve, reject) => {
          options?.signal?.addEventListener("abort", () => reject(new TransportError("cancelled", false, true)));
        });
      },
    });

    const promise = session.verify([makeClaim({ id: "a" })]);
    // let the microtask that calls transport.verify() run
    await Promise.resolve();
    await Promise.resolve();
    session.cancel();
    await promise;

    expect(capturedSignal?.aborted).toBe(true);
  });

  it("cancelling a session that only REUSED a deduped request does NOT abort the underlying request another session still needs", async () => {
    const sharedDedupCache = new Map<string, { promise: Promise<V1VerifyResponse>; expiresAt: number }>();
    const plugin: VerifierPlugin = { ...financePlugin, buildQuestion: () => "same-question" };
    let capturedSignal: AbortSignal | undefined;

    let resolveTransport!: (v: V1VerifyResponse) => void;
    const pendingPromise = new Promise<V1VerifyResponse>((resolve) => {
      resolveTransport = resolve;
    });

    const h1 = makeHarness({
      plugins: [plugin],
      sharedDedupCache,
      verifyImpl: (_req, options) => {
        capturedSignal = options?.signal;
        return pendingPromise;
      },
    });
    const h2 = makeHarness({ plugins: [plugin], sharedDedupCache, verifyImpl: () => pendingPromise });

    const p1 = h1.session.verify([makeClaim({ id: "a", raw_value: 3 })]);
    await Promise.resolve();
    await Promise.resolve();
    const p2 = h2.session.verify([makeClaim({ id: "b", raw_value: 3 })]);
    await Promise.resolve();

    // h2 only reused h1's in-flight request (cache hit) — cancelling h2
    // must NOT abort the signal h1's transport call is actually using.
    h2.session.cancel();
    expect(capturedSignal?.aborted).toBe(false);

    resolveTransport(makeResponse({ raw_value: 3, verified_value: 3 }));
    await p1;
    await p2;

    const h1Update = h1.events.find((e) => e.type === "claim:updated");
    expect(h1Update.claim.status).toBe("verified");
  });

  it("a claim belonging to a cancelled session is marked cancelled once its (non-shared) request rejects due to abort", async () => {
    const { session, events } = makeHarness({
      verifyImpl: async (_req, options) => {
        return new Promise((_resolve, reject) => {
          options?.signal?.addEventListener("abort", () => reject(new TransportError("cancelled", false, true)));
        });
      },
    });

    const promise = session.verify([makeClaim({ id: "a" })]);
    await Promise.resolve();
    await Promise.resolve();
    session.cancel();
    await promise;

    const update = events.find((e) => e.type === "claim:updated");
    expect(update.claim.status).toBe("cancelled");
  });

  it("detectAndVerify() runs registry detection and verification together", async () => {
    const claimsToReturn = [makeClaim({ id: "x" })];
    const plugin: VerifierPlugin = { ...financePlugin, detectClaims: () => claimsToReturn };
    const { session, events } = makeHarness({ plugins: [plugin] });

    await session.detectAndVerify("some source text");

    expect(events[0].type).toBe("claims:detected");
    expect(events[0].claims[0].id).toBe("x");
  });

  it("does not emit session:completed if the session was cancelled before all claims finished", async () => {
    const { session, events } = makeHarness({
      verifyImpl: (_req, options) =>
        new Promise((_resolve, reject) => {
          options?.signal?.addEventListener("abort", () => reject(new TransportError("cancelled", false, true)));
        }),
    });
    const promise = session.verify([makeClaim({ id: "a" }), makeClaim({ id: "b" })]);
    await Promise.resolve();
    await Promise.resolve();
    session.cancel();
    await promise;

    expect(events.some((e) => e.type === "session:completed")).toBe(false);
  });
});
