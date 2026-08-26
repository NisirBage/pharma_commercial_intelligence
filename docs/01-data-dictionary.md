# Data Dictionary — Source Dataset (Ground Truth)

Source: `kagglehub.dataset_download("milanzdravkovic/pharma-sales-data")`, version 1.
Downloaded 2026-08-27, no Kaggle API credentials were required (public dataset).
Regenerate this document from `scripts/inspect_schema.py` if the upstream dataset
changes — do not hand-edit assumptions into it.

The dataset ships as **4 flat CSV files**, no relational structure, no keys,
no metadata/README from the source. There is no `products`, `customers`,
`HCPs`, `territories`, `sales representatives`, `revenue`, `geography`, or
`prescriptions` table of any kind in the source data.

## Files

| File | Rows | Grain | Date range |
|---|---|---|---|
| `saleshourly.csv` | 50,532 | 1 row per hour, business hours only (08:00–19:00) | 2014-01-02 08:00 → 2019-10-08 19:00 |
| `salesdaily.csv` | 2,106 | 1 row per day | 2014-01-02 → 2019-10-08 |
| `salesweekly.csv` | 302 | 1 row per ISO week (week-ending date) | 2014-01-05 → 2019-10-13 |
| `salesmonthly.csv` | 70 | 1 row per calendar month (month-end date) | 2014-01-31 → 2019-10-31 |

All four files are **pre-aggregated views of the same underlying transactions**
at different time granularities — not four independent datasets. There is
no row-level (single-transaction) data anywhere in the source.

## Columns

| Column | Type | Present in | Meaning |
|---|---|---|---|
| `datum` | string (date, format varies by file — see below) | all | Period start/end timestamp for that row |
| `M01AB` … `R06` (8 columns) | float | all | Units sold in that period, for that ATC drug class (see below). Values are fractional (e.g. `44.3`), consistent with these being **aggregated/summed quantities**, not integer transaction counts. |
| `Year` | int | daily, hourly | Calendar year, redundant with `datum` |
| `Month` | int | daily, hourly | Calendar month, redundant with `datum` |
| `Hour` | int | daily, hourly | **Inconsistent meaning across files — see Data Quality Findings below** |
| `Weekday Name` | string | daily, hourly | Day-of-week name, redundant with `datum` |

`datum` format differs by file and is **not uniformly parseable with a single
pandas format string**: `salesdaily`/`salesweekly` use `M/D/YYYY`,
`saleshourly` uses `M/D/YYYY H:MM`, `salesmonthly` uses `YYYY-MM-DD`. Any ETL
step must handle this explicitly per file rather than assuming one format.

## The 8 product columns are ATC drug classes, not products, brands, or SKUs

Each of the 8 numeric columns is a **WHO ATC (Anatomical Therapeutic
Chemical) classification code**, a standard international drug-classification
system. This mapping is **external domain reference knowledge, not present
anywhere in the source data** — the dataset itself does not define these
codes, so this table should be treated as an annotation, not a verified fact
about the dataset:

| Code | ATC class (WHO reference) | Common use |
|---|---|---|
| M01AB | Antiinflammatory/antirheumatic, non-steroid — acetic acid derivatives | NSAIDs (e.g. diclofenac-type) |
| M01AE | Antiinflammatory/antirheumatic, non-steroid — propionic acid derivatives | NSAIDs (e.g. ibuprofen-type) |
| N02BA | Other analgesics/antipyretics — salicylic acid derivatives | Aspirin-type |
| N02BE | Other analgesics/antipyretics — anilides | Paracetamol/acetaminophen-type |
| N05B | Psycholeptics — anxiolytics | Anti-anxiety |
| N05C | Psycholeptics — hypnotics and sedatives | Sleep aids |
| R03 | Drugs for obstructive airway disease | Asthma/COPD (bronchodilators etc.) |
| R06 | Antihistamines for systemic use | Allergy medication |

There is **no brand name, manufacturer, price, cost, or margin** for any of
these classes — "product" in this dataset means "ATC therapeutic class," a
much coarser unit than a real pharma commercial team would use.

## Data Quality Findings

1. **`Hour` column is inconsistent across files and its daily-file meaning is
   unexplained.** In `saleshourly.csv` it correctly ranges 0–23 (hour of
   day). In `salesdaily.csv` it only takes 3 distinct values (`190`, `248`,
   `276`) — not a valid hour-of-day range. This looks like a leftover/derived
   feature from the original research pipeline (possibly a daily transaction
   or opening-hours-minutes count) that was not documented. **Decision:
   treat this column as unexplained; do not use it in any daily-grain
   analysis, and do not guess at its meaning in downstream docs.**
2. **No missing values** in any file (all null counts are 0) — but "0.0" is
   used for periods with no recorded sales, which is indistinguishable from
   "not measured." Given the data is a full continuous daily series with no
   gaps, 0.0 is treated as a genuine zero-sales observation.
3. **No entity keys of any kind** — no store ID, region, pharmacy ID, or
   country field. This is (presumably, based on the dataset's known origin
   as academic time-series-forecasting research data) a **single
   pharmacy/aggregation point**, not a multi-site retail network. This
   cannot be confirmed from the data itself since no site identifier exists
   at all — there is exactly one, implicit series per ATC class.
4. **No revenue, price, cost, or margin data anywhere.** All 8 numeric
   columns are unit/volume quantities.
5. **Hourly file only covers business hours (08:00–19:00)** — hours outside
   that range are simply absent rows, not zeros.

## What this means for the stated project scope

See [00-business-problem.md](00-business-problem.md) for the full
reframing — in short, the source data supports **demand forecasting,
seasonality/trend analysis, and category-level opportunity detection**, but
**not** territory optimization, HCP targeting, sales-rep routing, or any
revenue-based analysis, because no territory, HCP, rep, geography, or
revenue field exists anywhere in the source. Any such capability would
require clearly-labelled synthetic data layered on top (see that doc for the
recommended approach).
