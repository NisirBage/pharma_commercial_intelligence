"""Final forecast generation, using the FULL observed history (through the
dataset's last date) and the model selected per ATC class by
app.forecasting.selection. Produces a point forecast plus an uncertainty
interval and a structured, API-ready output shape (M4 Sec. 20 — this is
the object a future `GET /api/v1/forecast/{atc_class}` endpoint would
serialize directly).
"""

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from app.forecasting.backtesting import to_array_forecaster
from app.forecasting.baselines import BASELINES
from app.forecasting.ml_models import linear_regression_forecaster, random_forest_forecaster
from app.forecasting.statistical_models import ets_forecast_with_interval, make_ets_forecaster

MODEL_FACTORIES = {
    "naive": lambda: to_array_forecaster(BASELINES["naive"]),
    "seasonal_naive_7": lambda: to_array_forecaster(BASELINES["seasonal_naive_7"]),
    "moving_average_14": lambda: to_array_forecaster(BASELINES["moving_average_14"]),
    "linear_regression": linear_regression_forecaster,
    "random_forest": random_forest_forecaster,
    "ets": lambda: make_ets_forecaster(),
}


def residual_based_interval(
    point_forecast: np.ndarray, fold_results: list[dict], alpha: float = 0.1
) -> tuple[np.ndarray, np.ndarray]:
    """Builds a per-horizon-step interval from the empirical distribution
    of out-of-fold backtest residuals AT THAT HORIZON STEP, pooled across
    every fold — a real, not invented, residual-based method (M4 Sec. 11).
    Assumes the residual distribution at a given horizon step is roughly
    stable over time (a stationarity assumption) — a genuine limitation,
    documented in docs/forecasting-methodology.md, not claimed to be exact."""
    horizon = len(point_forecast)
    residuals_by_step: list[list[float]] = [[] for _ in range(horizon)]
    for r in fold_results:
        res = r["residuals"]
        for step in range(min(horizon, len(res))):
            residuals_by_step[step].append(res[step])

    lower_q, upper_q = alpha / 2, 1 - alpha / 2
    lower = np.array(
        [
            point_forecast[i] + (np.quantile(residuals_by_step[i], lower_q) if residuals_by_step[i] else 0.0)
            for i in range(horizon)
        ]
    )
    upper = np.array(
        [
            point_forecast[i] + (np.quantile(residuals_by_step[i], upper_q) if residuals_by_step[i] else 0.0)
            for i in range(horizon)
        ]
    )
    lower = np.clip(lower, 0.0, None)
    upper = np.maximum(upper, lower)
    return lower, upper


@dataclass
class ForecastOutput:
    atc_class: str
    forecast_grain: str
    horizon: int
    model: str
    predictions: list[dict[str, Any]]  # [{date, point_forecast, lower_bound, upper_bound}]
    uncertainty_method: str
    evaluation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate_forecast(
    series_frame: pd.DataFrame,
    atc_class: str,
    model_name: str,
    fold_results_for_interval: list[dict],
    horizon: int = 14,
    alpha: float = 0.1,
    seasonal_period: int = 7,
    evaluation: dict[str, Any] | None = None,
) -> ForecastOutput:
    """series_frame: the full [observation_date, units_sold] series through
    the last observed date — nothing beyond it, since this IS the forecast
    origin."""
    last_date = series_frame["observation_date"].max()
    future_dates = [last_date + pd.Timedelta(days=i + 1) for i in range(horizon)]

    if model_name == "ets":
        summary = ets_forecast_with_interval(series_frame, horizon, seasonal_period=seasonal_period, alpha=alpha)
        point = summary["mean"].to_numpy()
        lower = summary["pi_lower"].to_numpy()
        upper = summary["pi_upper"].to_numpy()
        uncertainty_method = "ets_native_prediction_interval"
    else:
        forecaster = MODEL_FACTORIES[model_name]()
        point = np.asarray(forecaster(series_frame, horizon), dtype=float)
        lower, upper = residual_based_interval(point, fold_results_for_interval, alpha=alpha)
        uncertainty_method = "residual_based_backtest_quantile"

    predictions = [
        {"date": str(d.date()), "point_forecast": float(p), "lower_bound": float(lo), "upper_bound": float(up)}
        for d, p, lo, up in zip(future_dates, point, lower, upper)
    ]

    return ForecastOutput(
        atc_class=atc_class,
        forecast_grain="daily",
        horizon=horizon,
        model=model_name,
        predictions=predictions,
        uncertainty_method=uncertainty_method,
        evaluation=evaluation or {},
    )
