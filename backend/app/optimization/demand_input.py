"""Demand input layer for optimization. Consumes the EXISTING M4
forecasting package end to end — this module contains no forecasting
logic of its own, only orchestration:

- The selected model per ATC class comes from M4's own model registry
  (`app.forecasting.registry`), never re-decided here.
- The point forecast comes from `app.forecasting.predictions.generate_forecast`
  — the exact same function M4 uses for its final future forecast.
- Per-horizon-step forecast-error (residual) distributions come from
  re-running `app.forecasting.backtesting.run_backtest` for the ALREADY
  SELECTED model only (M4's saved results kept derived summaries — mean
  residual, Ljung-Box — not the raw per-fold residual arrays this module
  needs for the lead-time uncertainty calculation in
  app.optimization.safety_stock). This is cheap: none of the 9 models M4
  selected is Random Forest or Linear Regression, the two expensive
  candidates.

This is what "the optimization layer should consume forecast + forecast
uncertainty from the existing forecasting package" (M5 Sec. 3) means in
code.
"""

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from app.analytics.data_access import load_from_raw_csv
from app.forecasting.backtesting import generate_folds, run_backtest, to_array_forecaster
from app.forecasting.baselines import BASELINES
from app.forecasting.datasets import SeriesPrepResult, build_all_series
from app.forecasting.ml_models import linear_regression_forecaster, random_forest_forecaster
from app.forecasting.predictions import ForecastOutput, generate_forecast
from app.forecasting.registry import REGISTRY_DIR, load_registry
from app.forecasting.statistical_models import make_ets_forecaster

# Identical to M4's own choices (backend/scripts/run_m4_backtest.py) —
# re-derived here as constants, not re-decided, so the backtest re-run
# below reproduces exactly the folds M4 evaluated the selected model on.
HORIZON = 14
N_FOLDS = 6
MIN_TRAIN_DAYS = 180
SEASONAL_PERIOD = 7

FORECASTER_FACTORIES = {
    "naive": lambda: to_array_forecaster(BASELINES["naive"]),
    "seasonal_naive_7": lambda: to_array_forecaster(BASELINES["seasonal_naive_7"]),
    "moving_average_14": lambda: to_array_forecaster(BASELINES["moving_average_14"]),
    "linear_regression": linear_regression_forecaster,
    "random_forest": random_forest_forecaster,
    "ets": lambda: make_ets_forecaster(seasonal_period=SEASONAL_PERIOD),
}


@dataclass
class DemandInput:
    atc_class: str
    selected_model: str
    evaluation_metrics: dict
    point_forecast: list[float]  # 14 values — the days immediately after the dataset's last observed date
    forecast_dates: list[str]
    historical_daily_demand: list[float]
    residual_std_by_step: list[float]  # length 14 — std of the selected model's out-of-fold error AT each horizon step
    fold_cumulative_errors: dict[int, list[float]]  # lead_time_days L -> the 6 folds' L-day cumulative forecast errors
    forecast_output: ForecastOutput  # M4's own output object, unmodified — see the module docstring
    fold_results: list[dict] = field(default_factory=list)
    """The raw per-fold backtest results (each a dict with an "residuals"
    list, among other keys — see app.forecasting.backtesting.run_backtest)
    for the selected model, kept for reuse by app.forecasting.diagnostics
    (M6's forecast-diagnostics endpoint) without re-running the backtest a
    third time. Added in M6 — purely additive (a defaulted field), so
    every M5 caller/test that predates it is unaffected."""


def _selected_model_record(entity: str, registry_dir: Path) -> dict:
    records = load_registry(registry_dir)
    record = next((r for r in records if r["atc_class"] == entity), None)
    if record is None:
        raise ValueError(
            f"No M4 registry record found for {entity!r} — run backend/scripts/run_m4_backtest.py first."
        )
    return record


def build_demand_input(entity: str, prep: SeriesPrepResult, registry_dir: Path = REGISTRY_DIR) -> DemandInput:
    record = _selected_model_record(entity, registry_dir)
    model_name = record["model_name"]
    evaluation_metrics = record["evaluation_metrics"]

    full_frame = prep.frame
    test_start = full_frame["observation_date"].max() - pd.Timedelta(days=HORIZON - 1)
    backtest_eligible = full_frame[full_frame["observation_date"] < test_start]
    folds = generate_folds(
        backtest_eligible["observation_date"], horizon=HORIZON, n_folds=N_FOLDS, min_train_days=MIN_TRAIN_DAYS
    )
    forecaster = FORECASTER_FACTORIES[model_name]()
    fold_results = run_backtest(backtest_eligible, forecaster, folds, seasonal_period=SEASONAL_PERIOD)

    residuals_matrix = np.array([r["residuals"] for r in fold_results])  # shape (n_folds, horizon)
    residual_std_by_step = [float(np.std(residuals_matrix[:, h])) for h in range(HORIZON)]
    fold_cumulative_errors = {
        lead_time: [float(np.sum(residuals_matrix[f, :lead_time])) for f in range(residuals_matrix.shape[0])]
        for lead_time in range(1, HORIZON + 1)
    }

    forecast_output = generate_forecast(
        full_frame,
        entity,
        model_name,
        fold_results,
        horizon=HORIZON,
        seasonal_period=SEASONAL_PERIOD,
        evaluation=evaluation_metrics,
    )

    return DemandInput(
        atc_class=entity,
        selected_model=model_name,
        evaluation_metrics=evaluation_metrics,
        point_forecast=[p["point_forecast"] for p in forecast_output.predictions],
        forecast_dates=[p["date"] for p in forecast_output.predictions],
        historical_daily_demand=full_frame["units_sold"].tolist(),
        residual_std_by_step=residual_std_by_step,
        fold_cumulative_errors=fold_cumulative_errors,
        forecast_output=forecast_output,
        fold_results=fold_results,
    )


def build_all_demand_inputs(
    raw_data_dir: Path | None = None, registry_dir: Path = REGISTRY_DIR
) -> dict[str, DemandInput]:
    df = load_from_raw_csv(raw_data_dir)
    series_by_entity = build_all_series(df)
    return {entity: build_demand_input(entity, prep, registry_dir) for entity, prep in series_by_entity.items()}
