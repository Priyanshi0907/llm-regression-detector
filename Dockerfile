FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal — SQLite ships with Python, no extra libs needed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    DB_PATH=/app/data/eval_results.db \
    REPORTS_DIR=/app/data/reports \
    PROMPTS_DIR=/app/prompts \
    DATASET_PATH=/app/golden_dataset/dataset_v1.json

RUN mkdir -p /app/data/reports

# Default: run the eval CLI against the latest prompt version.
# Override at `docker run` time, e.g.:
#   docker run --env-file .env myimage python -m src.cli --prompt prompts/v8.yaml
ENTRYPOINT ["python", "-m", "src.cli"]
CMD ["--prompt", "prompts/v8.yaml"]
