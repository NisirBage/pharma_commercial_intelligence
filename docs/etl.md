# ETL Pipeline

## Modules (`backend/app/etl/`)

| Module | Responsibility |
|---|---|
| `extract.py` | Reads the 4 raw CSVs from `settings.raw_data_dir`. Pure I/O — no cleaning or interpretation. Raises `FileNotFoundError` loudly if any expected file is missing (never falls back to synthetic/sample data). |
| `reference_data.py` | The external WHO ATC reference table (`ATC_REFERENCE`) — explicitly documented as annotation, not observed data. |
| `validate.py` | Pure, DB-free validation: schema, date-parse, null, duplicate, numeric-range, hour-of-day-range checks per file, plus the two cross-file investigations from M2 (`daily_hour_artifact_formula`, `reconciliation_*`). Returns a `list[CheckResult]`; never raises for a data problem — that's a caller decision (`has_blocking_failures`). |
| `transform.py` | Renames/types raw columns into each staging table's shape; melts the wide hourly staging frame into the long canonical shape (`transform_canonical_fact`). |
| `load.py` | Writes to Postgres via SQLAlchemy: seeds `dim_atc_class` (upsert), full-refreshes staging + fact tables, loads the canonical fact table with FK traceability back to `stg_sales_hourly`, and persists quality-check results. |
| `quality_report.py` | Builds the machine-readable data-quality report (per-file total/valid/rejected record counts + every check result) and writes it as timestamped JSON under `settings.quality_report_dir`. |
| `run_pipeline.py` | Orchestrates all of the above: extract -> validate -> (write report) -> [abort if blocking] -> transform -> load -> commit. Entry point: `python -m app.etl.run_pipeline` from `backend/`. |

## Why full-refresh, not incremental

`milanzdravkovic/pharma-sales-data` is a **fixed historical export**
(2014–2019), not a live feed — there is no "new data since last run"
concept. Every pipeline run therefore truncates `fact_demand_hourly` and
all four staging tables and reloads them from the current CSVs, inside one
transaction (commit only at the very end). `dim_atc_class` is the
exception — it's static reference data, so it's upserted (insert-if-absent)
rather than truncated, and stays stable across runs.

This is what makes the pipeline **reproducible**: run it twice against the
same CSVs and you get the same row counts, not doubled ones — verified in
`tests/integration/test_load.py::test_reload_is_idempotent_not_additive`.

## Row-level validity vs. dataset-level checks

Two different granularities of "data quality" are both tracked:

1. **Row-level** (`quality_report.summarize_dataset`): a row is valid if
   its date parses and no product column is negative. Reported as
   `total_records` / `valid_records` / `rejected_records` per file. On the
   current dataset every row is valid (0 rejected) — but this is a real
   computation, not a hardcoded pass, so a future refresh with bad rows
   would actually be caught and counted.
2. **Dataset/cross-file-level** (`validate.py`'s `CheckResult`s): schema
   shape, cross-granularity reconciliation, the `Hour` artifact formula,
   etc. These are what caught the two findings in
   docs/data-quality-decisions.md.

## Pass / fail / warn semantics

- **`pass`** — check succeeded, nothing to report.
- **`fail`** — a real, unexpected problem (e.g. schema drift, a null value,
  a broken reconciliation that wasn't already investigated and explained).
  `has_blocking_failures()` returning `True` **aborts the pipeline before
  any DB write** — the run is still recorded (`etl_run.status = "failed"`)
  with its quality checks persisted, so the failure is visible, but nothing
  is loaded on top of a validation problem that hasn't been looked at.
- **`warn`** — a known, already-investigated, documented issue that
  shouldn't block a run. Currently exactly one: `reconciliation_monthly_vs_daily`,
  which is *expected* to report mismatches (see Decision 2) — treating it
  as `fail` would mean the pipeline can never succeed against this dataset,
  which is wrong; treating it as silent `pass` would hide a real,
  documented data quality issue from the report. `warn` is the honest
  middle state.

## Reproducibility

From a clean checkout:

```bash
# 1. Get the raw data (from the project root)
python scripts/download_data.py

# 2. (Optional) re-verify the Hour-column / reconciliation findings
python scripts/investigate_hour_column.py

# 3. Run the pipeline (from backend/, needs a reachable Postgres —
#    see backend/app/core/config.py for the POSTGRES_*/DATABASE_URL env vars)
python -m app.etl.run_pipeline
```

No path in the pipeline is hard-coded to this machine — `app/core/config.py`
reads `RAW_DATA_DIR`, `POSTGRES_*`/`DATABASE_URL`, and
`QUALITY_REPORT_DIR` from environment variables (or an `.env` file at the
project root), with defaults that work out of the box for a standard
checkout.

## What could not be verified this milestone

No Postgres credentials were available in this environment (see the M2
completion report). Everything through `transform.py` and `load.py`'s SQL
logic **was** run end-to-end against the real, full dataset (all 50,532
hourly rows) using an in-memory/file SQLite engine as a substitute — this
validated the ETL logic itself (idempotency, FK traceability, row counts,
melt correctness) but not Postgres-specific behavior: the 3 SQL views
(`vw_demand_daily/weekly/monthly`, which use `date_trunc`/`EXTRACT(DOW ...)`,
Postgres-only syntax) and the Alembic migration have not been executed
against a real Postgres instance. This is the top item for M3 setup.

## Testing

`backend/tests/`, run via `pytest` from `backend/`:

- **Unit** (`tests/unit/`): `extract`, `validate`, `transform`,
  `quality_report` — all pure-Python/pandas, no DB. Includes both
  "clean fixture passes" tests and deliberately-broken-input tests (missing
  schema column, null value, negative unit count) to prove each check
  actually catches what it claims to.
- **Integration** (`tests/integration/test_load.py`): full load against
  in-memory SQLite — row counts, FK traceability from fact back to
  staging, idempotent-reload, and a deliberate-failure case (loading fact
  rows before staging exists must raise, not silently corrupt data).
- **Fixtures** (`tests/fixtures/pharma_mini/`): a tiny (4-hour, 2-day),
  fully hand-computed dataset reproducing the two real findings —
  `salesdaily.Hour` matches the sum-of-hourly formula exactly, and
  `salesmonthly.csv` has one deliberately injected mismatch (mirroring the
  real dataset's Decision 2 pattern) to prove the reconciliation check
  actually detects it rather than always passing.

24/24 tests passing as of this milestone (see the M2 completion report for
the full run output).
