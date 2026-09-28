"""
Ingestion layer: reads raw CSV/JSON/XML forensic exports, normalizes them into a
single schema, and loads them into local SQLite (swap for Postgres/TimescaleDB in
production by changing DB_PATH -> a psycopg2 connection; the rest of the pipeline
only depends on the table shapes below).
"""
import csv
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

BASE = Path(__file__).parent.parent
RAW_DIR = config.RAW_DATA_DIR
DB_PATH = config.DATABASE_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    label TEXT
);
CREATE TABLE IF NOT EXISTS addresses (
    address_id TEXT PRIMARY KEY,
    entity_id TEXT,
    first_seen TEXT
);
CREATE TABLE IF NOT EXISTS transactions (
    txid TEXT PRIMARY KEY,
    timestamp TEXT,
    input_addresses TEXT,
    output_addresses TEXT,
    amounts TEXT,
    fee REAL
);
CREATE TABLE IF NOT EXISTS network_layer (
    txid TEXT PRIMARY KEY,
    src_ip TEXT,
    src_port INTEGER,
    broadcast_ts TEXT,
    asn TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
    entity_id TEXT PRIMARY KEY,
    risk_score REAL,
    rank INTEGER,
    model_probability REAL,
    anomaly_score REAL,
    top_features TEXT,
    status TEXT DEFAULT 'open'
);
"""


DROP_STATEMENTS = """
DROP TABLE IF EXISTS entities;
DROP TABLE IF EXISTS addresses;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS network_layer;
DROP TABLE IF EXISTS alerts;
DROP TABLE IF EXISTS derived_clusters;
DROP TABLE IF EXISTS feedback_log;
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn, reset=False):
    if reset:
        conn.executescript(DROP_STATEMENTS)
    conn.executescript(SCHEMA)
    conn.commit()


def load_csv(conn, table, path, columns):
    with open(path) as f:
        reader = csv.DictReader(f)
        rows = [tuple(row[c] for c in columns) for row in reader]
    placeholders = ",".join(["?"] * len(columns))
    conn.executemany(
        f"INSERT OR REPLACE INTO {table} ({','.join(columns)}) VALUES ({placeholders})",
        rows,
    )
    conn.commit()
    print(f"  loaded {len(rows)} rows -> {table}")


def run(reset=False):
    conn = get_conn()
    init_db(conn, reset=reset)

    load_csv(conn, "entities", RAW_DIR / "entities.csv", ["entity_id", "label"])
    load_csv(conn, "addresses", RAW_DIR / "addresses.csv", ["address_id", "entity_id", "first_seen"])
    load_csv(conn, "transactions", RAW_DIR / "transactions.csv",
              ["txid", "timestamp", "input_addresses", "output_addresses", "amounts", "fee"])

    # network_layer.csv is optional -- a real-world upload may only have blockchain
    # data with no correlated network/IP layer. Cross-layer features simply come
    # back as zero/empty for that entity rather than the pipeline failing.
    network_path = RAW_DIR / "network_layer.csv"
    if network_path.exists():
        load_csv(conn, "network_layer", network_path, ["txid", "src_ip", "src_port", "broadcast_ts", "asn"])
    else:
        print("  network_layer.csv not found -- skipping (cross-layer features will be zero)")

    conn.close()
    print("ingestion complete ->", DB_PATH)


if __name__ == "__main__":
    run()
