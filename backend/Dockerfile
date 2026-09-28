FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY pipeline/ pipeline/
COPY backend/ backend/
COPY data/ data/
COPY docs/ docs/

# Path overrides must match at build time (so the pipeline writes here) and at
# runtime (so the API reads from the same place). docker-compose passes the
# same values to both build args and the container's `environment:` block --
# if you override DATABASE_PATH/GRAPH_PATH/etc in .env, both stay in sync
# automatically; you don't need to edit this file.
ARG DATABASE_PATH=/app/bitbrain.db
ARG GRAPH_PATH=/app/pipeline/graph.gpickle
ARG MODEL_DIR=/app/pipeline/models
ARG FEATURES_PATH=/app/pipeline/features.csv
ARG RAW_DATA_DIR=/app/data/raw
ARG METRICS_PATH=/app/docs/model_metrics.json
ARG SYNTH_SEED=42
ARG SYNTH_N_LICIT_ENTITIES=120
ARG SYNTH_N_ILLICIT_ENTITIES=25
ENV DATABASE_PATH=${DATABASE_PATH} \
    GRAPH_PATH=${GRAPH_PATH} \
    MODEL_DIR=${MODEL_DIR} \
    FEATURES_PATH=${FEATURES_PATH} \
    RAW_DATA_DIR=${RAW_DATA_DIR} \
    METRICS_PATH=${METRICS_PATH} \
    SYNTH_SEED=${SYNTH_SEED} \
    SYNTH_N_LICIT_ENTITIES=${SYNTH_N_LICIT_ENTITIES} \
    SYNTH_N_ILLICIT_ENTITIES=${SYNTH_N_ILLICIT_ENTITIES}

# Run the full offline pipeline once at image build time so the container
# starts with a populated database and trained models already on disk.
RUN python pipeline/run_pipeline.py

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
