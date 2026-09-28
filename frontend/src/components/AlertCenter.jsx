import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getAlerts } from "../api/client.js";

const SEEN_KEY = "bitbrain_seen_alert_ids";
const POLL_MS = 15000;
const TIER_HIGH = Number(import.meta.env.VITE_RISK_TIER_HIGH ?? 70);

function loadSeen() {
  try {
    return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function saveSeen(set) {
  try {
    localStorage.setItem(SEEN_KEY, JSON.stringify([...set]));
  } catch {
    /* storage unavailable — alerts just won't persist across reloads */
  }
}

export default function AlertCenter() {
  const [newAlerts, setNewAlerts] = useState([]);
  const [open, setOpen] = useState(false);
  const seenRef = useRef(loadSeen());
  const navigate = useNavigate();

  const poll = async () => {
    try {
      const alerts = await getAlerts({ status: "open", min_score: TIER_HIGH, limit: 100 });
      const unseen = alerts.filter((a) => !seenRef.current.has(a.entity_id));
      setNewAlerts(unseen);
    } catch {
      /* offline hiccup — silently retry on next interval, no need to alarm the user */
    }
  };

  useEffect(() => {
    poll();
    const id = setInterval(poll, POLL_MS);
    return () => clearInterval(id);
  }, []);

  const dismiss = (entityId) => {
    seenRef.current.add(entityId);
    saveSeen(seenRef.current);
    setNewAlerts((prev) => prev.filter((a) => a.entity_id !== entityId));
  };

  const openCase = (entityId) => {
    dismiss(entityId);
    setOpen(false);
    navigate(`/case/${entityId}`);
  };

  const dismissAll = () => {
    newAlerts.forEach((a) => seenRef.current.add(a.entity_id));
    saveSeen(seenRef.current);
    setNewAlerts([]);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="relative p-1.5 rounded-md hover:bg-canvas-panel text-slate-400 hover:text-slate-200"
        title="New high-risk leads"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {newAlerts.length > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-4 min-w-[16px] px-1 items-center justify-center rounded-full bg-risk-high text-[10px] font-mono font-bold text-white">
            {newAlerts.length > 9 ? "9+" : newAlerts.length}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-20" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-canvas-panel border border-canvas-border rounded-lg shadow-panel z-30">
            <div className="flex items-center justify-between px-3 py-2 border-b border-canvas-border">
              <p className="text-xs font-semibold text-slate-300">New high-risk leads</p>
              {newAlerts.length > 0 && (
                <button onClick={dismissAll} className="text-[11px] text-accent hover:underline">
                  dismiss all
                </button>
              )}
            </div>
            {newAlerts.length === 0 ? (
              <p className="px-3 py-6 text-center text-xs text-slate-600">No new alerts.</p>
            ) : (
              newAlerts.map((a) => (
                <div
                  key={a.entity_id}
                  className="px-3 py-2.5 border-b border-canvas-border/60 hover:bg-canvas-raised cursor-pointer group"
                  onClick={() => openCase(a.entity_id)}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-slate-200">{a.entity_id}</span>
                    <span className="font-mono text-xs text-risk-high font-semibold">{a.risk_score.toFixed(1)}</span>
                  </div>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {a.top_features?.[0]?.feature ? `driven by ${a.top_features[0].feature}` : "anomaly-based flag"}
                  </p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      dismiss(a.entity_id);
                    }}
                    className="text-[10px] text-slate-600 hover:text-slate-400 mt-1 opacity-0 group-hover:opacity-100"
                  >
                    dismiss
                  </button>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
