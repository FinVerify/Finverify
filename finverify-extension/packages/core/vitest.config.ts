import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "text-summary", "html", "lcov"],
      include: ["src/**/*.ts"],
      exclude: [
        "src/index.ts", // pure re-exports, nothing to unit test
        "src/plugins/example-climate/**", // explicitly a non-shipped demo, see its own doc comment
        "src/types.ts", // interfaces only, zero runtime statements
        "src/plugins/types.ts", // interfaces only, zero runtime statements
        "src/**/*.d.ts",
      ],
      thresholds: {
        lines: 90,
        statements: 90,
        functions: 90,
        branches: 85,
      },
    },
  },
});
