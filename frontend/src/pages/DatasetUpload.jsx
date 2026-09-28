import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getDatasetStatus, uploadDataset } from "../api/client.js";

const STAGE_LABELS = {
  ingest: "Loading files into the database",
  graph: "Building the address-transaction graph",
  features: "Computing structural, temporal & cross-layer features",
  train: "Training models and scoring entities",
};

export default function DatasetUpload() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    getDatasetStatus().then(setStatus);
    return () => clearInterval(pollRef.current);
  }, []);

  const canSubmit = file && !submitting;

  const startPolling = () => {
    pollRef.current = setInterval(async () => {
      const s = await getDatasetStatus();
      setStatus(s);
      if (s.status === "done" || s.status === "error") {
        clearInterval(pollRef.current);
        setSubmitting(false);
      }
    }, 1500);
  };

  const handleSubmit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await uploadDataset(file);
      startPolling();
    } catch (e) {
      setSubmitting(false);
      const detail = e?.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join(" · "));
      } else {
        setError(typeof detail === "string" ? detail : e?.message || "Upload failed");
      }
    }
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-xl font-semibold">Upload Dataset</h1>
        <p className="text-sm text-slate-400 mt-1">
          Upload one transaction export. CSV, JSON, and XML are accepted; transaction
          addresses are normalized and clustered into entities automatically before scoring.
        </p>
      </div>

      <label className="block max-w-xl border border-canvas-border rounded-lg p-5 cursor-pointer hover:border-accent/40 transition-colors">
        <span className="block text-sm text-slate-200 mb-2">Transaction data file</span>
        <span className="block text-xs text-slate-500 mb-3">Supported formats: .csv, .json, .xml</span>
        <input
          type="file"
          accept=".csv,.json,.xml,text/csv,application/json,application/xml,text/xml"
          className="text-xs text-slate-400 file:mr-3 file:py-1 file:px-2 file:rounded file:border-0 file:bg-canvas-raised file:text-slate-300 file:text-xs hover:file:bg-canvas-border"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        {file && <p className="text-[11px] text-risk-low mt-2">{file.name} ({(file.size / 1024).toFixed(1)} KB)</p>}
      </label>

      {error && (
        <div className="bg-risk-high-dim border border-risk-high/30 text-risk-high text-sm rounded-lg px-4 py-3">
          {error}
        </div>
      )}

      <button
        disabled={!canSubmit}
        onClick={handleSubmit}
        className="px-4 py-2 rounded-md bg-accent/20 border border-accent/40 text-accent text-sm font-medium hover:bg-accent/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {submitting ? "Processing..." : "Upload & Run Pipeline"}
      </button>

      {status && status.status !== "idle" && (
        <div className="bg-canvas-panel border border-canvas-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <span
              className={`w-2 h-2 rounded-full ${
                status.status === "running" ? "bg-accent animate-pulse-slow"
                  : status.status === "done" ? "bg-risk-low"
                  : status.status === "error" ? "bg-risk-high" : "bg-slate-600"
              }`}
            />
            <span className="text-sm font-medium text-slate-200 capitalize">{status.status}</span>
            {status.stage && <span className="text-xs text-slate-500">— {STAGE_LABELS[status.stage] || status.stage}</span>}
          </div>
          <p className="text-xs text-slate-500 font-mono whitespace-pre-wrap">{status.message}</p>

          {status.status === "done" && (
            <div className="mt-3 flex items-center gap-3">
              <p className="text-xs text-slate-400">
                {status.entity_count} entities scored
                {status.metrics?.mode && (
                  <span className="text-slate-600"> · mode: {status.metrics.mode}</span>
                )}
              </p>
              <button
                onClick={() => navigate("/alerts")}
                className="text-xs text-accent hover:underline"
              >
                View alert queue →
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
