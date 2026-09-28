import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getEntity, getEntityGraph, submitFeedback } from "../api/client.js";
import RiskBadge from "../components/RiskBadge.jsx";
import ShapChart from "../components/ShapChart.jsx";
import Timeline from "../components/Timeline.jsx";
import EvidenceGraph from "../components/EvidenceGraph.jsx";
import WalletLinks from "../components/WalletLinks.jsx";
import RiskGauge from "../components/RiskGauge.jsx";

const LABELS = {
  n_addresses: "address count",
  n_transactions: "transaction count",
  graph_degree: "graph degree",
  fan_out_addresses: "fan-out addresses",
  n_counterparties: "counterparties",
  burstiness: "timing burstiness",
  distinct_ips: "distinct IPs",
  distinct_asns: "distinct ASNs",
  ip_per_tx_ratio: "IP-per-transaction ratio",
};

function reasonSentence(entity) {
  const drivers = entity.top_features
    .filter((f) => f.impact > 0)
    .map((f) => LABELS[f.feature] || f.feature);
  if (!drivers.length) {
    return "No strong risk-increasing drivers were found; this entity's flag is primarily anomaly-based.";
  }
  return `Flagged primarily due to ${drivers.join(", ")} — consistent with mixer/fan-out infrastructure rather than a single wallet.`;
}

function Panel({ title, children, className = "" }) {
  return (
    <div className={`bg-canvas-panel border border-canvas-border rounded-xl p-5 shadow-panel ${className}`}>
      <h2 className="text-sm font-semibold text-slate-300 mb-3">{title}</h2>
      {children}
    </div>
  );
}

export default function CaseView() {
  const { entityId } = useParams();
  const [entity, setEntity] = useState(null);
  const [graph, setGraph] = useState(null);
  const [busy, setBusy] = useState(false);
  const [justUpdated, setJustUpdated] = useState(false);

  useEffect(() => {
    getEntity(entityId).then(setEntity);
    getEntityGraph(entityId, 2).then(setGraph);
  }, [entityId]);

  const handleFeedback = async (status) => {
    setBusy(true);
    await submitFeedback(entityId, status);
    const updated = await getEntity(entityId);
    setEntity(updated);
    setBusy(false);
    setJustUpdated(true);
    setTimeout(() => setJustUpdated(false), 1500);
  };

  if (!entity) return <p className="text-slate-500 text-sm">Loading case...</p>;

  return (
    <div className="space-y-6 print-case">
      {/* ---- 1. RISK SCORE + 2. ALERT REASON ---- */}
      <div>
        <Link to="/alerts" className="no-print text-xs text-slate-500 hover:text-slate-300">
          ← Back to alert queue
        </Link>
        <div className="flex items-center gap-3 mt-1 flex-wrap">
          <h1 className="text-xl font-semibold font-mono">{entity.entity_id}</h1>
          <RiskBadge score={entity.risk_score} showBar />
          <span
            className={`text-xs px-2 py-0.5 rounded font-mono transition-colors ${
              justUpdated ? "bg-accent/20 text-accent" : "bg-canvas-panel text-slate-400 border border-canvas-border"
            }`}
          >
            {entity.status}
          </span>
          <span className="text-xs text-slate-600 font-mono">rank #{entity.rank}</span>
        </div>
        <p className="text-sm text-slate-400 mt-2 max-w-2xl">{reasonSentence(entity)}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* ---- 3. WALLET LINKS ---- */}
          <Panel title={`Wallet links (${entity.n_addresses} addresses)`}>
            <WalletLinks addresses={entity.addresses} totalCount={entity.n_addresses} />
          </Panel>

          {/* ---- 4. TIMELINE ---- */}
          <Panel title="Transaction timeline">
            <Timeline items={entity.timeline} />
          </Panel>

          {/* ---- 5. EVIDENCE GRAPH ---- */}
          <Panel title="Evidence graph (2-hop)">
            {graph ? <EvidenceGraph graph={graph} /> : <p className="text-slate-500 text-sm">Loading graph...</p>}
          </Panel>
        </div>

        <div className="space-y-6">
          <Panel title="Why flagged (SHAP)">
            <ShapChart topFeatures={entity.top_features} />
          </Panel>

          <Panel title="Confidence breakdown">
            <div className="flex flex-col gap-4">
              <RiskGauge
                value={entity.model_probability}
                label="Matches known pattern"
                sublabel="supervised model probability"
                color="#f43f5e"
              />
              <RiskGauge
                value={entity.anomaly_score}
                label="Statistically unusual"
                sublabel="unsupervised anomaly score"
                color="#22d3ee"
              />
            </div>
          </Panel>

          <Panel title="Investigator actions" className="no-print">
            <div className="flex flex-col gap-2">
              <button
                disabled={busy}
                onClick={() => handleFeedback("reviewed")}
                className="px-3 py-2 rounded-md bg-canvas-raised hover:bg-canvas-border text-sm text-left transition-colors"
              >
                Mark as reviewed
              </button>
              <button
                disabled={busy}
                onClick={() => handleFeedback("flagged")}
                className="px-3 py-2 rounded-md bg-risk-high-dim hover:bg-risk-high/20 text-risk-high text-sm text-left transition-colors"
              >
                Escalate / confirm suspicious
              </button>
              <button
                disabled={busy}
                onClick={() => handleFeedback("safe")}
                className="px-3 py-2 rounded-md bg-risk-low-dim hover:bg-risk-low/20 text-risk-low text-sm text-left transition-colors"
              >
                Mark as safe
              </button>
              <button
                onClick={() => window.print()}
                className="px-3 py-2 rounded-md border border-canvas-border hover:bg-canvas-raised text-sm text-left text-slate-400 mt-1"
              >
                Export case (PDF via print)
              </button>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
