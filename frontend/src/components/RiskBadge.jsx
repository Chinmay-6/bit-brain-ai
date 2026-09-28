import { tierOf, TIER_COLORS } from "../lib/risk.js";

export default function RiskBadge({ score, showBar = false }) {
  const tier = tierOf(score);
  const c = TIER_COLORS[tier];

  return (
    <div className="inline-flex items-center gap-2">
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-mono font-semibold ${c.bg} ${c.text} ${c.border}`}>
        <span className="w-1.5 h-1.5 rounded-full bg-current" />
        {score.toFixed(1)}
      </span>
      {showBar && (
        <div className="w-16 h-1.5 rounded-full bg-canvas-border overflow-hidden">
          <div
            className="h-full rounded-full"
            style={{ width: `${score}%`, background: c.hex, transition: "width 0.4s ease" }}
          />
        </div>
      )}
    </div>
  );
}
