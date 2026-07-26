import { describe, it, expect } from "vitest";
import { PluginRegistry } from "../src/plugins/registry.js";
import type { VerifierPlugin } from "../src/plugins/types.js";
import type { ExtractedClaim } from "../src/types.js";

function makeClaim(overrides: Partial<ExtractedClaim> = {}): ExtractedClaim {
  return {
    id: "id-1",
    domain: "wrong-domain", // deliberately wrong, to test the registry re-stamps it
    sentence: "sentence",
    raw_value: 1,
    claim_type: "test",
    match: "1",
    offset: 0,
    ...overrides,
  };
}

function makePlugin(id: string, claims: ExtractedClaim[] = []): VerifierPlugin {
  return {
    id,
    displayName: id,
    detectClaims: () => claims,
    buildQuestion: () => "question?",
  };
}

describe("PluginRegistry", () => {
  it("registers and lists plugins", () => {
    const registry = new PluginRegistry();
    const plugin = makePlugin("finance");
    registry.register(plugin);
    expect(registry.list()).toEqual([plugin]);
    expect(registry.get("finance")).toBe(plugin);
  });

  it("throws on duplicate registration of the same id", () => {
    const registry = new PluginRegistry();
    registry.register(makePlugin("finance"));
    expect(() => registry.register(makePlugin("finance"))).toThrow(/already registered/i);
  });

  it("unregister removes a plugin", () => {
    const registry = new PluginRegistry();
    registry.register(makePlugin("finance"));
    registry.unregister("finance");
    expect(registry.get("finance")).toBeUndefined();
    expect(registry.list()).toEqual([]);
  });

  it("get returns undefined for an unknown id", () => {
    const registry = new PluginRegistry();
    expect(registry.get("nope")).toBeUndefined();
  });

  it("detectAll aggregates claims across every registered plugin", () => {
    const registry = new PluginRegistry();
    registry.register(makePlugin("finance", [makeClaim({ id: "f1" })]));
    registry.register(makePlugin("climate", [makeClaim({ id: "c1" })]));

    const claims = registry.detectAll("some text");
    expect(claims.map((c) => c.id).sort()).toEqual(["c1", "f1"]);
  });

  it("detectAll re-stamps claim.domain to the owning plugin's id, even if the plugin got it wrong", () => {
    const registry = new PluginRegistry();
    registry.register(makePlugin("finance", [makeClaim({ id: "f1", domain: "totally-wrong" })]));

    const claims = registry.detectAll("some text");
    expect(claims[0].domain).toBe("finance");
  });

  it("detectAll with pluginIds scopes detection to only the requested plugins", () => {
    const registry = new PluginRegistry();
    registry.register(makePlugin("finance", [makeClaim({ id: "f1" })]));
    registry.register(makePlugin("climate", [makeClaim({ id: "c1" })]));

    const claims = registry.detectAll("some text", ["climate"]);
    expect(claims.map((c) => c.id)).toEqual(["c1"]);
  });

  it("detectAll with an unknown pluginId in the list silently ignores it rather than throwing", () => {
    const registry = new PluginRegistry();
    registry.register(makePlugin("finance", [makeClaim({ id: "f1" })]));

    const claims = registry.detectAll("some text", ["finance", "nonexistent"]);
    expect(claims.map((c) => c.id)).toEqual(["f1"]);
  });

  it("detectAll returns an empty array when no plugins are registered", () => {
    const registry = new PluginRegistry();
    expect(registry.detectAll("some text")).toEqual([]);
  });
});
