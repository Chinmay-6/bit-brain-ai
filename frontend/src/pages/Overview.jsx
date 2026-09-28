import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getOverview, getAlerts } from "../api/client.js";
import RiskBadge from "../components/RiskBadge.jsx";

function StatCard({ label, value, tone = "default" }) {
  const tones = {
    default: "text-slate-100",
    high: "text-red-400",
    medium: "text-amber-400",
    low: "text-emerald-400",
  };
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <p className="text-xs uppercase tracking-wide text-slate-500 mb-1">{label}</p>
      <p className={`text-3xl font-bold ${tones[tone]}`}>{value}</p>
    </div>
  );
}

export default function Overview() {
  const [stats, setStats] = useState(null);
  const [topAlerts, setTopAlerts] = useState([]);

  useEffect(() => {
    getOverview().then(setStats);
    getAlerts({ limit: 5 }).then(setTopAlerts);
  }, []);

  if (!stats) return <p className="text-slate-500">Loading...</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Investigation Overview</h1>
        <p className="text-sm text-slate-500">Bulk Bitcoin network + blockchain metadata, correlated and scored offline.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="Total Entities Scored" value={stats.total_entities} />
        <StatCard label="High Risk (open)" value={stats.high_risk_open} tone="high" />
        <StatCard label="Medium Risk (open)" value={stats.medium_risk_open} tone="medium" />
        <StatCard label="Low Risk (open)" value={stats.low_risk_open} tone="low" />
        <StatCard label="Reviewed" value={stats.reviewed} />
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-300">Top ranked leads</h2>
          <Link to="/alerts" className="text-xs text-emerald-400 hover:underline">
            View full queue →
          </Link>
        </div>
        <div className="space-y-2">
          {topAlerts.map((a) => (
            <Link
              key={a.entity_id}
              to={`/case/${a.entity_id}`}
              className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-slate-800/60 transition"
            >
              <span className="font-mono text-sm text-slate-300">{a.entity_id}</span>
              <span className="text-xs text-slate-500">
                {a.top_features[0] && `${a.top_features[0].feature}`}
              </span>
              <RiskBadge score={a.risk_score} />
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
