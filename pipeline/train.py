"""
AI/ML core:
  1. IsolationForest  - unsupervised anomaly pre-filter, needs no labels
  2. RandomForestClassifier - supervised baseline on labeled entities
  3. SHAP TreeExplainer - per-entity top feature drivers (why flagged)
  4. risk_score = weighted combo of RF probability + IF anomaly score
     -> ranked, written into the `alerts` table the API serves directly

Models are saved to pipeline/models/ so the API never has to retrain at request
time, and so the whole thing works fully offline after this script has run once.
"""
import json
import sqlite3
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

BASE = Path(__file__).parent.parent
DB_PATH = config.DATABASE_PATH
FEATURES_PATH = config.FEATURES_PATH
MODEL_DIR = config.MODEL_DIR
MODEL_DIR.mkdir(parents=True, exist_ok=True)
METRICS_PATH = config.METRICS_PATH
METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    "n_addresses", "n_transactions", "graph_degree", "fan_out_addresses",
    "n_counterparties", "burstiness", "distinct_ips", "distinct_asns", "ip_per_tx_ratio",
]

# risk_score weighting: tune via RISK_WEIGHT_SUPERVISED / RISK_WEIGHT_ANOMALY env vars
W_SUPERVISED = config.RISK_WEIGHT_SUPERVISED
W_ANOMALY = config.RISK_WEIGHT_ANOMALY


def run():
    df = pd.read_csv(FEATURES_PATH)
    X = df[FEATURE_COLS].fillna(0)

    # --- 1. Isolation Forest: unsupervised, runs on everything, no labels required ---
    iso = IsolationForest(n_estimators=200, contamination="auto", random_state=42)
    iso.fit(X)
    # decision_function: higher = more normal. Flip + normalize to 0..1 "anomaly score"
    raw_scores = -iso.decision_function(X)
    anomaly_score = (raw_scores - raw_scores.min()) / (raw_scores.max() - raw_scores.min() + 1e-9)
    df["anomaly_score"] = anomaly_score

    # --- 2. Random Forest: supervised, trained only on labeled entities ---
    # A user-uploaded dataset may have no ground-truth labels at all (every
    # entity "unknown"), or too few of one class to train/stratify. Detect
    # that up front and fall back to pure anomaly-based scoring rather than
    # crashing the pipeline -- this is the realistic case for real forensic
    # exports, not an edge case to ignore.
    labeled = df[df["label"].isin(["licit", "illicit"])].copy()
    n_classes = labeled["label"].nunique()
    MIN_LABELED_PER_CLASS = 3
    class_counts = labeled["label"].value_counts()
    has_enough_labels = (
        n_classes >= 2 and class_counts.min() >= MIN_LABELED_PER_CLASS
    )

    if has_enough_labels:
        y = (labeled["label"] == "illicit").astype(int)
        X_labeled = labeled[FEATURE_COLS].fillna(0)

        X_train, X_test, y_train, y_test = train_test_split(
            X_labeled, y, test_size=0.25, stratify=y, random_state=42
        )
        rf = RandomForestClassifier(
            n_estimators=300, max_depth=8, class_weight="balanced", random_state=42
        )
        rf.fit(X_train, y_train)

        y_pred = rf.predict(X_test)
        y_prob_test = rf.predict_proba(X_test)[:, 1]
        metrics = {
            "mode": "supervised",
            "precision": round(precision_score(y_test, y_pred, zero_division=0), 4),
            "recall": round(recall_score(y_test, y_pred, zero_division=0), 4),
            "roc_auc": round(roc_auc_score(y_test, y_prob_test), 4),
            "n_train": int(len(X_train)),
            "n_test": int(len(X_test)),
        }
        print("RandomForest holdout metrics:", metrics)

        df["model_probability"] = rf.predict_proba(X)[:, 1]

        # --- 3. SHAP explanations for every entity ---
        explainer = shap.TreeExplainer(rf)
        shap_values = explainer.shap_values(X)
        if isinstance(shap_values, list):
            shap_illicit = shap_values[1]
        elif shap_values.ndim == 3:
            shap_illicit = shap_values[:, :, 1]
        else:
            shap_illicit = shap_values

        top_features_per_row = []
        for i in range(len(df)):
            contribs = list(zip(FEATURE_COLS, shap_illicit[i]))
            contribs.sort(key=lambda x: abs(x[1]), reverse=True)
            top3 = [{"feature": f, "impact": round(float(v), 4)} for f, v in contribs[:3]]
            top_features_per_row.append(top3)
        df["top_features"] = [json.dumps(t) for t in top_features_per_row]

        joblib.dump(rf, MODEL_DIR / "random_forest.joblib")
        effective_w_supervised = W_SUPERVISED
        effective_w_anomaly = W_ANOMALY
    else:
        # Not enough labeled data to train or trust a supervised model.
        # Score purely on the Isolation Forest, and explain each flag with
        # a z-score-based "how unusual is this feature" ranking instead of
        # SHAP -- same UI shape (signed top-3 features), honestly different
        # underlying method, and this is stated plainly in the metrics file
        # rather than silently pretending it's a trained-model explanation.
        metrics = {
            "mode": "unsupervised_only",
            "reason": f"insufficient labeled data (found {n_classes} class(es), "
                      f"need >= 2 with >= {MIN_LABELED_PER_CLASS} examples each)",
            "n_labeled": int(len(labeled)),
        }
        print("Skipping supervised training:", metrics["reason"])

        df["model_probability"] = 0.0

        means = X.mean()
        stds = X.std().replace(0, 1)
        z = (X - means) / stds

        top_features_per_row = []
        for i in range(len(df)):
            contribs = list(zip(FEATURE_COLS, z.iloc[i]))
            contribs.sort(key=lambda x: abs(x[1]), reverse=True)
            top3 = [{"feature": f, "impact": round(float(v), 4)} for f, v in contribs[:3]]
            top_features_per_row.append(top3)
        df["top_features"] = [json.dumps(t) for t in top_features_per_row]

        effective_w_supervised = 0.0
        effective_w_anomaly = 1.0

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    # --- 4. combined risk score + rank ---
    df["risk_score"] = (
        effective_w_supervised * df["model_probability"] + effective_w_anomaly * df["anomaly_score"]
    ) * 100
    df["risk_score"] = df["risk_score"].round(2)
    df = df.sort_values("risk_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1

    # --- persist models ---
    joblib.dump(iso, MODEL_DIR / "isolation_forest.joblib")
    joblib.dump(FEATURE_COLS, MODEL_DIR / "feature_cols.joblib")
    print("models saved ->", MODEL_DIR)

    # --- write alerts table (this is what the API serves) ---
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS alerts (
        entity_id TEXT PRIMARY KEY,
        risk_score REAL,
        rank INTEGER,
        model_probability REAL,
        anomaly_score REAL,
        top_features TEXT,
        status TEXT DEFAULT 'open'
    )""")
    rows = [
        (r.entity_id, r.risk_score, int(r.rank), round(r.model_probability, 4),
         round(r.anomaly_score, 4), r.top_features, "open")
        for r in df.itertuples()
    ]
    conn.executemany(
        """INSERT INTO alerts (entity_id, risk_score, rank, model_probability, anomaly_score, top_features, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(entity_id) DO UPDATE SET
             risk_score=excluded.risk_score, rank=excluded.rank,
             model_probability=excluded.model_probability, anomaly_score=excluded.anomaly_score,
             top_features=excluded.top_features""",
        rows,
    )
    conn.commit()
    conn.close()
    print(f"alerts table populated: {len(rows)} entities scored & ranked")


if __name__ == "__main__":
    run()
