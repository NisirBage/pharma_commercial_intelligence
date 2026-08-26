# Analytics Methodology

Every analytical function lives in `backend/app/analytics/` and operates on
the **canonical hourly frame** (columns: `atc_code`, `observation_ts`,
`units_sold`, `year`, `month`, `hour_of_day`, `weekday_name`) — the same
shape as `fact_demand_hourly` from M2. See
[app/analytics/data_access.py](../backend/app/analytics/data_access.py)
for how it's loaded (from Postgres when available; from the raw CSVs via
the exact M2 transform functions otherwise — no independent data path).

## Cross-cutting principles

- **Grain discipline.** Every function that needs a daily/weekly/monthly
  figure gets it from `app/analytics/aggregate.py` — one rollup path,
  matching the M2 SQL views (`vw_demand_daily/weekly/monthly`). Nothing
  computes its own ad hoc groupby. Monthly figures are **always** derived
  from the hourly fact table, never from `salesmonthly.csv` (see M2
  Decision 2 — that file does not reconcile).
- **No future leakage.** Every rolling/baseline calculation (volatility,
  anomaly detection) uses `.shift(1)` before windowing, so a day's
  baseline never includes that day itself, let alone future days.
- **Statistically defensible, not eyeballed.** Trend, seasonality, and
  change-point claims all carry a formal test statistic and p-value.
  "Looks cyclical" is never treated as evidence on its own.
- **Terminology.** Every number is an observed **sales/demand volume**
  (units sold). Never revenue, profit, market share, or prescription
  volume — the dataset contains none of those (see
  [01-data-dictionary.md](01-data-dictionary.md)).
- **Structured output.** Every function returns `MetricResult` or
  `AnomalyResult` (`app/analytics/types.py`) — `{metric, value, period,
  entity, grain, metadata}` — so a future API can serialize results
  directly without re-deriving business logic.

## Grain reference

| Grain | Meaning | Source |
|---|---|---|
| `hourly` | Raw canonical observations, one row per (ATC class, hour) | `fact_demand_hourly` / `saleshourly.csv` |
| `daily` | Summed per (ATC class, calendar date) | Rolled up from hourly |
| `weekly` | Summed per (ATC class, Sunday-ending week) | Rolled up from hourly |
| `monthly` | Summed per (ATC class, calendar month) | Rolled up from hourly — **never** `salesmonthly.csv` |

---

## 1. Executive KPI layer (`app/analytics/kpis.py`)

### total_demand
1. **Business question:** How much total volume was sold, overall or for one ATC class?
2. **Definition:** Sum of all observed units sold in the requested scope.
3. **Formula:** `SUM(units_sold)`
4. **Data source:** Canonical hourly frame (any grain — see note below).
5. **Grain:** Grain-invariant by construction; `grain` param is recorded for context only.
6. **Aggregation:** None needed — summation commutes across rollups (tested in `tests/unit/analytics/test_kpis.py::test_total_demand_is_grain_invariant`).
7. **Interpretation:** The single top-line demand number for the observed history.
8. **Limitations:** Says nothing about distribution over time — see average/peak/min below.

### average_demand / median_demand
1. **Business question:** What's typical demand per period?
2. **Definition:** Central tendency of period totals.
3. **Formula:** `MEAN`/`MEDIAN(period totals)`.
4. **Data source:** Rolled-up canonical frame at the requested grain.
5. **Grain:** Caller-specified (default `hourly`).
6. **Aggregation:** Via `app/analytics/aggregate.py`.
7. **Interpretation:** Median is preferred when a metric needs to be robust to a small number of extreme days (see peak_demand); mean is preferred for planning totals.
8. **Limitations:** Neither describes spread — see the volatility section.

### peak_demand / min_demand
1. **Business question:** What was the single highest/lowest-demand period — relevant to capacity and stockout-risk planning?
2. **Definition:** Max/min of period totals, with the period itself recorded.
3. **Formula:** `MAX`/`MIN(period totals)`; `metadata.peak_period`/`min_period` records when.
4. **Data source:** Rolled-up canonical frame.
5. **Grain:** Caller-specified.
6. **Aggregation:** Via `app/analytics/aggregate.py`.
7. **Interpretation:** A single extreme period — not evidence of a repeating pattern (see anomaly detection for that).
8. **Limitations:** One extreme value can be a data artifact as easily as a real event; always cross-check against the anomaly-detection output before acting on it.

### period_over_period_growth
1. **Business question:** Is demand growing or shrinking, period to period?
2. **Definition:** Percent change between the latest period and the one `periods_back` before it.
3. **Formula:** `(latest - previous) / previous * 100`
4. **Data source:** Rolled-up canonical frame.
5. **Grain:** Caller-specified (default `monthly`).
6. **Aggregation:** Via `app/analytics/aggregate.py`.
7. **Interpretation:** A single-point growth read — noisy at short grains, more stable at monthly.
8. **Limitations:** Undefined (returned as `None`, never `inf`/`NaN`) when the previous period is exactly 0, or there's insufficient history. **Also: the most recent period in this dataset is a partial month (data ends 2019-10-08) — a period-over-period comparison touching it will look like a steep decline that is actually a partial-month artifact.** See [business-insights.md](business-insights.md).

### contribution_by_atc
1. **Business question:** Which ATC classes drive total observed demand?
2. **Definition:** Each class's share of total observed volume.
3. **Formula:** `class_total / grand_total * 100`, ranked descending.
4. **Data source:** Canonical hourly frame, full history.
5. **Grain:** `overall` (not period-specific).
6. **Aggregation:** `groupby(atc_code)`.
7. **Interpretation:** Demand contribution **within this dataset** — not market share (no broader-market data exists).
8. **Limitations:** A static, whole-history share; doesn't show whether contribution is shifting over time (see per-class trend in Section 3).

---

## 2. Temporal analysis (`app/analytics/trends.py`)

### linear_trend
1. **Business question:** Is there a statistically defensible long-term trend, or none detectable?
2. **Definition:** OLS slope of monthly total demand against a monthly time index.
3. **Formula:** `scipy.stats.linregress(x=month_index, y=monthly_total)`; classified `growing`/`declining` only if `p < 0.05` **and** the slope has the matching sign, else `stable_or_no_significant_trend`.
4. **Data source:** Monthly rollup of the canonical hourly frame.
5. **Grain:** `monthly`.
6. **Aggregation:** `app/analytics/aggregate.to_monthly`.
7. **Interpretation:** A defensible growth/decline call — never asserted from slope sign alone.
8. **Limitations:** Assumes a roughly linear relationship; under-describes a series with curvature or a genuine regime change (see Section 6, structural-change detection, for that). Requires ≥ 3 monthly periods.

### yearly_totals (+ YoY)
1. **Business question:** Which years had more/less total demand, and by how much?
2. **Definition:** Calendar-year totals with year-over-year percent change.
3. **Formula:** `SUM(units_sold)` per year; `YoY = (year_total - prior_year_total) / prior_year_total * 100`.
4. **Data source:** Canonical hourly frame.
5. **Grain:** `yearly`.
6. **Aggregation:** `groupby(observation_ts.dt.year)`.
7. **Interpretation:** Coarse, easy-to-communicate year-level movement.
8. **Limitations:** **The first (2014) and last (2019) calendar years in this dataset are partial** (`is_complete_year` flags this explicitly — see [business-insights.md](business-insights.md)). A YoY figure touching either is not a full-year comparison.

---

## 3. Seasonality (`app/analytics/seasonality.py`)

### day_of_week_effect / hour_of_day_effect
1. **Business question:** Does demand vary systematically by weekday / by hour of day?
2. **Definition:** Non-parametric test for whether group medians differ across weekdays / hours.
3. **Formula:** Kruskal-Wallis H-test (`scipy.stats.kruskal`) across the 7 weekday groups / 24 hour groups.
4. **Data source:** Daily rollup (weekday) or raw hourly observations (hour-of-day).
5. **Grain:** `daily` / `hourly`.
6. **Aggregation:** `groupby(weekday)` / `groupby(hour_of_day)`.
7. **Interpretation:** `significant=True` (p < 0.05) means the groups are not drawn from the same distribution — a real, not chance, pattern.
8. **Limitations:** Kruskal-Wallis says groups differ, not by how much or in what direction — `mean_units_by_weekday`/`mean_units_by_hour` in `metadata` supply that. **`hour_of_day` is always sourced from `saleshourly.csv`'s real hour column — never `salesdaily.csv`'s `Hour` artifact (M2 Decision 1).**

### seasonal_strength
1. **Business question:** Is there real, decomposable seasonality at a given cycle length, or does a cyclical-looking chart not hold up statistically?
2. **Definition:** STL-decomposition-based seasonality strength (Hyndman & Athanasopoulos).
3. **Formula:** `max(0, 1 - Var(residual) / Var(seasonal + residual))` after `statsmodels.tsa.seasonal.STL` decomposition.
4. **Data source:** Daily or monthly rollup.
5. **Grain:** `daily` (weekly cycle, `period=7`) or `monthly` (annual cycle, `period=12`).
6. **Aggregation:** Via `app/analytics/aggregate.py`, then STL.
7. **Interpretation:** 0 = no seasonal pattern; close to 1 = strong, regular seasonality.
8. **Limitations:** Requires ≥ 2 full cycles of history to fit at all (`insufficient_periods` otherwise); STL assumes a roughly consistent seasonal shape over time.

---

## 4. ATC class analysis & concentration (`app/analytics/atc_analysis.py`)

### build_atc_profiles / classify_by_trend / rank_by_contribution
1. **Business question:** Which classes are dominant, growing, declining, or stable — and by what evidence?
2. **Definition:** Per-class bundle of the KPI/trend/volatility metrics above.
3. **Formula:** Composition of `kpis`, `trends.linear_trend`, `volatility.coefficient_of_variation` — no new math.
4. **Data source:** Canonical hourly frame, filtered per class.
5. **Grain:** `daily` for the KPI components, `monthly` for trend.
6. **Aggregation:** Per-class.
7. **Interpretation:** `classify_by_trend` buckets classes **only** using `linear_trend`'s already-significance-tested classification — never a subjective read of a chart.
8. **Limitations:** A class's trend classification can be sensitive to the exact history window; re-running against an updated dataset can move a class between buckets.

### demand_concentration
1. **Business question:** Is demand concentrated among a few ATC classes, or spread evenly across all 8?
2. **Definition:** Share/cumulative-share ranking, CR3 (top-3 concentration ratio), and HHI.
3. **Formula:** `share_pct` per class; `CR3 = sum(top 3 shares)`; `HHI = sum(share_i_in_percent^2)` (0–10000 scale).
4. **Data source:** `kpis.contribution_by_atc`.
5. **Grain:** `overall`.
6. **Aggregation:** Ranking + cumulative sum.
7. **Interpretation:** This is concentration **within this dataset's 8 observed ATC classes** — not market concentration (no broader-market data exists). Competition-economics HHI reference bands (<1500/1500–2500/>2500) are cited only to give the number scale.
8. **Limitations:** With only 8 classes, HHI's theoretical minimum (perfectly even split) is 1250, not 0 — the usual "near-0 = unconcentrated" intuition doesn't directly transfer to an 8-category split.

---

## 5. Volatility (`app/analytics/volatility.py`)

### coefficient_of_variation (primary cross-class metric)
1. **Business question:** How variable is a class's demand relative to its own average — comparable across classes of very different volume?
2. **Definition:** Scale-free dispersion measure.
3. **Formula:** `CV = std(period totals) / mean(period totals)`.
4. **Data source:** Daily (default) or hourly rollup.
5. **Grain:** `daily` / `hourly`.
6. **Aggregation:** Via `app/analytics/aggregate.py`.
7. **Interpretation:** Higher CV = more volatile relative to its own scale. Used for `rank_by_volatility`.
8. **Limitations:** Undefined at `mean == 0` (reported via `metadata.reason`, never `inf`). Low-volume classes with many near-zero days mechanically show higher CV — documented, not hidden.

### rolling_std / interquartile_range
1. **Business question:** How has volatility changed over time (rolling_std)? What's the outlier-robust spread (IQR)?
2. **Definition:** Trailing rolling standard deviation; interquartile range of period totals.
3. **Formula:** `rolling(window_days).std()`; `Q3 - Q1`.
4. **Data source:** Daily rollup.
5. **Grain:** `daily`.
6. **Aggregation:** Rolling window / quantiles.
7. **Interpretation:** `rolling_std` is the direct input to anomaly detection (Section 6), not a standalone KPI. IQR is a stable "typical spread" that ignores extreme tails entirely.
8. **Limitations:** `rolling_std` needs `window_days` of history before producing a value (`NaN` before that). IQR requires ≥ 4 periods.

---

## 6. Anomaly detection (`app/analytics/anomalies.py`)

### detect_rolling_zscore (Method A/B) / detect_iqr (Method C)
1. **Business question:** Which specific days deviated unusually from a class's own recent history?
2. **Definition:** Two independent, transparent statistical outlier flags.
3. **Formula:**
   - Rolling z-score: `z = (observed - rolling_mean) / rolling_std`, both computed from a **30-day trailing window of strictly prior days** (`.shift(1)` before `.rolling()` — no future leakage). Flagged at `|z| >= 2.0`; `severity="high"` at `|z| >= 3.0`.
   - IQR (Tukey fence): flagged outside `[Q1 - 1.5·IQR, Q3 + 1.5·IQR]` computed over the same trailing 30-day window.
4. **Data source:** Daily rollup, per ATC class.
5. **Grain:** `daily`.
6. **Aggregation:** Per-class, per-day.
7. **Interpretation:** An anomaly is reported as **exactly** an observed statistical deviation from recent history — timestamp, class, observed value, expected baseline, deviation %, score, direction, severity. **Never** labeled with a business cause (supply disruption, campaign, epidemic, launch) — the dataset has no corroborating evidence for any of those. See [business-insights.md](business-insights.md) for how findings here feed the Observed/Analytical/Hypothesis framing.
8. **Limitations:** Needs ≥ 31 days of history before the first day can be evaluated. **A zero-variance baseline (a perfectly flat run of prior days) cannot produce a z-score or a non-zero IQR — such deviations go undetected by design**, a documented, tested limitation (`tests/unit/analytics/test_anomalies.py`), not a silent gap. Isolation Forest / other ML deliberately not used — M3 calls for a transparent baseline first.

### detect_mean_shift (structural / change-point screening)
1. **Business question:** Did the overall level of demand shift at some point (a structural change), as distinct from a continuous trend or a short anomaly?
2. **Definition:** Candidate change-point screen via grid-searched two-sample comparison.
3. **Formula:** For every candidate split point in the monthly (or daily) series, Welch's t-test between the "before" and "after" segments; report the split with the largest `|t|`.
4. **Data source:** Monthly (default) or daily rollup.
5. **Grain:** `monthly` / `daily`.
6. **Aggregation:** Grid search over split points.
7. **Interpretation:** Identifies **where** a series' mean level differs before vs. after a candidate date. Does **not** identify why — see [business-insights.md](business-insights.md).
8. **Limitations:** Grid-searching many splits and reporting only the best is a **multiple-comparisons problem** — the reported p-value is **not corrected** and should be read as indicative screening, not a rigorous hypothesis test. Requires ≥ 6 periods (3 per segment minimum).

---

## 7. Cross-granularity reconciliation (`app/analytics/reconciliation.py`)

1. **Business question:** Can the current analytical outputs be trusted, or is a source file known to be unreliable?
2. **Definition:** Re-runs M2's proven reconciliation checks (`app.etl.validate.check_cross_grain_reconciliation`) as an ongoing analytical QC signal, formatted for direct display.
3. **Formula:** Cell-by-cell comparison of the raw daily/weekly/monthly files against sums of the finer grain (see [data-quality-decisions.md](data-quality-decisions.md)).
4. **Data source:** Raw CSVs (all 4 files).
5. **Grain:** Cross-grain by definition.
6. **Aggregation:** N/A (comparison, not aggregation).
7. **Interpretation:** `Daily: Reconciled ✓`, `Weekly: Reconciled ✓`, `Monthly: Source inconsistency detected ⚠` — exactly the M2 finding, re-verified.
8. **Limitations:** Confirms the *known* monthly issue is still present and unchanged; it does not detect *new* kinds of inconsistency the checks weren't designed for.

---

## Performance notes (current scale vs. future scale)

At ~50K hourly observations, every function above runs in-process on a
pandas DataFrame in well under a second (the one exception,
`detect_anomalies` across all 8 classes with both methods, runs in a few
seconds — grid-searching `detect_mean_shift` similarly). This is
appropriate for the current dataset size; it would **not** be appropriate
unchanged at a materially larger scale. If this dataset grew from ~50K
hourly rows to millions/billions:

- **Rolling/window computations** (volatility, anomaly detection) should
  move from in-process pandas `.rolling()` to **database-side window
  functions** (Postgres `OVER (PARTITION BY atc_code ORDER BY
  observation_ts ROWS BETWEEN ...)`), avoiding a full table pull per run.
- **Grain rollups** (`aggregate.py`) should become **materialized views**
  (or the M2 SQL views refreshed incrementally) rather than recomputed
  from the hourly grain on every call.
- **`detect_mean_shift`'s grid search** is O(n) t-tests over n candidate
  splits — fine at 70 months, would need a smarter algorithm (e.g. binary
  segmentation) at a much finer grain over a much longer history.
- **Indexes**: `fact_demand_hourly(atc_code, observation_ts)` (already
  created in the M2 migration) is the right index for all of the above;
  a much larger table would also want **partitioning by time** (e.g.
  monthly partitions) so window/rollup queries only scan relevant
  partitions.
- **Incremental computation**: today, every run recomputes over the full
  history. At scale, rolling baselines and rollups should be computed
  incrementally (append-only) rather than recomputed from scratch.

None of this is implemented now — correctness and maintainability at the
current (small) scale take priority, per the M3 instructions.
