# Pharmaceutical Demand Intelligence & Supply Planning Platform

Portfolio project demonstrating the full path from
business problem → requirements → data → data model → analytics/ML →
optimization → API → dashboard → testing, on a real dataset.

**Scope note:** the source dataset does not support the "territory
optimization" framing implied by this project's original working name —
rescoped to demand forecasting, seasonality/anomaly detection, and
inventory/supply-planning optimization. See
[docs/00-business-problem.md](docs/00-business-problem.md) for the full
reasoning (approved: Option A).

## Milestone status

| Milestone | Scope | Status |
|---|---|---|
| 1 | Project setup, data acquisition, schema discovery, business problem framing | **Complete** |
| 2 | Data model & ETL | **Complete** — see [docs/data-model.md](docs/data-model.md) / [docs/etl.md](docs/etl.md) / [docs/data-quality-decisions.md](docs/data-quality-decisions.md) |
| 3 | Demand intelligence & exploratory analytics | **Complete** — see [docs/analytics-methodology.md](docs/analytics-methodology.md) / [docs/business-insights.md](docs/business-insights.md) |
| 4 | Demand forecasting | **Complete** — see [docs/forecasting-methodology.md](docs/forecasting-methodology.md) / [docs/model-selection.md](docs/model-selection.md) / [docs/forecasting-leakage-audit.md](docs/forecasting-leakage-audit.md) / [docs/forecasting-insights.md](docs/forecasting-insights.md) |
| 5 | Inventory & supply planning optimization | **Complete** — see [docs/optimization-methodology.md](docs/optimization-methodology.md) / [docs/planning-assumptions.md](docs/planning-assumptions.md) / [docs/optimization-insights.md](docs/optimization-insights.md) / [docs/data-gap-analysis.md](docs/data-gap-analysis.md) |
| 6 | Backend API (FastAPI) | **Complete** — see [docs/api-design.md](docs/api-design.md) / [docs/interview-guide.md](docs/interview-guide.md) |
| 7 | Dashboard | Not started |
| 8 | Testing & CI/CD hardening | Not started |

## Dataset

`kagglehub.dataset_download("milanzdravkovic/pharma-sales-data")` — pharmacy
sales volumes for 8 WHO ATC drug classes, Jan 2014–Oct 2019, at hourly/
daily/weekly/monthly granularity. No Kaggle API credentials were required.
See [docs/01-data-dictionary.md](docs/01-data-dictionary.md) for the full,
verified schema and data quality findings, and
[docs/data-quality-decisions.md](docs/data-quality-decisions.md) for the
two investigated anomalies (the `Hour` column artifact, and the
`salesmonthly.csv` reconciliation defect).

## Repo layout

```
docs/                    Business/requirements/architecture/data docs (written before code)
data/raw/                Raw CSVs from Kaggle (gitignored — regenerate via scripts/download_data.py)
data/synthetic/          Any synthetic data introduced later (seeded, documented, never mixed with raw/)
scripts/                 Standalone data acquisition / investigation scripts
backend/app/core/        Configuration (env-driven, no hard-coded paths)
backend/app/models/      SQLAlchemy ORM models (dims, staging, canonical fact, ETL metadata)
backend/app/etl/         Extract / validate / transform / load / quality-report / pipeline runner
backend/app/analytics/   KPIs, trends, seasonality, ATC-class analysis, volatility, anomalies, reconciliation
backend/app/forecasting/ Datasets, features, baselines, ETS/ML models, backtesting, metrics, selection, diagnostics, predictions, model registry
backend/app/optimization/ Demand input (reuses M4), safety stock, reorder point, LP allocation (OR-Tools), scenarios, sensitivity, recommendations
backend/app/api/         FastAPI routes, dependency injection, exception handlers, request-logging middleware
backend/app/schemas/     Pydantic request/response models (also the OpenAPI source of truth)
backend/app/services/    Request/response translation, input validation, and caching over M3/M4/M5
backend/app/db/migrations/  Alembic migrations
backend/tests/           pytest — unit (pure logic) + integration (SQLite-backed load tests, real-data API tests) + api (FastAPI TestClient, synthetic fixtures)
```

Frontend scaffolding lands in Milestone 7+.

## API

```
Frontend
   |
FastAPI (backend/app/main.py)
   |
Service layer (backend/app/services/)
   |
Analytics / Forecasting / Optimization (M3 / M4 / M5)
   |
PostgreSQL (optional) / canonical CSV-derived data (M2)
```

Run locally (needs `data/raw/*.csv` from `scripts/download_data.py`, and
ideally `backend/data/model_registry/*.json` from
`scripts/run_m4_backtest.py` for the forecast/optimization endpoints):

```bash
cd backend
uvicorn app.main:app --reload
```

Interactive docs: `http://localhost:8000/docs` (Swagger) or
`http://localhost:8000/redoc`. Full architecture, caching strategy, and
security review: [docs/api-design.md](docs/api-design.md).

Sample request/response:

```bash
curl http://localhost:8000/api/v1/kpis/summary
```
```json
{
  "data": {
    "total_demand": 127595.5,
    "average_daily_demand": 60.59,
    "peak_daily_demand": 198.95,
    "dominant_atc_class": "N02BE",
    "dominant_atc_share_pct": 49.38,
    "period": {"start": "2014-01-02", "end": "2019-10-08"}
  },
  "metadata": {"generated_at": "...", "source": "M3 analytics"}
}
```

```bash
curl -X POST http://localhost:8000/api/v1/optimization/run \
  -H "Content-Type: application/json" \
  -d '{"scenario": "balanced"}'
```

## Reproducing the data + pipeline locally

```bash
# From the project root: get the raw data
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install kagglehub pandas
python scripts/download_data.py
python scripts/inspect_schema.py
python scripts/investigate_hour_column.py   # re-verify the Hour-column finding

# Backend / ETL / API
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest                                       # 277 tests (see docs/etl.md, docs/forecasting-methodology.md, docs/optimization-methodology.md, docs/api-design.md)
# python -m app.etl.run_pipeline             # needs a reachable Postgres — see app/core/config.py
python scripts/run_m4_backtest.py            # reproduces every forecasting number in docs/; also populates the model registry the API's forecast/optimization endpoints read
python scripts/run_m5_optimization.py        # reproduces every optimization number in docs/ (needs run_m4_backtest.py first)
uvicorn app.main:app --reload                # http://localhost:8000/docs
```
