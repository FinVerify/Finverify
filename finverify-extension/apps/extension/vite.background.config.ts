import { defineConfig } from "vite";
import { resolve } from "path";

// IIFE here too, even though MV3 background workers *can* be declared
// "type": "module" — using IIFE for every entry means one build strategy
// to reason about instead of two, and it sidesteps needing
// web_accessible_resources for any shared chunk.
export default defineConfig({
  resolve: { alias: { "@": resolve(__dirname, "src") } },
  build: {
    outDir: "dist",
    emptyOutDir: false,
    modulePreload: false,
    target: "es2020",
    lib: {
      entry: resolve(__dirname, "src/background/index.ts"),
      name: "FinVerifyBackground",
      formats: ["iife"],
      fileName: () => "src/background/index.js",
    },
  },
});
