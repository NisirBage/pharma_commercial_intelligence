# Pharmaceutical Demand Intelligence & Supply Planning Platform

Portfolio project (ZS BTSA interview prep) demonstrating the full path from
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
| 5 | Optimization | Not started |
| 6 | Backend API | Not started |
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
backend/app/db/migrations/  Alembic migrations
backend/tests/           pytest — unit (pure logic) + integration (SQLite-backed load tests)
```

Frontend and API scaffolding land in Milestone 6+.

## Reproducing the data + pipeline locally

```bash
# From the project root: get the raw data
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install kagglehub pandas
python scripts/download_data.py
python scripts/inspect_schema.py
python scripts/investigate_hour_column.py   # re-verify the Hour-column finding

# Backend / ETL
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest                                       # 144 tests (see docs/etl.md, docs/forecasting-methodology.md)
# python -m app.etl.run_pipeline             # needs a reachable Postgres — see app/core/config.py
python scripts/run_m4_backtest.py            # reproduces every forecasting number in docs/
```
