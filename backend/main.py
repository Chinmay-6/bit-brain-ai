"""
Bit-Brain AI backend. Serves everything from local SQLite + the saved NetworkX
graph -- no external network calls, so this runs entirely offline.

Run: uvicorn backend.main:app --reload --port 8000   (from the project root)
"""
import json
import pickle
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

import networkx as nx
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent))
import config
from backend.pipeline_runner import get_state, start_pipeline_async
from backend.dataset_parser import normalize_dataset

BASE = Path(__file__).parent.parent
DB_PATH = config.DATABASE_PATH
GRAPH_PATH = config.GRAPH_PATH

app = FastAPI(title="Bit-Brain AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,   # set CORS_ORIGINS env var in production, default "*"
    allow_methods=["*"],
    allow_headers=["*"],
)

_graph_cache: Optional[nx.DiGraph] = None


def get_graph() -> nx.DiGraph:
    global _graph_cache
    if _graph_cache is None:
        with open(GRAPH_PATH, "rb") as f:
            _graph_cache = pickle.load(f)
    return _graph_cache


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class FeedbackIn(BaseModel):
    entity_id: str
    status: str  # "reviewed" | "flagged" | "safe"


@app.post("/api/dataset/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Accepts one CSV, JSON, or XML transaction export. Transaction identifiers,
    input addresses, and output addresses are inferred from common field names;
    addresses co-spent as inputs are automatically assigned to the same entity.

    Replaces the current dataset entirely (old demo/previous-upload data is
    cleared) and runs the full pipeline (ingest -> graph -> features -> train)
    in the background. Poll GET /api/dataset/status for progress.
    """
    if get_state()["status"] == "running":
        raise HTTPException(409, "A dataset is already being processed. Check /api/dataset/status.")

    raw = await file.read()
    if not raw:
        raise HTTPException(422, "The uploaded file is empty")
    try:
        contents, entity_count = normalize_dataset(file.filename or "", raw)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, ET.ParseError) as exc:
        raise HTTPException(422, str(exc)) from exc

    config.RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for filename, raw in contents.items():
        (config.RAW_DATA_DIR / filename).write_bytes(raw)
    # if the previous dataset had a network_layer.csv and this upload doesn't,
    # remove the stale file so ingest.py's optional-file check doesn't pick it up
    if "network_layer.csv" not in contents:
        stale = config.RAW_DATA_DIR / "network_layer.csv"
        if stale.exists():
            stale.unlink()

    started = start_pipeline_async(reset=True)
    if not started:
        raise HTTPException(409, "A dataset is already being processed. Check /api/dataset/status.")

    return {"status": "processing", "message": f"File received. Inferred {entity_count} entities and started the pipeline."}


@app.get("/api/dataset/status")
def dataset_status():
    return get_state()


@app.get("/api/dataset/schema")
def dataset_schema():
    """Describes accepted file formats and automatically inferred fields."""
    return {"formats": ["csv", "json", "xml"], "entity_clustering": "multi-input co-spend"}


@app.get("/api/overview")
def overview():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) c FROM alerts").fetchone()["c"]
    open_high = conn.execute(
        "SELECT COUNT(*) c FROM alerts WHERE risk_score >= ? AND status='open'",
        (config.RISK_TIER_HIGH,),
    ).fetchone()["c"]
    open_med = conn.execute(
        "SELECT COUNT(*) c FROM alerts WHERE risk_score >= ? AND risk_score < ? AND status='open'",
        (config.RISK_TIER_MEDIUM, config.RISK_TIER_HIGH),
    ).fetchone()["c"]
    open_low = conn.execute(
        "SELECT COUNT(*) c FROM alerts WHERE risk_score < ? AND status='open'",
        (config.RISK_TIER_MEDIUM,),
    ).fetchone()["c"]
    reviewed = conn.execute(
        "SELECT COUNT(*) c FROM alerts WHERE status != 'open'"
    ).fetchone()["c"]
    conn.close()
    return {
        "total_entities": total,
        "high_risk_open": open_high,
        "medium_risk_open": open_med,
        "low_risk_open": open_low,
        "reviewed": reviewed,
    }


@app.get("/api/alerts")
def list_alerts(
    min_score: float = Query(0, ge=0, le=100),
    status: Optional[str] = None,
    limit: int = Query(config.ALERTS_DEFAULT_LIMIT, le=500),
    offset: int = 0,
):
    conn = get_conn()
    q = "SELECT * FROM alerts WHERE risk_score >= ?"
    params = [min_score]
    if status:
        q += " AND status = ?"
        params.append(status)
    q += " ORDER BY risk_score DESC LIMIT ? OFFSET ?"
    params += [limit, offset]
    rows = conn.execute(q, params).fetchall()
    conn.close()

    return [
        {
            "entity_id": r["entity_id"],
            "risk_score": r["risk_score"],
            "rank": r["rank"],
            "model_probability": r["model_probability"],
            "anomaly_score": r["anomaly_score"],
            "top_features": json.loads(r["top_features"]),
            "status": r["status"],
        }
        for r in rows
    ]


@app.get("/api/entities/{entity_id}")
def entity_detail(entity_id: str):
    conn = get_conn()
    alert = conn.execute("SELECT * FROM alerts WHERE entity_id = ?", (entity_id,)).fetchone()
    if not alert:
        conn.close()
        raise HTTPException(404, "entity not found")

    ent_row = conn.execute("SELECT * FROM entities WHERE entity_id = ?", (entity_id,)).fetchone()
    addr_rows = conn.execute("SELECT address_id FROM addresses WHERE entity_id = ?", (entity_id,)).fetchall()
    addresses = [r["address_id"] for r in addr_rows]

    # timeline: every tx touching any of this entity's addresses
    # (LIKE-per-address scan is fine at this dataset size; swap for a join table in production)
    tx_rows = []
    seen = set()
    for a in addresses:
        rows = conn.execute(
            """SELECT DISTINCT t.txid, t.timestamp, t.fee, n.src_ip, n.asn
               FROM transactions t
               LEFT JOIN network_layer n ON n.txid = t.txid
               WHERE t.input_addresses LIKE ? OR t.output_addresses LIKE ?""",
            (f"%{a}%", f"%{a}%"),
        ).fetchall()
        for r in rows:
            if r["txid"] not in seen:
                seen.add(r["txid"])
                tx_rows.append(dict(r))
    tx_rows.sort(key=lambda r: r["timestamp"])

    conn.close()

    return {
        "entity_id": entity_id,
        "ground_truth_label": ent_row["label"] if ent_row else "unknown",
        "risk_score": alert["risk_score"],
        "rank": alert["rank"],
        "model_probability": alert["model_probability"],
        "anomaly_score": alert["anomaly_score"],
        "top_features": json.loads(alert["top_features"]),
        "status": alert["status"],
        "n_addresses": len(addresses),
        "addresses": addresses[:25],  # cap payload size
        "timeline": tx_rows[:100],
    }


@app.get("/api/graph/{entity_id}")
def entity_graph(entity_id: str, hops: int = Query(2, ge=1, le=3)):
    """Returns a k-hop evidence subgraph around this entity's addresses, for viz."""
    conn = get_conn()
    addr_rows = conn.execute("SELECT address_id FROM addresses WHERE entity_id = ?", (entity_id,)).fetchall()
    conn.close()
    addresses = {r["address_id"] for r in addr_rows}
    if not addresses:
        raise HTTPException(404, "entity not found")

    G = get_graph()
    frontier = set(a for a in addresses if a in G)
    visited = set(frontier)
    for _ in range(hops):
        next_frontier = set()
        for n in frontier:
            next_frontier |= set(G.predecessors(n)) | set(G.successors(n))
        next_frontier -= visited
        visited |= next_frontier
        frontier = next_frontier
        if len(visited) > config.GRAPH_MAX_SUBGRAPH_NODES:
            break

    sub = G.subgraph(visited)
    nodes = [
        {
            "id": n,
            "kind": data.get("kind", "unknown"),
            "is_focus": n in addresses,
        }
        for n, data in sub.nodes(data=True)
    ]
    edges = [
        {"source": u, "target": v, "kind": data.get("kind"), "amount": data.get("amount")}
        for u, v, data in sub.edges(data=True)
    ]
    return {"entity_id": entity_id, "nodes": nodes, "edges": edges}


def _resolve_entity_for_addresses(conn, addresses: List[str]) -> Optional[sqlite3.Row]:
    """Given a set of addresses touched by a transaction, find the entity (and
    its alert/risk info) that any of them belong to, if resolvable."""
    if not addresses:
        return None
    placeholders = ",".join("?" * len(addresses))
    row = conn.execute(
        f"""SELECT a.entity_id, al.risk_score, al.status
            FROM addresses a
            LEFT JOIN alerts al ON al.entity_id = a.entity_id
            WHERE a.address_id IN ({placeholders})
            ORDER BY al.risk_score DESC
            LIMIT 1""",
        addresses,
    ).fetchone()
    return row


def _tx_row_to_dict(conn, row) -> dict:
    inputs = json.loads(row["input_addresses"])
    outputs = json.loads(row["output_addresses"])
    net = conn.execute(
        "SELECT src_ip, src_port, broadcast_ts, asn FROM network_layer WHERE txid = ?", (row["txid"],)
    ).fetchone()
    entity = _resolve_entity_for_addresses(conn, inputs + outputs)
    return {
        "txid": row["txid"],
        "timestamp": row["timestamp"],
        "fee": row["fee"],
        "input_addresses": inputs,
        "output_addresses": outputs,
        "amounts": json.loads(row["amounts"]),
        "network": dict(net) if net else None,
        "entity_id": entity["entity_id"] if entity else None,
        "entity_risk_score": entity["risk_score"] if entity else None,
        "entity_status": entity["status"] if entity else None,
    }


@app.get("/api/transactions/search")
def search_transactions(
    q: str = Query(..., min_length=3, description="txid or address substring"),
    limit: int = Query(50, le=200),
):
    """
    Searches transactions by txid substring or by participating address
    (input or output) substring. A minimum of 3 characters avoids table-scan
    queries matching almost everything on a large real dataset.
    """
    conn = get_conn()
    like = f"%{q}%"
    rows = conn.execute(
        """SELECT txid, timestamp, input_addresses, output_addresses, amounts, fee
           FROM transactions
           WHERE txid LIKE ? OR input_addresses LIKE ? OR output_addresses LIKE ?
           ORDER BY timestamp DESC
           LIMIT ?""",
        (like, like, like, limit),
    ).fetchall()
    results = [_tx_row_to_dict(conn, r) for r in rows]
    conn.close()
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/transactions/{txid}")
def get_transaction(txid: str):
    conn = get_conn()
    row = conn.execute(
        """SELECT txid, timestamp, input_addresses, output_addresses, amounts, fee
           FROM transactions WHERE txid = ?""",
        (txid,),
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "transaction not found")
    result = _tx_row_to_dict(conn, row)
    conn.close()
    return result


@app.post("/api/feedback")
def submit_feedback(payload: FeedbackIn):
    if payload.status not in ("reviewed", "flagged", "safe", "open"):
        raise HTTPException(400, "invalid status")
    conn = get_conn()
    cur = conn.execute(
        "UPDATE alerts SET status = ? WHERE entity_id = ?", (payload.status, payload.entity_id)
    )
    conn.commit()
    updated = cur.rowcount
    conn.close()
    if not updated:
        raise HTTPException(404, "entity not found")
    return {"entity_id": payload.entity_id, "status": payload.status}
