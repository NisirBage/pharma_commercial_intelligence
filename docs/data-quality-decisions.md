# Data Quality Decisions

This document records data quality issues found in
`milanzdravkovic/pharma-sales-data`, the investigation performed for each,
and the resulting decision — with the evidence, not a guess. Investigation
scripts live in `scripts/` and are re-runnable against the raw CSVs.

---

## Decision 1: The `Hour` column in `salesdaily.csv`

**Investigation:** [scripts/investigate_hour_column.py](../scripts/investigate_hour_column.py)

### Finding

`salesdaily.csv`'s `Hour` column takes only 3 distinct values across all
2,106 rows: `276` (2,104 rows), `248` (1 row, 2014-01-02 — the first date in
the whole dataset), and `190` (1 row, 2019-10-08 — the last date in the
whole dataset).

Cross-referencing against `saleshourly.csv` (the only file with a genuine
0–23 hour-of-day column) proves the mechanism exactly:

**`salesdaily.Hour` is the arithmetic SUM of the hour-of-day values (`Hour`
column, range 0–23) of every `saleshourly.csv` row recorded for that date.**

- For a normal day with all 24 hours recorded (0 through 23):
  `sum(0..23) = 276` — matches the dominant value.
- 2014-01-02 (the dataset's first day) only has hourly records for hours
  8–23 (16 rows, the collection window evidently started mid-day):
  `sum(8..23) = 248` — exact match.
- 2019-10-08 (the dataset's last day) only has hourly records for hours
  0–19 (20 rows, the collection window evidently ended mid-day):
  `sum(0..19) = 190` — exact match.

This was verified as an **exact match on all 2,106/2,106 rows**
(`daily.Hour == sum(hourly.Hour for that date)`, correlation 1.0, zero
exceptions). It is not a hypothesis — it is the confirmed generating formula.

### Interpretation

This is a byproduct of whatever script the dataset's original author used to
produce `salesdaily.csv` from `saleshourly.csv` — almost certainly a
`groupby(date).sum()` where the numeric `Hour` column got swept into the
aggregation along with the real product columns, instead of being dropped
first. It carries **no business meaning whatsoever** — it is not a
duration, a transaction count, an hour-of-day, or any other interpretable
quantity. It is an artifact of the source's own data-prep pipeline.

### Decision

- **Retained as-is in the staging layer** (`stg_sales_daily`), renamed to
  `hour_sum_artifact` with a `NOT NULL` comment documenting exactly this
  finding, for full source-fidelity/audit traceability (raw files are
  immutable; staging should reflect the source honestly, artifacts
  included).
- **Excluded entirely from the canonical analytical model**
  (`fact_demand_hourly` and all derived views). It must never be surfaced
  as a metric, feature, or dashboard field.
- **Not treated as a data quality defect** in the demand values themselves
  — every other column in `salesdaily.csv` reconciles exactly with
  `saleshourly.csv` (see Decision 2 methodology), so this is isolated to
  one meaningless column, not a sign of broader corruption in that file.

---

## Decision 2: Cross-granularity reconciliation (daily / weekly / monthly)

**Investigation:** ad hoc reconciliation, run from the project root:
```
python -c "..."   # see docs/data-quality-decisions.md history / scripts/investigate_hour_column.py for the pattern
```
(Query summed the 8 product columns for the appropriate daily window and
diffed against the coarser file, per pair below.)

Since the four files are pre-aggregated views of the same underlying
transactions (per M1), it's necessary to check whether they actually agree
before deciding whether higher grains can be trusted or must be recomputed
from a single source of truth.

### daily vs. hourly — reconciles exactly

`salesdaily` values equal `SUM(saleshourly)` grouped by date, for **all 8
product columns across all 2,106 dates** (max abs diff = 0.0000). Fully
trustworthy derivation.

### weekly vs. daily — reconciles exactly

`salesweekly` uses **Sunday-ending, trailing 7-day windows**. Summing
`salesdaily` over each such window and comparing to `salesweekly` gives
**zero mismatches across all 302 weeks × 8 columns (2,416 cells)**. Fully
trustworthy derivation.

### monthly vs. daily — does NOT reconcile; genuine source defect found

Summing `salesdaily` by calendar month and comparing to `salesmonthly`
gives **61 mismatches out of 560 cells (33 of the 70 months affected,
47%)**. Most are small (tens of units, plausibly a different aggregation
method or minor rounding upstream), but two months show a large,
structural defect:

- **January 2017**: `salesmonthly` reports ~0 for 7 of 8 columns (one
  column shows `1.0`) while the daily-sum for that month is in the
  hundreds to low thousands per column (e.g. N02BE: monthly file says
  `0.0`, daily-sum says `1439.36`).
- **February 2017**: every column in `salesmonthly` is systematically
  *lower* than the daily-sum for that month, by amounts in the same rough
  magnitude as January's missing totals.

This pattern (one month near-zero, the next month low) is consistent with
a monthly-boundary/date-indexing bug in whatever process generated
`salesmonthly.csv` — e.g. late-December or January transactions
misattributed across the month boundary — rather than random noise. It
cannot be corrected from the data available (no row-level source exists to
re-derive the "correct" monthly figure), so it is not corrected — it is
flagged and the file is not used as a source of truth.

### Decision — canonical grain and model shape

1. **`saleshourly.csv` is the canonical base grain.** It is the finest
   available resolution and both coarser files that could be checked
   against it (`salesdaily`, transitively `salesweekly`) reconcile
   exactly.
2. **`salesdaily.csv` and `salesweekly.csv` are trustworthy** but are
   *derived*, not independent — the canonical fact table is built once,
   from hourly, and daily/weekly analytical views are computed **from the
   canonical fact table**, not by loading the daily/weekly CSVs as a
   second source of the same numbers (this is what avoids double-counting
   across grains, per the M2 instructions).
3. **`salesmonthly.csv` is NOT used as a source of truth for monthly
   figures.** It is loaded into a staging table for audit/reference only,
   explicitly flagged as unreconciled, and excluded from the canonical
   model. Monthly analytics are instead computed as a rollup of the
   canonical hourly-derived fact table, which is provably consistent with
   the finer grains.
4. All three non-hourly staging tables (`stg_sales_daily`,
   `stg_sales_weekly`, `stg_sales_monthly`) are still loaded in full — per
   the immutable-raw-files / staging-layer principle — so the
   reconciliation checks above are re-runnable as an automated data
   quality check on every pipeline run, not a one-time finding.

See [docs/data-model.md](data-model.md) for the resulting schema and
[docs/etl.md](etl.md) for how these checks are implemented as reusable
validation steps.
