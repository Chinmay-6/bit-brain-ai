# Bit-Brain AI — Technical Write-up

**SIH26146 · AI-Powered Monitoring & Analysis of Bitcoin Transaction Traffic · Team Bit Brainers**

## 1. Approach

Bit-Brain AI treats Bitcoin forensics as a **two-layer correlation problem**: the
blockchain ledger (addresses, transactions, amounts) and the network layer (source
IP, port, broadcast timestamp) are fused into a single evidence graph rather than
analyzed separately. This is deliberate — existing tools that look only at
transaction-to-transaction relationships miss infrastructure-level signals (shared
IPs, mixer-like broadcast patterns) that are exactly what distinguishes coordinated
illicit activity from normal usage.

Pipeline: **ingest → normalize → build address–transaction graph → cluster
addresses into entities → engineer structural/temporal/cross-layer features →
score with a hybrid ML model → explain with SHAP → rank into an investigator
queue.** Every stage persists its output, so any stage can be re-run independently
during casework.

## 2. Data

Public forensic datasets such as Elliptic++ provide labeled blockchain data but
**not** packet-level network metadata tied to transaction IDs — that join does not
exist in any public dataset, so it cannot be sourced, only generated. For this
prototype, `data/generate_synthetic_data.py` produces both layers together, with
explicitly injected patterns:

- **Licit entities**: 1–4 addresses, diverse source IPs, low fan-out, payments to
  addresses outside the entity.
- **Illicit entities**: 5–20 addresses, transactions drawn from a **small shared
  IP/ASN pool** (simulating mixer or bot infrastructure), high fan-out (many-input
  consolidation followed by many-output distribution), and **bursty timing**
  (rapid transaction sequences followed by gaps — a layering signature).

This is stated openly rather than presented as real forensic data. The pipeline
itself is data-source agnostic: pointing `pipeline/ingest.py` at real Elliptic++
exports (or a live forensic dataset for the final round) requires no changes
downstream.

## 3. Graph construction

We build a **directed bipartite graph**: address nodes and transaction nodes, with
edges `input_address → tx` and `tx → output_address`. This preserves Bitcoin's
native many-to-many transaction structure rather than collapsing it into a single
flat table.

**Entity clustering** uses the standard multi-input heuristic: addresses that
appear together as inputs to the same transaction are assumed to be controlled by
one actor (a wallet typically must hold the private keys for every input it
spends). This is treated as *useful but imperfect* in the write-up and the UI —
privacy-preserving wallets and CoinJoin-style transactions can defeat it, which is
why the model layer does not rely on clustering alone for its verdict.

## 4. Model choice

A **hybrid two-model design**, not a single classifier:

| Model | Type | Role |
|---|---|---|
| Isolation Forest | Unsupervised | Runs on every entity, no labels required. Catches novel patterns a supervised model has never seen. |
| Random Forest | Supervised | Trained on labeled entities. Provides a calibrated probability and — critically — is directly SHAP-explainable. |

**Why not rules-only**: a rules engine can only catch patterns its author already
anticipated. **Why not GNN-only for the MVP**: graph neural networks need more
labeled data and tuning time than a hackathon prototype allows to be trustworthy;
they are the documented stretch goal (see §7), evaluated against this RF baseline
rather than replacing it outright. **Why not RL/LSTM/streaming**: those were in our
early architecture sketch but do not fit this problem — there are no "actions" to
take on someone else's Bitcoin, and the problem statement supplies static forensic
exports, not a live stream, so a batch pipeline is the correct fit, not a
compute/complexity liability.

On the held-out test split from this prototype's dataset: precision **1.00**,
recall **1.00**, ROC-AUC **1.00** (108 train / 37 test entities — see
`docs/model_metrics.json`, regenerated automatically on every `train.py` run).
These numbers are expected to be near-perfect on this synthetic set because the
injected fraud patterns are cleanly separable in feature space by design, for
demo legibility. On real forensic data we expect performance closer to the
published Elliptic++ benchmark for Random Forest — **97.5% precision / 71.9%
recall** for transaction-level detection — which is the number to cite for
real-world expectations, not the synthetic holdout figure.

**Risk score** = `0.65 × RF probability + 0.35 × normalized anomaly score`,
scaled to 0–100 and ranked. The weighting is a tunable constant in
`pipeline/train.py`, not a hardcoded verdict — as labeled data grows relative to
unlabeled, the supervised weight should increase.

## 5. Explainability

Every scored entity carries its **top-3 SHAP feature contributions** (positive =
pushes risk up, negative = pushes risk down), computed once at training time and
served directly by the API — no explanation is generated live, keeping inference
fast and fully offline.

The dashboard surfaces this three ways per case, matching what an investigator
actually needs to act:
1. **Why flagged** — SHAP bar chart with signed contributions.
2. **How connected** — a 2-hop evidence subgraph (addresses + transactions),
   interactive and zoomable, so the analyst can see the fan-out/clustering
   structure directly rather than trust a score.
3. **How confident** — supervised probability and unsupervised anomaly score
   shown *separately*, so an analyst can tell whether a flag rests on a known
   pattern (high RF probability) or a novel one (high anomaly score, lower RF
   probability) — these warrant different investigative approaches.

**Known limitation, stated explicitly**: SHAP explains what the model relied
on, not ground truth about intent. A human-in-the-loop review step (the
mark-reviewed/flagged/safe actions in the dashboard, backed by `/api/feedback`)
is a first-class part of the design, not an afterthought — this matches the
literature's consistent finding that automated scores should route to analyst
review, not stand alone as a verdict.

## 6. Dashboard

Three screens, each answering one investigator question:

- **Overview** — how much risk is in the queue right now (counts by tier).
- **Alert Queue** — sortable, filterable ranked list; the primary triage view.
- **Case View** — the evidence graph, SHAP drivers, full transaction timeline
  (with correlated IP/ASN per transaction), and mark-safe/flag actions, all for
  one entity at once.

## 7. Deployment & offline guarantee

Single `docker-compose up --build`. The backend image runs the entire pipeline
at build time (data generation → ingestion → graph → features → training), so the
running container never makes a network call — verified by building and running
with the host's network disconnected. Storage is SQLite + a NetworkX graph
pickle for this prototype; `pipeline/ingest.py` and `backend/main.py` isolate all
storage access so swapping to PostgreSQL/TimescaleDB + Neo4j for a
production-scale deployment touches only those two files.

## 8. What's next (honestly scoped, not implemented in this prototype)

- GCN/GAT model trained on the same graph, benchmarked against the RF baseline
  rather than assumed superior.
- Cross-chain correlation (this build is single-chain by design, matching the
  problem statement's Bitcoin-only scope).
- Active-learning loop feeding investigator feedback (`/api/feedback`) back into
  retraining — the endpoint exists; the retraining loop does not yet.
