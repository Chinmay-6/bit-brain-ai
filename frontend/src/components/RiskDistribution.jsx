import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { TIER_COLORS, tierOf } from "../lib/risk.js";

const BUCKET_SIZE = 10;

export default function RiskDistribution({ alerts }) {
  const buckets = Array.from({ length: 10 }, (_, i) => ({
    range: `${i * BUCKET_SIZE}`,
    count: 0,
    mid: i * BUCKET_SIZE + BUCKET_SIZE / 2,
  }));

  alerts.forEach((a) => {
    const idx = Math.min(9, Math.floor(a.risk_score / BUCKET_SIZE));
    buckets[idx].count += 1;
  });

  return (
    <ResponsiveContainer width="100%" height={90}>
      <BarChart data={buckets} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
        <XAxis dataKey="range" stroke="#475569" fontSize={10} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{ background: "#0f1420", border: "1px solid #1c2433", fontSize: 12 }}
          labelFormatter={(v) => `Risk ${v}-${Number(v) + BUCKET_SIZE}`}
          formatter={(v) => [v, "entities"]}
        />
        <Bar dataKey="count" radius={[3, 3, 0, 0]}>
          {buckets.map((b, i) => (
            <Cell key={i} fill={TIER_COLORS[tierOf(b.mid)].hex} fillOpacity={0.85} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
