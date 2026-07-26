/** @type {import('tailwindcss').Config} */
// Color tokens intentionally mirror finverify-terminal/frontend/tailwind.config.ts
// so the extension's UI reads as the same product, not a bolted-on skin.
export default {
  content: ["./src/**/*.{js,ts,jsx,tsx,html}"],
  theme: {
    extend: {
      colors: {
        "t-bg": "#0a0a0a",
        "t-surface": "#111111",
        "t-border": "#1e1e1e",
        "t-border-accent": "#2a2a2a",
        "t-primary": "#e0e0e0",
        "t-secondary": "#888888",
        "t-muted": "#444444",
        "t-green": "#00ff88",
        "t-amber": "#fbbf24",
        "t-red": "#f87171",
        "t-blue": "#60a5fa",
        "t-cyan": "#22d3ee",
        "t-purple": "#a78bfa",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "Cascadia Code", "Fira Code", "monospace"],
      },
      animation: {
        "fade-in": "fadeIn 0.15s ease-out",
        "slide-up": "slideUp 0.2s ease-out",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  // Extension UI is injected into the host page (chatgpt.com) as a shadow-root-less
  // subtree today; prefix keeps our classes from ever colliding with ChatGPT's own
  // Tailwind build if they add one later.
  prefix: "fv-",
  corePlugins: { preflight: false },
  plugins: [],
};
