import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

// IIFE is load-bearing here, not stylistic: manifest.json's content_scripts
// entries execute as classic scripts (there is no "type": "module" option
// for content_scripts in MV3), so an ES module bundle with `import`
// statements between chunks would throw a SyntaxError the instant ChatGPT
// tries to inject it. IIFE + a single entry point guarantees Rollup inlines
// everything (React included) into one flat, self-contained file.
export default defineConfig({
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  plugins: [react()],
  resolve: { alias: { "@": resolve(__dirname, "src") } },
  build: {
    outDir: "dist",
    emptyOutDir: false, // background + popup builds populate the same dist/
    cssCodeSplit: false,
    modulePreload: false,
    target: "es2020",
    lib: {
      entry: resolve(__dirname, "src/content/index.tsx"),
      name: "FinVerifyContentScript",
      formats: ["iife"],
      fileName: () => "src/content/index.js",
    },
    rollupOptions: {
      output: {
        // lib-mode + iife wants an explicit global var name for any
        // exports; we have none (side-effect-only entry) so this is unused
        // but Rollup still requires it to be set.
        assetFileNames: (asset) => (asset.name?.endsWith(".css") ? "src/content/index.css" : "src/assets/[name]-[hash][extname]"),
      },
    },
  },
});
