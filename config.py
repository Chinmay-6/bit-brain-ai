"""
Central configuration for Bit-Brain AI. Every value here is overridable via
environment variable, with a working local default so the project runs with
zero configuration out of the box. Both the pipeline scripts (data/, pipeline/)
and the backend (backend/main.py) import from this single module so there is
exactly one place that knows about paths, ports, and tunable weights.

Copy .env.example to .env and edit it; docker-compose reads .env automatically.
For a manual (non-Docker) run, export these in your shell or use a tool like
`python-dotenv` / `honcho` if you prefer -- this project intentionally avoids
that dependency and just reads os.environ directly, so plain `export VAR=val`
works everywhere including inside the offline Linux target environment.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent


def _bool(name, default):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


# --- storage paths (swap these to point at a different volume/mount) ---
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", str(BASE_DIR / "bitbrain.db")))
GRAPH_PATH = Path(os.environ.get("GRAPH_PATH", str(BASE_DIR / "pipeline" / "graph.gpickle")))
MODEL_DIR = Path(os.environ.get("MODEL_DIR", str(BASE_DIR / "pipeline" / "models")))
FEATURES_PATH = Path(os.environ.get("FEATURES_PATH", str(BASE_DIR / "pipeline" / "features.csv")))
RAW_DATA_DIR = Path(os.environ.get("RAW_DATA_DIR", str(BASE_DIR / "data" / "raw")))
METRICS_PATH = Path(os.environ.get("METRICS_PATH", str(BASE_DIR / "docs" / "model_metrics.json")))

# --- backend server ---
BACKEND_HOST = os.environ.get("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", 8000))
CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")]
LOG_LEVEL = os.environ.get("LOG_LEVEL", "info")

# --- frontend (consumed by docker-compose port mapping; the frontend itself
#     reads its own VITE_* vars at build time, see frontend/.env.example) ---
FRONTEND_PORT = int(os.environ.get("FRONTEND_PORT", 8080))

# --- risk scoring weights (see pipeline/train.py) ---
RISK_WEIGHT_SUPERVISED = float(os.environ.get("RISK_WEIGHT_SUPERVISED", 0.65))
RISK_WEIGHT_ANOMALY = float(os.environ.get("RISK_WEIGHT_ANOMALY", 0.35))

# --- risk tiers used by /api/overview; keep in sync with frontend/.env's
#     VITE_RISK_TIER_HIGH / VITE_RISK_TIER_MEDIUM if you change these ---
RISK_TIER_HIGH = float(os.environ.get("RISK_TIER_HIGH", 70))
RISK_TIER_MEDIUM = float(os.environ.get("RISK_TIER_MEDIUM", 40))

# --- synthetic data generator (data/generate_synthetic_data.py) ---
SYNTH_SEED = int(os.environ.get("SYNTH_SEED", 42))
SYNTH_N_LICIT_ENTITIES = int(os.environ.get("SYNTH_N_LICIT_ENTITIES", 120))
SYNTH_N_ILLICIT_ENTITIES = int(os.environ.get("SYNTH_N_ILLICIT_ENTITIES", 25))

# --- misc ---
GRAPH_MAX_SUBGRAPH_NODES = int(os.environ.get("GRAPH_MAX_SUBGRAPH_NODES", 300))
ALERTS_DEFAULT_LIMIT = int(os.environ.get("ALERTS_DEFAULT_LIMIT", 50))
