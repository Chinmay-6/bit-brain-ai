import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getAlerts } from "../api/client.js";
import RiskBadge from "../components/RiskBadge.jsx";

const TIER_HIGH = Number(import.meta.env.VITE_RISK_TIER_HIGH ?? 70);
const TIER_MEDIUM = Number(import.meta.env.VITE_RISK_TIER_MEDIUM ?? 40);

const TIERS = [
  { label: "All", value: 0 },
  { label: `High (≥${TIER_HIGH})`, value: TIER_HIGH },
  { label: `Medium (≥${TIER_MEDIUM})`, value: TIER_MEDIUM },
];

export default function AlertQueue() {
  const [alerts, setAlerts] = useState([]);
  const [minScore, setMinScore] = useState(0);
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getAlerts({ min_score: minScore, status: status || undefined, limit: 200 })
      .then(setAlerts)
      .finally(() => setLoading(false));
  }, [minScore, status]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Alert Queue</h1>
        <div className="flex gap-2">
          {TIERS.map((t) => (
            <button
              key={t.value}
              onClick={() => setMinScore(t.value)}
              className={`px-3 py-1.5 text-xs rounded-md border ${
                minScore === t.value
                  ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-300"
                  : "border-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-md px-2 text-xs text-slate-300"
          >
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="reviewed">Reviewed</option>
            <option value="flagged">Flagged</option>
            <option value="safe">Marked safe</option>
          </select>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/50 text-slate-400 text-xs uppercase tracking-wide">
            <tr>
              <th className="text-left px-4 py-3">Rank</th>
              <th className="text-left px-4 py-3">Entity</th>
              <th className="text-left px-4 py-3">Risk</th>
              <th className="text-left px-4 py-3">Model Prob.</th>
              <th className="text-left px-4 py-3">Anomaly</th>
              <th className="text-left px-4 py-3">Top reason</th>
              <th className="text-left px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-500">Loading...</td>
              </tr>
            )}
            {!loading && alerts.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-500">No alerts match this filter.</td>
              </tr>
            )}
            {alerts.map((a) => (
              <tr key={a.entity_id} className="hover:bg-slate-800/40">
                <td className="px-4 py-3 text-slate-500">#{a.rank}</td>
                <td className="px-4 py-3">
                  <Link to={`/case/${a.entity_id}`} className="font-mono text-emerald-400 hover:underline">
                    {a.entity_id}
                  </Link>
                </td>
                <td className="px-4 py-3"><RiskBadge score={a.risk_score} /></td>
                <td className="px-4 py-3 text-slate-300">{(a.model_probability * 100).toFixed(1)}%</td>
                <td className="px-4 py-3 text-slate-300">{(a.anomaly_score * 100).toFixed(1)}%</td>
                <td className="px-4 py-3 text-slate-400 text-xs">{a.top_features[0]?.feature}</td>
                <td className="px-4 py-3">
                  <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-400">{a.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
