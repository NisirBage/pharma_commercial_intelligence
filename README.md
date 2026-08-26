# Pharma Commercial Intelligence Platform

Portfolio project (ZS BTSA interview prep) demonstrating the full path from
business problem → requirements → data → data model → analytics/ML →
optimization → API → dashboard → testing, on a real dataset.

**Scope note:** the source dataset does not support the "territory
optimization" framing implied by this project's working name — see
[docs/00-business-problem.md](docs/00-business-problem.md) for why, and for
the rescoped requirements this build actually targets (demand forecasting,
seasonality/opportunity detection, and inventory optimization for pharmacy
drug-class sales). That decision is pending explicit sign-off before
Milestone 2.

## Milestone status

| Milestone | Scope | Status |
|---|---|---|
| 1 | Project setup, data acquisition, schema discovery, business problem framing | **Complete — awaiting scope decision (Option A vs B, see docs/00-business-problem.md)** |
| 2 | Data model & ETL | Not started |
| 3 | Analytics & forecasting | Not started |
| 4 | Optimization | Not started |
| 5 | Backend API | Not started |
| 6 | Dashboard | Not started |
| 7 | Testing & CI/CD | Not started |

## Dataset

`kagglehub.dataset_download("milanzdravkovic/pharma-sales-data")` — pharmacy
sales volumes for 8 WHO ATC drug classes, Jan 2014–Oct 2019, at hourly/
daily/weekly/monthly granularity. No Kaggle API credentials were required.
See [docs/01-data-dictionary.md](docs/01-data-dictionary.md) for the full,
verified schema and data quality findings.

## Repo layout

```
docs/           Business/requirements/architecture docs (written before code)
data/raw/       Raw CSVs from Kaggle (gitignored — regenerate via scripts/download_data.py)
data/synthetic/ Any synthetic data introduced later (seeded, documented, never mixed with raw/)
scripts/        Standalone data acquisition / inspection scripts
```

Backend, frontend, and infra scaffolding land in Milestone 2+.

## Reproducing the data locally

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install kagglehub pandas
python scripts/download_data.py
python scripts/inspect_schema.py
```
