export const TIER_HIGH = Number(import.meta.env.VITE_RISK_TIER_HIGH ?? 70);
export const TIER_MEDIUM = Number(import.meta.env.VITE_RISK_TIER_MEDIUM ?? 40);

export function tierOf(score) {
  if (score >= TIER_HIGH) return "high";
  if (score >= TIER_MEDIUM) return "medium";
  return "low";
}

export const TIER_COLORS = {
  high: { text: "text-risk-high", bg: "bg-risk-high-dim", border: "border-risk-high/30", hex: "#f43f5e" },
  medium: { text: "text-risk-medium", bg: "bg-risk-medium-dim", border: "border-risk-medium/30", hex: "#f59e0b" },
  low: { text: "text-risk-low", bg: "bg-risk-low-dim", border: "border-risk-low/30", hex: "#22c55e" },
};
