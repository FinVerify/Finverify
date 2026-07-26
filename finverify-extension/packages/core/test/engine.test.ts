import { describe, it, expect, vi } from "vitest";
import { VerificationEngine } from "../src/engine.js";
import type { VerifierPlugin } from "../src/plugins/types.js";
import type { VerificationTransport } from "../src/transport.js";
import type { ExtractedClaim } from "../src/types.js";

function makePlugin(id: string, claims: ExtractedClaim[] = []): VerifierPlugin {
  return {
    id,
    displayName: id,
    detectClaims: () => claims,
    buildQuestion: () => "q",
  };
}

function makeClaim(id: string): ExtractedClaim {
  return { id, domain: "x", sentence: "s", raw_value: 1, claim_type: "t", match: "1", offset: 0 };
}

describe("VerificationEngine", () => {
  it("registers plugins passed at construction and exposes them via listPlugins", () => {
    const transport: VerificationTransport = { verify: async (r) => ({ ...r, verified_value: r.raw_value, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v", timestamp: "t" }) };
    const plugin = makePlugin("finance");
    const engine = new VerificationEngine({ transport, plugins: [plugin] });
    expect(engine.listPlugins()).toEqual([plugin]);
  });

  it("registerPlugin adds a plugin after construction", () => {
    const transport: VerificationTransport = { verify: async (r) => ({ ...r, verified_value: r.raw_value, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v", timestamp: "t" }) };
    const engine = new VerificationEngine({ transport });
    engine.registerPlugin(makePlugin("climate"));
    expect(engine.listPlugins().map((p) => p.id)).toEqual(["climate"]);
  });

  it("unregisterPlugin removes a plugin", () => {
    const transport: VerificationTransport = { verify: async (r) => ({ ...r, verified_value: r.raw_value, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v", timestamp: "t" }) };
    const engine = new VerificationEngine({ transport, plugins: [makePlugin("finance")] });
    engine.unregisterPlugin("finance");
    expect(engine.listPlugins()).toEqual([]);
  });

  it("detectClaims delegates to the registered plugins and aggregates results", () => {
    const transport: VerificationTransport = { verify: async (r) => ({ ...r, verified_value: r.raw_value, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v", timestamp: "t" }) };
    const engine = new VerificationEngine({
      transport,
      plugins: [makePlugin("finance", [makeClaim("f1")]), makePlugin("climate", [makeClaim("c1")])],
    });
    const claims = engine.detectClaims("text");
    expect(claims.map((c) => c.id).sort()).toEqual(["c1", "f1"]);
  });

  it("detectClaims respects a pluginIds filter", () => {
    const transport: VerificationTransport = { verify: async (r) => ({ ...r, verified_value: r.raw_value, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v", timestamp: "t" }) };
    const engine = new VerificationEngine({
      transport,
      plugins: [makePlugin("finance", [makeClaim("f1")]), makePlugin("climate", [makeClaim("c1")])],
    });
    expect(engine.detectClaims("text", ["climate"]).map((c) => c.id)).toEqual(["c1"]);
  });

  it("createSession produces sessions whose events are all visible via engine.on", async () => {
    const transport: VerificationTransport = {
      verify: async (r) => ({ ...r, verified_value: r.raw_value, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v", timestamp: "t" }),
    };
    const engine = new VerificationEngine({ transport, plugins: [makePlugin("finance")] });

    const events: any[] = [];
    engine.on((e) => events.push(e));

    const session = engine.createSession();
    await session.verify([makeClaim("a") /* domain "x", but registry has "finance" registered */]);

    // Claim's domain "x" has no matching plugin -> should surface as an
    // error event, proving the session created by the engine is wired to
    // the engine's own registry (not some disconnected empty one).
    expect(events.some((e) => e.type === "claim:updated" && e.claim.status === "error")).toBe(true);
  });

  it("on() returns an unsubscribe function that stops delivering events from sessions created after unsubscription", async () => {
    const transport: VerificationTransport = {
      verify: async (r) => ({ ...r, verified_value: r.raw_value, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v", timestamp: "t" }),
    };
    const engine = new VerificationEngine({ transport, plugins: [makePlugin("finance")] });
    const listener = vi.fn();
    const unsubscribe = engine.on(listener);
    unsubscribe();

    const session = engine.createSession();
    await session.verify([makeClaim("a")]);
    expect(listener).not.toHaveBeenCalled();
  });

  it("checkHealth delegates to the transport's checkHealth", async () => {
    const checkHealth = vi.fn().mockResolvedValue({ status: "ok", dvl: "online", llm: "online", model: "m" });
    const transport: VerificationTransport = { verify: async () => { throw new Error("unused"); }, checkHealth };
    const engine = new VerificationEngine({ transport });
    await expect(engine.checkHealth()).resolves.toEqual({ status: "ok", dvl: "online", llm: "online", model: "m" });
    expect(checkHealth).toHaveBeenCalledTimes(1);
  });

  it("checkHealth throws a clear error if the transport doesn't implement it", async () => {
    const transport: VerificationTransport = { verify: async () => { throw new Error("unused"); } };
    const engine = new VerificationEngine({ transport });
    await expect(engine.checkHealth()).rejects.toThrow(/does not implement checkHealth/i);
  });

  it("two sessions created by the same engine share the dedup cache (verified via call count)", async () => {
    const verify = vi.fn(async (r: any) => ({ ...r, verified_value: r.raw_value, correction_applied: null, trust_score: "HIGH", trust_color: "#0f8", delta_pct: 0, dvl_version: "v", timestamp: "t" }));
    const plugin: VerifierPlugin = { id: "finance", displayName: "f", detectClaims: () => [], buildQuestion: () => "same-question" };
    const engine = new VerificationEngine({ transport: { verify }, plugins: [plugin] });

    const s1 = engine.createSession();
    const s2 = engine.createSession();
    await Promise.all([
      s1.verify([{ id: "a", domain: "finance", sentence: "s", raw_value: 7, claim_type: "t", match: "7", offset: 0 }]),
      s2.verify([{ id: "b", domain: "finance", sentence: "s", raw_value: 7, claim_type: "t", match: "7", offset: 0 }]),
    ]);

    expect(verify).toHaveBeenCalledTimes(1);
  });
});
