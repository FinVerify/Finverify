import { describe, it, expect } from "vitest";
import { resolveAdapter, listAdapters } from "@/adapters/registry";

/**
 * Locks in the productization-pass fix: the registry must gate every
 * unverified adapter, including Claude. Claude's selectors are
 * self-documented as never having been run against a real, authenticated
 * claude.ai session (see adapters/claude/index.ts) — this test exists so
 * a future change can't silently flip that back to `verified: true`
 * (or add claude.ai to an allowlist) without a test failing here.
 */
describe("adapter registry — verification gate", () => {
  it("keeps every adapter's declared verified flag matching the intended launch matrix", () => {
    const byId = Object.fromEntries(listAdapters().map((a) => [a.id, a.verified]));
    expect(byId).toEqual({
      chatgpt: true,
      claude: false,
      gemini: false,
      copilot: false,
      perplexity: false,
    });
  });

  it("resolves the ChatGPT adapter as active on its domain", () => {
    expect(resolveAdapter("chatgpt.com")?.id).toBe("chatgpt");
    expect(resolveAdapter("chat.openai.com")?.id).toBe("chatgpt");
  });

  it("does NOT resolve the Claude adapter on claude.ai — implemented, but not yet manually verified", () => {
    expect(resolveAdapter("claude.ai")).toBeNull();
  });

  it("still exposes the Claude adapter in the registry listing (implementation kept, not deleted)", () => {
    const claude = listAdapters().find((a) => a.id === "claude");
    expect(claude).toBeDefined();
    expect(claude?.verified).toBe(false);
    expect(typeof claude?.matches).toBe("function");
    expect(claude?.matches("claude.ai")).toBe(true); // it *would* match — verification is the only gate
  });

  it("never resolves an adapter for an unrelated hostname", () => {
    expect(resolveAdapter("example.com")).toBeNull();
  });

  it("the dev-only allowUnverified escape hatch is opt-in and never reachable from the shipped build", () => {
    expect(resolveAdapter("claude.ai")).toBeNull();
    expect(resolveAdapter("claude.ai", { allowUnverified: true })?.id).toBe("claude");
  });
});
