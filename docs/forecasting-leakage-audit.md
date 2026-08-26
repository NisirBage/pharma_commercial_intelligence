# Forecasting Leakage Audit

Every feature the ML forecasting candidates (`app/forecasting/ml_models.py`)
use, and how leakage was prevented for each. This is meant to let a
reviewer verify, feature by feature, that nothing from the future ever
reaches a prediction for the past.

## Feature audit table

| Feature | Historical only? | Shift required? | Leakage risk | How it's prevented |
|---|---|---|---|---|
| `lag_1` | Yes — value from `t-1` | Yes, `.shift(1)` | Low, if shifted correctly | `add_lag_features` (`app/forecasting/features.py`) uses `df[target_col].shift(lag)` — pandas `.shift()` on a chronologically-sorted frame guarantees row `t` only ever sees row `t-lag`. |
| `lag_7` | Yes — value from `t-7` | Yes, `.shift(7)` | Low | Same mechanism as `lag_1`. |
| `lag_14` | Yes — value from `t-14` | Yes, `.shift(14)` | Low | Same mechanism. |
| `lag_28` | Yes — value from `t-28` | Yes, `.shift(28)` | Low | Same mechanism. |
| `rolling_mean_7`/`_14`/`_28` | Yes — mean over `[t-w, t-1]` | Yes — `.shift(1)` **before** `.rolling(w)` | **High if the shift is dropped** — `df[target_col].rolling(w).mean()` on its own would include row `t`'s own target in its own feature, the textbook rolling-feature leakage bug the M4 brief calls out explicitly. | `add_rolling_features` always computes `shifted = df[target_col].shift(1)` first, then rolls on `shifted` — see `tests/unit/forecasting/test_features.py::test_rolling_mean_is_shifted_and_excludes_current_day` and the explicit leakage regression test below. |
| `rolling_median_7`/`_14`/`_28` | Yes | Yes, same `.shift(1)`-first pattern | Same as rolling mean | Same code path — all five rolling stats (`mean`, `median`, `std`, `min`, `max`) are computed from the same pre-shifted series in one place. |
| `rolling_std_7`/`_14`/`_28` | Yes | Yes | Same | Same. |
| `rolling_min_7`/`_14`/`_28` | Yes | Yes | Same | Same. |
| `rolling_max_7`/`_14`/`_28` | Yes | Yes | Same | Same. |
| `day_of_week` | N/A — derived from the date itself | No | **None** — the date of a future forecast target is always known in advance; this is not leakage by definition. | `add_calendar_features` derives it from `observation_date`, never from `units_sold`. |
| `day_of_month` | N/A | No | None | Same reasoning. |
| `month` | N/A | No | None | Same reasoning. |
| `week_of_year` | N/A | No | None | Same reasoning. |
| `is_weekend` | N/A | No | None | Same reasoning. |

## Beyond individual features: leakage vectors checked at the pipeline level

| Vector | Status | How it's prevented |
|---|---|---|
| Random train/test splitting | **Not used anywhere** | All splitting is chronological (`app/forecasting/backtesting.generate_folds`) — training windows only ever expand forward in time; every fold's validation window starts the day immediately after its training window ends. |
| Future rolling statistics | **Not used** | Every rolling/lag feature is `.shift(1)`-first (see table above). |
| Future target values | **Not used** | The recursive multi-step forecast (`app/forecasting/ml_models._recursive_forecast`) only ever appends its OWN prior predictions to extend history forward — it never has access to a real future value at any step. |
| Future aggregates (e.g. computing a mean/std over the whole series, including future rows, before splitting) | **Not used** | All rolling/aggregate statistics are computed with pandas `.shift()`/`.rolling()` on the full chronological series (which naturally excludes any future info per-row by construction), never with a separately pre-computed whole-series statistic. |
| Future-derived normalization (e.g. scaling features using statistics from the full dataset, including the test period) | **Not applicable** | None of the models in this project use feature scaling/normalization (Random Forest and ETS don't need it; Linear Regression's raw lag/rolling/calendar features were used unscaled — see docs/forecasting-methodology.md for why this is an acceptable simplicity tradeoff at this stage). |
| Future-derived feature selection (e.g. picking which lags/windows to use based on performance on the test period) | **Not used** | The lag set `(1, 7, 14, 28)` and rolling windows `(7, 14, 28)` (`app/forecasting/features.py`) were chosen up front from domain reasoning (daily/weekly/monthly-ish cycles) and M3's seasonality findings — never tuned against backtest or test results. |
| Hyperparameter tuning on the final test period | **Not used** | Random Forest and Linear Regression hyperparameters (`n_estimators=200`, `max_depth=8`, no tuning for Linear Regression) are fixed constants, chosen from general defaults and dataset-size reasoning, never grid-searched against any fold's or the test window's results — see docs/model-selection.md. |
| Model reuse across folds | **Not used** | `app/forecasting/ml_models.make_ml_forecaster` takes an `estimator_factory`, constructing and fitting a brand-new, unfitted model instance for every single fold — a model is never fit once and reused/updated across folds. |
| The known-unreliable `salesmonthly.csv` used as a forecasting input | **Not used** | `app/forecasting/datasets.py` builds every series exclusively from the canonical hourly fact table (via `app.analytics.data_access`/`app.analytics.aggregate.to_daily`) — `salesmonthly.csv` is never read anywhere in the forecasting package. |

## Automated regression test

`tests/unit/forecasting/test_features.py::test_rolling_feature_unaffected_by_changing_the_current_or_future_row`
constructs a series, computes rolling features, then **mutates every value
from a chosen date onward** and recomputes the features. It asserts every
feature value strictly before that date is byte-for-byte unchanged, and
that the feature *at* that date is also unchanged (since it only ever
looks at the `window_days` values *before* it). This test would **fail**
if the `.shift(1)`-before-`.rolling()` ordering were ever accidentally
reversed — it is the concrete, executable version of this audit document,
not just a written claim.

`test_lag_feature_unaffected_by_changing_a_later_row` does the same check
for lag features.

`tests/unit/forecasting/test_ml_models.py::test_recursive_forecast_does_not_use_any_data_beyond_the_origin`
additionally proves the recursive multi-step forecaster's output is fully
determined by data up to the origin — nothing beyond it is even passed in,
so there's no way for it to leak in even in principle.
