"""
Builds the core forensic graph:
  - bipartite address<->transaction graph (input address -> tx -> output address)
  - entity clustering via the multi-input heuristic (addresses spent together in
    the same transaction are assumed commonly-owned)

Persisted as a NetworkX pickle (graph/graph.gpickle). In production this is what
gets pushed into Neo4j via neo4j_client.py -- the graph shape is identical, only
the storage backend changes.
"""
import json
import pickle
import sqlite3
import sys
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

BASE = Path(__file__).parent.parent
DB_PATH = config.DATABASE_PATH
GRAPH_PATH = config.GRAPH_PATH


def load_transactions(conn):
    rows = conn.execute("SELECT txid, timestamp, input_addresses, output_addresses, amounts, fee "
                         "FROM transactions").fetchall()
    return rows


def build_graph(conn):
    G = nx.DiGraph()
    for row in load_transactions(conn):
        txid = row["txid"]
        inputs = json.loads(row["input_addresses"])
        outputs = json.loads(row["output_addresses"])
        amounts = json.loads(row["amounts"])

        G.add_node(txid, kind="tx", timestamp=row["timestamp"], fee=row["fee"])
        for a in inputs:
            G.add_node(a, kind="address")
            G.add_edge(a, txid, kind="input")
        for a, amt in zip(outputs, amounts):
            G.add_node(a, kind="address")
            G.add_edge(txid, a, amount=amt, kind="output")
    return G


def multi_input_clustering(conn):
    """Union-find over addresses that co-appear as inputs of the same tx."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for row in load_transactions(conn):
        inputs = json.loads(row["input_addresses"])
        for a in inputs:
            find(a)
        for a, b in zip(inputs, inputs[1:]):
            union(a, b)

    clusters = {}
    for addr in parent:
        root = find(addr)
        clusters.setdefault(root, []).append(addr)

    # cluster_id -> list of addresses (only clusters with >1 address are "derived" entities;
    # singleton clusters fall back to the entity_id from ground truth/labels table if present)
    address_to_cluster = {}
    for i, (root, addrs) in enumerate(clusters.items()):
        cluster_id = f"cluster_{i}"
        for a in addrs:
            address_to_cluster[a] = cluster_id
    return address_to_cluster


def persist_clusters(conn, address_to_cluster):
    conn.execute("""CREATE TABLE IF NOT EXISTS derived_clusters (
        address_id TEXT PRIMARY KEY, cluster_id TEXT)""")
    conn.executemany(
        "INSERT OR REPLACE INTO derived_clusters (address_id, cluster_id) VALUES (?, ?)",
        list(address_to_cluster.items()),
    )
    conn.commit()


def run():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("building address-transaction graph...")
    G = build_graph(conn)
    print(f"  nodes: {G.number_of_nodes()}  edges: {G.number_of_edges()}")

    print("clustering addresses (multi-input heuristic)...")
    address_to_cluster = multi_input_clustering(conn)
    persist_clusters(conn, address_to_cluster)
    n_clusters = len(set(address_to_cluster.values()))
    print(f"  {len(address_to_cluster)} addresses -> {n_clusters} derived clusters")

    with open(GRAPH_PATH, "wb") as f:
        pickle.dump(G, f)
    print("graph saved ->", GRAPH_PATH)

    conn.close()


if __name__ == "__main__":
    run()
