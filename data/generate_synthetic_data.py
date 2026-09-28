"""
Generates a self-contained synthetic dataset that mimics what Bit-Brain AI expects
in production: a blockchain layer (addresses, transactions) and a network layer
(IP/port/broadcast timestamp per txid), with labeled entities and INJECTED FRAUD
PATTERNS (fan-out, chains, shared-IP clusters) so the downstream ML pipeline has
real signal to detect.

Why synthetic: public forensic datasets (e.g. Elliptic++) provide the blockchain
layer but not packet-level network metadata joined to txids -- that pairing does
not exist publicly, so it must be generated. This is documented, not hidden.

Output (data/raw/):
  addresses.csv        address_id, entity_id, first_seen
  transactions.csv      txid, timestamp, input_addresses(list), output_addresses(list), amounts(list), fee
  network_layer.csv     txid, src_ip, src_port, broadcast_ts, asn
  labels.csv             entity_id, label  (licit | illicit | unknown)
"""
import csv
import json
import random
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

random.seed(config.SYNTH_SEED)

OUT_DIR = config.RAW_DATA_DIR
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_LICIT_ENTITIES = config.SYNTH_N_LICIT_ENTITIES
N_ILLICIT_ENTITIES = config.SYNTH_N_ILLICIT_ENTITIES
ADDR_PER_LICIT_ENTITY = (1, 4)
ADDR_PER_ILLICIT_ENTITY = (5, 20)   # illicit actors spread funds across many addresses
TX_PER_ENTITY = (10, 60)

START_TIME = datetime(2026, 1, 1)


def rand_ts(base, spread_hours=24 * 90):
    return base + timedelta(seconds=random.randint(0, spread_hours * 3600))


def gen_ip(pool=None):
    if pool:
        return random.choice(pool)
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"


def main():
    addresses = []   # (address_id, entity_id, first_seen)
    entities = []    # (entity_id, label)
    transactions = []
    network_rows = []

    # --- licit entities: normal behaviour, diverse IPs, low fan-out ---
    for _ in range(N_LICIT_ENTITIES):
        entity_id = f"ent_{uuid.uuid4().hex[:8]}"
        entities.append((entity_id, "licit"))
        n_addr = random.randint(*ADDR_PER_LICIT_ENTITY)
        entity_addrs = [f"addr_{uuid.uuid4().hex[:10]}" for _ in range(n_addr)]
        entry_ts = rand_ts(START_TIME)
        for a in entity_addrs:
            addresses.append((a, entity_id, entry_ts.isoformat()))

        n_tx = random.randint(*TX_PER_ENTITY)
        for _ in range(n_tx):
            ts = rand_ts(entry_ts)
            txid = f"tx_{uuid.uuid4().hex[:12]}"
            n_in = random.randint(1, 2)
            n_out = random.randint(1, 2)
            inputs = random.sample(entity_addrs, min(n_in, len(entity_addrs))) or entity_addrs[:1]
            # licit txs mostly settle with addresses outside the entity (regular payments)
            outputs = [f"addr_{uuid.uuid4().hex[:10]}" for _ in range(n_out)]
            amounts = [round(random.uniform(0.001, 2.5), 8) for _ in outputs]
            fee = round(random.uniform(0.00001, 0.0005), 8)
            transactions.append((txid, ts.isoformat(), json.dumps(inputs),
                                  json.dumps(outputs), json.dumps(amounts), fee))
            # network: diverse IPs, timing close to broadcast (normal propagation delay)
            network_rows.append((txid, gen_ip(), random.randint(10000, 60000),
                                  (ts - timedelta(seconds=random.uniform(0.5, 8))).isoformat(),
                                  f"AS{random.randint(1000,60000)}"))

    # --- illicit entities: fan-out chains, shared IP pools (mixer-like), bursty timing ---
    for _ in range(N_ILLICIT_ENTITIES):
        entity_id = f"ent_{uuid.uuid4().hex[:8]}"
        entities.append((entity_id, "illicit"))
        n_addr = random.randint(*ADDR_PER_ILLICIT_ENTITY)
        entity_addrs = [f"addr_{uuid.uuid4().hex[:10]}" for _ in range(n_addr)]
        entry_ts = rand_ts(START_TIME)
        for a in entity_addrs:
            addresses.append((a, entity_id, entry_ts.isoformat()))

        # a small shared IP pool simulates mixer / bot infrastructure
        ip_pool = [gen_ip() for _ in range(random.randint(2, 4))]
        asn_pool = [f"AS{random.randint(1000,60000)}" for _ in range(2)]

        n_tx = random.randint(*TX_PER_ENTITY)
        chain_ts = entry_ts
        for i in range(n_tx):
            # bursty: several txs seconds apart, then a gap -- mimics layering
            if i % 5 == 0:
                chain_ts = rand_ts(chain_ts, spread_hours=6)
            else:
                chain_ts = chain_ts + timedelta(seconds=random.randint(5, 120))
            txid = f"tx_{uuid.uuid4().hex[:12]}"
            # fan-out: one input consolidates several of the entity's own addresses
            n_in = random.randint(2, min(6, n_addr))
            inputs = random.sample(entity_addrs, n_in)
            n_out = random.randint(3, 8)  # fan-out to many outputs
            outputs = random.sample(entity_addrs, min(n_out, n_addr)) if random.random() < 0.6 \
                else [f"addr_{uuid.uuid4().hex[:10]}" for _ in range(n_out)]
            amounts = [round(random.uniform(0.0005, 0.05), 8) for _ in outputs]
            fee = round(random.uniform(0.00001, 0.0002), 8)
            transactions.append((txid, chain_ts.isoformat(), json.dumps(inputs),
                                  json.dumps(outputs), json.dumps(amounts), fee))
            network_rows.append((txid, gen_ip(ip_pool), random.randint(10000, 60000),
                                  (chain_ts - timedelta(seconds=random.uniform(0.1, 2))).isoformat(),
                                  random.choice(asn_pool)))

    # --- write outputs ---
    with open(OUT_DIR / "entities.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entity_id", "label"])
        w.writerows(entities)

    with open(OUT_DIR / "addresses.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["address_id", "entity_id", "first_seen"])
        w.writerows(addresses)

    with open(OUT_DIR / "transactions.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txid", "timestamp", "input_addresses", "output_addresses", "amounts", "fee"])
        w.writerows(transactions)

    with open(OUT_DIR / "network_layer.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["txid", "src_ip", "src_port", "broadcast_ts", "asn"])
        w.writerows(network_rows)

    print(f"entities: {len(entities)}  addresses: {len(addresses)}  "
          f"transactions: {len(transactions)}  network_rows: {len(network_rows)}")
    print(f"written to {OUT_DIR}")


if __name__ == "__main__":
    main()
