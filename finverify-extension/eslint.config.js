import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default tseslint.config(
  {
    ignores: [
      "**/node_modules/**",
      "**/dist/**",
      "**/coverage/**",
      "packages/core/vitest.config.ts",
      "apps/extension/vite.*.config.ts",
    ],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    rules: {
      // The codebase relies on `_` / `_prefixed` names for intentionally
      // unused params (event handler signatures, interface conformance)
      // rather than omitting them — matches the pattern used throughout
      // both packages (see session.ts, http-transport.ts).
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      // Plugin/transport interfaces intentionally use `any` sparingly at
      // test-mock boundaries; keep it a warning, not a hard failure.
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
  {
    files: ["apps/extension/src/**/*.{ts,tsx}"],
    plugins: { "react-hooks": reactHooks },
    languageOptions: {
      globals: { ...globals.browser, chrome: "readonly" },
    },
    rules: {
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
    },
  },
  {
    files: ["apps/extension/scripts/**/*.mjs", "scripts/**/*.mjs", "examples/**/*.mjs", "**/*.config.{js,mjs,ts}"],
    languageOptions: {
      globals: globals.node,
    },
  },
  {
    files: ["apps/extension/e2e/setup/**/*.mjs"],
    languageOptions: {
      globals: globals.node,
    },
  },
  {
    files: ["apps/extension/e2e/**/*.ts"],
    languageOptions: {
      globals: { ...globals.node, ...globals.browser },
    },
    rules: {
      // page.evaluate() callbacks run in the browser and reference
      // window.__fv* test hooks that don't exist in TS's DOM lib —
      // `any` there is the pragmatic choice, not a code smell.
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  {
    files: ["packages/core/test/**/*.ts"],
    rules: {
      // Test doubles legitimately need broader typing than production code.
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
);
