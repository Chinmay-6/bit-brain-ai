import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const LABELS = {
  n_addresses: "Address count",
  n_transactions: "Transaction count",
  graph_degree: "Graph degree",
  fan_out_addresses: "Fan-out addresses",
  n_counterparties: "Counterparties",
  burstiness: "Timing burstiness",
  distinct_ips: "Distinct IPs",
  distinct_asns: "Distinct ASNs",
  ip_per_tx_ratio: "IP-per-tx ratio",
};

export default function ShapChart({ topFeatures }) {
  const data = topFeatures.map((f) => ({
    name: LABELS[f.feature] || f.feature,
    impact: f.impact,
  }));

  return (
    <div>
      <ResponsiveContainer width="100%" height={140}>
        <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
          <XAxis type="number" stroke="#64748b" fontSize={11} />
          <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={12} width={140} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", fontSize: 12 }}
            formatter={(v) => [v.toFixed(4), "SHAP impact"]}
          />
          <Bar dataKey="impact" radius={[0, 4, 4, 0]}>
            {data.map((d, i) => (
              <Cell key={i} fill={d.impact >= 0 ? "#f87171" : "#4ade80"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <p className="text-xs text-slate-500 mt-1">
        Red = pushes risk up, green = pushes risk down. Bars show SHAP contribution from the Random Forest model.
      </p>
    </div>
  );
}
