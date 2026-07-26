import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": resolve(__dirname, "src") } },
  build: {
    outDir: "dist",
    emptyOutDir: false,
    modulePreload: false,
    target: "es2020",
    rollupOptions: {
      input: { popup: resolve(__dirname, "src/popup/index.html") },
      output: {
        entryFileNames: "src/popup/index.js",
        assetFileNames: "src/popup/[name][extname]",
      },
    },
  },
});
