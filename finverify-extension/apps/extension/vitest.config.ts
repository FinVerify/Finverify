import { defineConfig } from "vitest/config";
import { resolve } from "path";

// Pure-logic unit tests only (no DOM, no chrome.* mocking) — anything
// touching the live page belongs in e2e/ under Playwright instead. Kept
// deliberately separate from that suite so these run in milliseconds
// with zero browser dependency.
export default defineConfig({
  resolve: { alias: { "@": resolve(__dirname, "src") } },
  test: {
    include: ["src/**/*.test.ts"],
    environment: "node",
  },
});
