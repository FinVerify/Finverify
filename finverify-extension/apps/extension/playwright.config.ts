import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.ts",
  timeout: 30_000,
  fullyParallel: false, // each test launches its own persistent browser context; keep resource use predictable
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
  webServer: {
    command: "node e2e/setup/static-server.mjs",
    url: "http://127.0.0.1:8973/chatgpt-fixture.html",
    reuseExistingServer: !process.env.CI,
    timeout: 10_000,
  },
  use: {
    baseURL: "http://127.0.0.1:8973",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
});
