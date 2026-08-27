# Packages the API alone (no database container — see docs/api-design.md,
# "Deployment considerations", for why a full docker-compose stack wasn't
# built in M6). Build from the backend/ directory:
#
#   docker build -t pharma-ci-api .
#   docker run -p 8000:8000 --env-file ../.env pharma-ci-api
#
# The container needs data/raw/*.csv (scripts/download_data.py) and
# data/model_registry/*.json (scripts/run_m4_backtest.py) mounted or
# baked in — the API's primary data path is CSV-derived, not the
# database (see docs/api-design.md).

FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
