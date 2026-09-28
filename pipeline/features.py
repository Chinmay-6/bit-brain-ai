"""
Computes entity-level features from the graph + raw tables:
  - structural: tx count, address count, fan-in/out, degree stats
  - temporal: burstiness (std/mean of inter-tx gaps), activity span
  - cross-layer: distinct IP count, distinct ASN count per entity (network layer
    joined to transactions via txid) -- a small IP/ASN pool for a large tx volume
    is the signature of mixer-like / bot infrastructure

Output: pipeline/features.csv  (entity_id, label, <feature columns>)
"""
import json
import pickle
import sqlite3
import statistics as stats
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

BASE = Path(__file__).parent.parent
DB_PATH = config.DATABASE_PATH
GRAPH_PATH = config.GRAPH_PATH
FEATURES_PATH = config.FEATURES_PATH


def entity_addresses(conn):
    rows = conn.execute("SELECT address_id, entity_id FROM addresses").fetchall()
    m = {}
    for r in rows:
        m.setdefault(r["entity_id"], []).append(r["address_id"])
    return m


def address_to_txs(conn):
    """address -> list of (txid, timestamp, role) it participates in."""
    out = {}
    for row in conn.execute("SELECT txid, timestamp, input_addresses, output_addresses FROM transactions"):
        inputs = json.loads(row["input_addresses"])
        outputs = json.loads(row["output_addresses"])
        for a in inputs:
            out.setdefault(a, []).append((row["txid"], row["timestamp"], "input"))
        for a in outputs:
            out.setdefault(a, []).append((row["txid"], row["timestamp"], "output"))
    return out


def tx_network_info(conn):
    rows = conn.execute("SELECT txid, src_ip, asn FROM network_layer").fetchall()
    return {r["txid"]: (r["src_ip"], r["asn"]) for r in rows}


def burstiness(timestamps):
    if len(timestamps) < 3:
        return 0.0
    ts_sorted = sorted(timestamps)
    gaps = [(pd.Timestamp(b) - pd.Timestamp(a)).total_seconds()
            for a, b in zip(ts_sorted, ts_sorted[1:])]
    if not gaps or stats.mean(gaps) == 0:
        return 0.0
    return stats.pstdev(gaps) / stats.mean(gaps)


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    with open(GRAPH_PATH, "rb") as f:
        G = pickle.load(f)

    ent_addrs = entity_addresses(conn)
    addr_txs = address_to_txs(conn)
    tx_net = tx_network_info(conn)
    labels = {r["entity_id"]: r["label"] for r in conn.execute("SELECT entity_id, label FROM entities")}

    rows = []
    for entity_id, addrs in ent_addrs.items():
        tx_set = set()
        timestamps = []
        ips, asns = set(), set()
        total_out_value = 0.0
        counterparties = set()

        for a in addrs:
            for txid, ts, role in addr_txs.get(a, []):
                tx_set.add(txid)
                timestamps.append(ts)
                if txid in tx_net:
                    ip, asn = tx_net[txid]
                    ips.add(ip)
                    asns.add(asn)
                # counterparties: neighbours of this address in the graph that aren't its own
                for nbr in list(G.predecessors(a)) + list(G.successors(a)):
                    if nbr not in addrs and G.nodes.get(nbr, {}).get("kind") == "address":
                        counterparties.add(nbr)

        n_tx = len(tx_set)
        n_addr = len(addrs)
        degree = sum(G.degree(a) for a in addrs if a in G)
        fan_out = sum(1 for a in addrs if a in G and G.out_degree(a) > 3)

        rows.append({
            "entity_id": entity_id,
            "label": labels.get(entity_id, "unknown"),
            "n_addresses": n_addr,
            "n_transactions": n_tx,
            "graph_degree": degree,
            "fan_out_addresses": fan_out,
            "n_counterparties": len(counterparties),
            "burstiness": round(burstiness(timestamps), 4),
            "distinct_ips": len(ips),
            "distinct_asns": len(asns),
            "ip_per_tx_ratio": round(len(ips) / n_tx, 4) if n_tx else 0.0,
        })

    df = pd.DataFrame(rows)
    df.to_csv(FEATURES_PATH, index=False)
    print(f"features written for {len(df)} entities -> {FEATURES_PATH}")
    print(df["label"].value_counts().to_dict())

    conn.close()


if __name__ == "__main__":
    run()
