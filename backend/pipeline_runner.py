"""
Runs the ingest -> graph -> features -> train pipeline in a background thread
after a dataset upload, so the HTTP request returns immediately and the
frontend polls GET /api/dataset/status for progress. Single global STATE dict
guarded by a lock -- this app runs as a single uvicorn worker (appropriate for
an offline single-machine forensic tool), so this is not a distributed-systems
problem.
"""
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from pipeline import ingest, graph_builder, features, train

_lock = threading.Lock()
STATE = {
    "status": "idle",       # idle | running | done | error
    "stage": None,          # ingest | graph | features | train
    "message": "",
    "updated_at": None,
    "entity_count": None,
    "metrics": None,
}


def _set(**kwargs):
    with _lock:
        STATE.update(kwargs)
        STATE["updated_at"] = datetime.now(timezone.utc).isoformat()


def get_state():
    with _lock:
        return dict(STATE)


def _run(reset: bool):
    try:
        _set(status="running", stage="ingest", message="Loading uploaded files into the database...")
        ingest.run(reset=reset)

        _set(stage="graph", message="Building the address-transaction graph and clustering entities...")
        graph_builder.run()

        _set(stage="features", message="Computing structural, temporal, and cross-layer features...")
        features.run()

        _set(stage="train", message="Training models and scoring entities...")
        train.run()

        import sqlite3
        conn = sqlite3.connect(config.DATABASE_PATH)
        count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        conn.close()

        metrics = None
        if config.METRICS_PATH.exists():
            import json
            metrics = json.loads(config.METRICS_PATH.read_text())

        _set(status="done", stage=None, message=f"Done. {count} entities scored.",
             entity_count=count, metrics=metrics)
    except Exception as e:
        _set(status="error", stage=STATE.get("stage"),
             message=f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}")


def start_pipeline_async(reset: bool = True):
    """Kicks off the pipeline in a background thread. Returns immediately."""
    if STATE["status"] == "running":
        return False  # already in progress, caller should reject/report busy
    t = threading.Thread(target=_run, args=(reset,), daemon=True)
    t.start()
    return True
