import { useState } from "react";
import { Link } from "react-router-dom";
import { searchTransactions } from "../api/client.js";
import RiskBadge from "../components/RiskBadge.jsx";

export default function TransactionSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const runSearch = async (e) => {
    e?.preventDefault();
    if (q.trim().length < 3) {
      setError("Enter at least 3 characters (txid or address).");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const data = await searchTransactions(q.trim());
      setResults(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Search failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Transaction Search</h1>
        <p className="text-sm text-slate-400 mt-1">
          Search by full or partial transaction ID, or by any input/output address.
        </p>
      </div>

      <form onSubmit={runSearch} className="flex gap-2 max-w-xl">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="tx_a1b2c3... or addr_..."
          className="flex-1 bg-canvas-panel border border-canvas-border rounded-md px-3 py-2 text-sm font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-accent/50"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 rounded-md bg-accent/20 border border-accent/40 text-accent text-sm font-medium hover:bg-accent/30 disabled:opacity-40"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <p className="text-xs text-risk-high">{error}</p>}

      {results && (
        <div>
          <p className="text-xs text-slate-500 mb-3">
            {results.count} match{results.count === 1 ? "" : "es"} for "{results.query}"
          </p>
          <div className="space-y-2">
            {results.results.map((tx) => (
              <div key={tx.txid} className="bg-canvas-panel border border-canvas-border rounded-xl p-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <span className="font-mono text-sm text-slate-200">{tx.txid}</span>
                  <div className="flex items-center gap-2">
                    {tx.entity_id ? (
                      <>
                        {tx.entity_risk_score != null && <RiskBadge score={tx.entity_risk_score} />}
                        <Link to={`/case/${tx.entity_id}`} className="text-xs text-accent hover:underline font-mono">
                          {tx.entity_id} →
                        </Link>
                      </>
                    ) : (
                      <span className="text-xs text-slate-600">no resolved entity</span>
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 mt-3 text-xs text-slate-500">
                  <p>timestamp: <span className="text-slate-300 font-mono">{tx.timestamp}</span></p>
                  <p>fee: <span className="text-slate-300 font-mono">{tx.fee}</span></p>
                  <p>inputs: <span className="text-slate-300 font-mono">{tx.input_addresses.join(", ")}</span></p>
                  <p>outputs: <span className="text-slate-300 font-mono">{tx.output_addresses.join(", ")}</span></p>
                  {tx.network && (
                    <p className="sm:col-span-2">
                      network: <span className="text-slate-300 font-mono">{tx.network.src_ip}:{tx.network.src_port} · {tx.network.asn}</span>
                    </p>
                  )}
                </div>
              </div>
            ))}
            {results.count === 0 && (
              <p className="text-sm text-slate-600 text-center py-8">No transactions matched.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
