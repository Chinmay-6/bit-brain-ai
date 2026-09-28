"""Runs the full offline pipeline end to end: generate -> ingest -> graph -> features -> train."""
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
STEPS = [
    ("Generating synthetic dataset", BASE / "data" / "generate_synthetic_data.py"),
    ("Ingesting into SQLite", BASE / "pipeline" / "ingest.py"),
    ("Building graph + entity clustering", BASE / "pipeline" / "graph_builder.py"),
    ("Computing features", BASE / "pipeline" / "features.py"),
    ("Training models + scoring alerts", BASE / "pipeline" / "train.py"),
]

if __name__ == "__main__":
    for label, script in STEPS:
        print(f"\n=== {label} ===")
        result = subprocess.run([sys.executable, str(script)])
        if result.returncode != 0:
            print(f"FAILED at: {label}")
            sys.exit(1)
    print("\nPipeline complete. Start the API with: uvicorn backend.main:app --reload")
