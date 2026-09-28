/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: "#0a0e14",
          raised: "#0f1420",
          panel: "#121826",
          border: "#1c2433",
        },
        accent: {
          DEFAULT: "#22d3ee", // cyan — the one hero accent, never reused for risk semantics
          dim: "#0e7490",
        },
        risk: {
          high: "#f43f5e",
          "high-dim": "#4c1d24",
          medium: "#f59e0b",
          "medium-dim": "#452e0a",
          low: "#22c55e",
          "low-dim": "#0f2e1c",
        },
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "'JetBrains Mono'", "'Cascadia Code'", "Consolas", "monospace"],
        sans: ["-apple-system", "BlinkMacSystemFont", "'Segoe UI'", "Inter", "Roboto", "sans-serif"],
      },
      boxShadow: {
        panel: "0 0 0 1px rgba(255,255,255,0.04), 0 8px 24px -8px rgba(0,0,0,0.6)",
      },
      animation: {
        "pulse-slow": "pulse 2.4s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};
