# Forecasting Methodology

Implementation: `backend/app/forecasting/`. Every number in this document
comes from `backend/scripts/run_m4_backtest.py`'s actual run against the
full real dataset (404,256 canonical hourly observations) — reproducible
by re-running that script.

## 1. Problem definition

**Target:** Observed demand volume (`units_sold`) — never revenue, profit,
or prescription count; the dataset doesn't contain those (see
[01-data-dictionary.md](01-data-dictionary.md)).

**Forecast entity: both, verified empirically.** M3 found substantial
divergence between ATC classes (R03 growing, N02BA/N05B declining, the
rest flat), which motivated forecasting per class rather than only in
aggregate. This project builds **9 independent series** — 1 per ATC class
plus 1 aggregate ("ALL", the sum across all 8 classes) — and evaluates
both. **The result is genuinely mixed, not a clean win for per-class** —
see Section 9/[forecasting-insights.md](forecasting-insights.md) for the
actual comparison, which found the direct aggregate forecast **more**
accurate than summing the 8 per-class forecasts on the final test window.
Both are kept: per-class forecasts remain necessary for any per-drug
operational decision (you cannot reorder "demand" in the abstract), but
the aggregate forecast is the more accurate choice if the actual business
question is about total volume.

**Forecast grain: daily.** Hourly is too sparse/operating-hours-gated for
a planning target (M3 found near-zero demand for hours 0-7); weekly/
monthly lose the responsiveness a supply planner needs and monthly in
particular must never be sourced from `salesmonthly.csv` (M2 Decision 2)
— though a *derived* monthly rollup from the canonical hourly frame would
be technically possible, daily was judged the right primary grain given
the (weak, per M3: strength 0.234) weekly seasonality and the need for a
forecast horizon shorter than a month for practical reordering decisions.

**Forecast horizon: 14 days.** Long enough to cover a full weekly cycle
twice (relevant given the day-of-week effect M3 found, p=0.00023) and to
be operationally useful for a reorder-cycle-length planning horizon;
short enough that daily-grain volatility (M3: per-class CV ranging
0.52–1.84) doesn't compound into an unusably wide forecast the way a
30-day horizon risked doing. The horizon-step error diagnostics in
Section 12/[forecasting-insights.md](forecasting-insights.md) test this
choice directly rather than asserting it.

**Forecast frequency: daily regeneration**, matching the grain — a new
14-day-ahead forecast is produced from the latest available day of
history, exactly as modeled by the rolling-origin backtesting scheme
below (each fold origin is a stand-in for "today").

## 2. Leakage prevention

Full audit: [forecasting-leakage-audit.md](forecasting-leakage-audit.md).
Summary of the mechanisms:

- **No random splitting anywhere** — every split is chronological
  (`app/forecasting/backtesting.generate_folds`).
- **Every lag/rolling feature is shift-then-roll**
  (`app/forecasting/features.py`) — verified by an executable regression
  test that mutates future values and asserts earlier feature rows are
  byte-for-byte unchanged.
- **Recursive ML forecasting never sees real future values** — each
  step's own forecast (not the true value, which isn't available) is fed
  back in to compute the next step's features
  (`app/forecasting/ml_models._recursive_forecast`).
- **Hyperparameters and feature/lag choices were fixed up front**, never
  tuned against validation or test results (see
  [model-selection.md](model-selection.md)).
- **The final test window is touched exactly once**, after model
  selection is already complete, purely to report honest out-of-sample
  performance.

## 3. Backtesting design

**Rolling-origin (expanding window), 6 folds, horizon=14 days,
min_train_days=180.** Training windows always start at the series'
beginning (2014-01-02) and grow forward; each fold's validation window is
the 14 days immediately after that fold's training cutoff — never
overlapping, never touching data the model has seen.

**Exact fold dates used** (identical across every series, since all 9
share the same date range):

| Fold | Train end (inclusive) | Validation window |
|---|---|---|
| 1 | 2014-06-30 | 2014-07-01 → 2014-07-14 |
| 2 | 2015-07-15 | 2015-07-16 → 2015-07-29 |
| 3 | 2016-07-28 | 2016-07-29 → 2016-08-11 |
| 4 | 2017-08-12 | 2017-08-13 → 2017-08-26 |
| 5 | 2018-08-26 | 2018-08-27 → 2018-09-09 |
| 6 | 2019-09-10 | 2019-09-11 → 2019-09-24 |

**Final held-out TEST window (separate from all 6 folds above):
2019-09-25 → 2019-10-08** — the dataset's true last 14 days. Used exactly
once per ATC class, after the model-selection policy has already picked a
winner from the 6 validation folds, purely to report an honest
out-of-sample number. No model choice, hyperparameter, or feature was
ever adjusted based on this window.

**Why 180-day minimum training / 6 folds:** 180 days gives roughly 6
months of warm-up — comfortably past the 28-day feature warm-up
(Section 6) and enough history for ETS to identify a weekly seasonal
component (which needs ≥ 2 full cycles, i.e. ≥ 14 days, with a wide
margin). 6 folds, spread roughly a year apart across 2014–2019, means
every backtest touches a different season/year of the business rather
than clustering around one period.

**No gap between train and validation** — a fold's validation window
starts the day immediately after training ends, matching how a real
day-ahead forecast would actually be produced (no artificial embargo
period was judged necessary here, since no feature uses information from
"today" that wouldn't genuinely be available at prediction time).

## 4. Baseline models (mandatory, per M4 Sec. 4)

| Baseline | Formula | Rationale |
|---|---|---|
| `naive` | `forecast(t+h) = demand(t)` for every h | The mandatory floor every other model must beat. |
| `seasonal_naive_7` | `forecast(t+h) = demand(t+h-7)` | Weekly period — M3 found a significant (if modest) day-of-week effect at daily grain. |
| `moving_average_14` | `forecast(t+h) = mean(last 14 observed days)` for every h | Window matches the chosen forecast horizon — long enough to smooth day-to-day noise, short enough to not average in demand from over 2 weeks ago (justified against M3's weak 0.234 weekly-seasonality-strength finding, i.e. there's limited value in a much longer window). |

## 5. Candidate models

| Candidate | Why included |
|---|---|
| **Linear Regression** (lag/rolling/calendar features) | Simplest genuine ML step up from the baselines — a natural "Model A" to test whether a linear combination of recent history + calendar signal beats flat baselines at all. |
| **Random Forest** (same features) | Captures nonlinearity/interactions the linear model can't (e.g. a different day-of-week effect depending on the recent trend level) without heavy tuning. |
| **ETS / Holt-Winters** (statsmodels `ETSModel`, additive trend+seasonal, period=7) | Directly models trend + seasonality — matching M3's confirmed findings — without SARIMA's heavier `(p,d,q)×(P,D,Q)` order-search, which is materially more expensive to run honestly (a real grid search, not a single guessed order) across 9 series × 6 folds and harder to justify at this project's scope. |

**XGBoost was explicitly considered and NOT included.** Random Forest
already tests whether a nonlinear tree-ensemble beats linear regression
at this data scale (~2,000 rows/class); there's no evidence at this scale
that XGBoost's more complex boosting/regularization would materially
outperform `RandomForestRegressor`, and adding a new heavy dependency for
an unproven, marginal benefit would be overengineering (per this
project's own architectural principles). **SARIMA was considered and not
included** for the compute-cost/justification reason above — ETS covers
the same trend+seasonality ground more cheaply and interpretably.

## 6. Feature engineering (ML candidates only)

| Feature | Formula | Reasoning |
|---|---|---|
| `lag_1`, `lag_7`, `lag_14`, `lag_28` | `units_sold.shift(lag)` | 1-day (yesterday), 1-week, 2-week, 4-week — cover the daily/weekly/monthly-ish cycles a supply planner would naturally reference. |
| `rolling_mean/median/std/min/max_{7,14,28}` | `units_sold.shift(1).rolling(w).<stat>()` | Same 3 windows, each summarized 5 ways — gives the model both a central-tendency and a spread signal at each horizon, always excluding the current/target day. |
| `day_of_week`, `is_weekend` | From the date | Matches M3's confirmed day-of-week effect. |
| `day_of_month`, `month`, `week_of_year` | From the date | Candidate signals for the moderate-to-strong annual seasonality M3 found (strength 0.553) — calendar position is a cheap proxy a tree model can exploit even without an explicit annual Fourier term. |

**Multi-step strategy: recursive, not direct-multi-horizon.** One model
per series is trained to predict 1 day ahead; the 14-day forecast is
produced by feeding each step's own prediction back in as if it were
real, to compute the next step's lag/rolling features
(`app/forecasting/ml_models._recursive_forecast`). This keeps the model
count bounded (1 model/series/candidate, not 14), at the cost of
potential error compounding across the horizon — measured directly in
[forecasting-insights.md](forecasting-insights.md)'s horizon-step
diagnostics (which, empirically, did not show a clean compounding
pattern for the models actually selected — see that document).

Hyperparameters were **fixed, not tuned**: Random Forest
(`n_estimators=200, max_depth=8, random_state=42`), Linear Regression
(scikit-learn defaults). No grid search was run against any fold or the
test window — see [model-selection.md](model-selection.md) for why.

## 7. Metrics

**MAE and RMSE** are the primary metrics (both reported per fold and
averaged). **WAPE** (`sum(|actual-pred|) / sum(|actual|) * 100`) is the
metric the model-selection policy actually keys off, because it's
comparable across ATC classes of very different volume. **MASE**
(`MAE(forecast) / MAE(in-sample naive)`, scaled from the training period
only) is also reported as a cross-check.

**Plain MAPE was deliberately not used.** Daily per-ATC demand contains
genuine zero-demand days — M1/M3 found the dataset-wide daily minimum is
exactly 0.0, and low-volume classes (N05C, ~1% of total demand) have many
zero days — which makes point-wise percentage error undefined/infinite
for a real fraction of observations. WAPE, a ratio of sums rather than of
individual points, does not have this problem.

## 8-9. Model comparison and per-ATC results

See [model-selection.md](model-selection.md) for the full comparison
table (every model × every ATC class, validation-fold WAPE) and the
selected model per class with its test-holdout performance.

## 10-14 (selection, uncertainty, diagnostics, visualization, business interpretation)

See [model-selection.md](model-selection.md) and
[forecasting-insights.md](forecasting-insights.md).

## 15. Model registry

`backend/app/forecasting/registry.py` — one JSON file per selected model
under `backend/data/model_registry/` (gitignored, regenerable), recording
model name, ATC class, training/validation period, horizon, features,
hyperparameters, evaluation metrics, a training timestamp, and a
`dataset_version_hash` (a SHA-256 of each raw file's row count, columns,
and first/last row — a reproducible proxy for "dataset version" since the
Kaggle dataset itself has no formal version field). No MLflow — a
file-per-model registry is sufficient at this scale and is trivially
diffable in version control.

## 16. Reproducibility

```
python scripts/download_data.py          # from the project root
cd backend && pip install -r requirements.txt
python scripts/run_m4_backtest.py         # reproduces every number in this document
pytest                                    # 144 tests, all against synthetic/fixture data (no live DB needed)
```

Random seeds are fixed (`RANDOM_SEED = 42` in `app/forecasting/ml_models.py`)
so Random Forest results are deterministic across runs — verified in
`tests/unit/forecasting/test_ml_models.py::test_random_forest_forecaster_is_deterministic_with_fixed_seed`.

## 19. API preparation

`app/forecasting/predictions.ForecastOutput` is the exact shape a future
`GET /api/v1/forecast/{atc_class}` endpoint would serialize:

```json
{
  "atc_class": "N02BE",
  "forecast_grain": "daily",
  "horizon": 14,
  "model": "moving_average_14",
  "predictions": [{"date": "2019-10-09", "point_forecast": 64.7, "lower_bound": 35.0, "upper_bound": 94.4}, ...],
  "uncertainty_method": "residual_based_backtest_quantile",
  "evaluation": {"mae": 8.44, "rmse": 11.07, "wape": 33.71, "mase": 0.74}
}
```

## Performance notes: current scale vs. future scale

Full 9-series × 6-model × 6-fold backtest runtime: **170.8s** (~2.8 min)
on ~50K hourly / ~2,100 daily observations per class. Random Forest
dominates the runtime (~13-14s per series for 6 folds; everything else
combined is a few seconds per series). This is fine at the current scale;
it would **not** be at a materially larger one. If this grew from ~2,000
daily rows/class to millions of rows or many more classes/entities:

- **Database-side feature generation**: lag/rolling features should move
  to Postgres window functions (`LAG()`, `AVG() OVER (... ROWS BETWEEN
  ...)`) rather than pandas, avoiding a full-table pull per backtest run.
- **Materialized feature tables**: recomputing all lag/rolling features
  from scratch on every fold (as this implementation does) doesn't scale;
  a materialized, incrementally-updated feature table would let each
  fold just slice a date range instead of recomputing.
- **Incremental forecasting / retraining schedule**: today, every run
  retrains from scratch. At scale, only the newest data's features need
  computing incrementally, and models should be retrained on an explicit
  schedule (e.g. weekly) rather than on every forecast request.
- **Batch prediction**: generating one forecast per ATC class in a loop
  (as this implementation does) is fine at 8 classes; at hundreds/
  thousands of entities this should batch across entities within one
  model-fitting pass where the model type supports it (Random Forest
  already does with a multi-output target; ETS, being per-series, would
  need to be parallelized across entities instead).
- **Model artifact storage**: currently only metadata is persisted
  (`app/forecasting/registry.py`); at scale, fitted model objects
  themselves (not just their metrics) would need a proper artifact store
  rather than being refit on every use.
- **Partitioning**: `fact_demand_hourly` (M2) is already indexed on
  `(atc_code, observation_ts)` — a much larger table would additionally
  want time-based partitioning so a single class's backtest doesn't scan
  the whole table.

None of this is implemented now — correctness and maintainability at the
current (small) scale take priority, per this project's stated
principles and the M4 instructions.
