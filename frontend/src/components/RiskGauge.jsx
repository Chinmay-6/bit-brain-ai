const SIZE = 84;
const STROKE = 7;
const RADIUS = (SIZE - STROKE) / 2;
const CIRC = 2 * Math.PI * RADIUS;

export default function RiskGauge({ value, label, sublabel, color = "#22d3ee" }) {
  const pct = Math.max(0, Math.min(1, value));
  const offset = CIRC * (1 - pct);

  return (
    <div className="flex items-center gap-3">
      <svg width={SIZE} height={SIZE} className="-rotate-90 shrink-0">
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke="#1c2433"
          strokeWidth={STROKE}
        />
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth={STROKE}
          strokeDasharray={CIRC}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="central"
          transform={`rotate(90 ${SIZE / 2} ${SIZE / 2})`}
          className="font-mono font-semibold"
          fill="#e5e9f0"
          fontSize="18"
        >
          {(pct * 100).toFixed(0)}
        </text>
      </svg>
      <div>
        <p className="text-sm font-medium text-slate-200">{label}</p>
        <p className="text-xs text-slate-500 max-w-[16ch] leading-snug">{sublabel}</p>
      </div>
    </div>
  );
}
