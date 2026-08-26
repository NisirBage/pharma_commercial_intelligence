"""Statistical time-series candidate: Exponential Smoothing (Holt-Winters,
via statsmodels' `ETSModel`).

Chosen over SARIMA: ETS directly and simply models trend + seasonality —
matching M3's confirmed trend and seasonality findings — without SARIMA's
heavier order-selection search (p/d/q × P/D/Q grid), which is harder to
justify at this project's scope and adds material runtime cost across
8 classes × multiple folds. See docs/forecasting-methodology.md Sec. 5 for
the full candidate-selection rationale.

Additive (not multiplicative) trend/seasonal components only — this
dataset has genuine zero-demand days (M1/M2/M3), and multiplicative ETS
components are undefined at zero.
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.exponential_smoothing.ets import ETSModel

TARGET_COL = "units_sold"

# Need at least 2 full seasonal cycles for a seasonal component to be
# identifiable at all.
MIN_TRAIN_DAYS_FOR_SEASONAL_FIT = 14


def _as_dated_series(train_df: pd.DataFrame) -> pd.Series:
    """ETSModel needs a properly date-indexed Series (not a raw ndarray)
    for `get_prediction`'s internal index bookkeeping to work at all — a
    plain array input makes statsmodels' `PredictionResults` crash trying
    to read `.index` off what it assumes is a pandas object. Builds an
    explicit daily-frequency DatetimeIndex from the training dates
    themselves (never inferred/guessed) so forecast dates line up exactly
    with `app.forecasting.datasets`' gap-free daily series."""
    series = train_df.set_index("observation_date")[TARGET_COL].astype(float)
    series.index.freq = "D"
    return series


def _fit_ets(series: pd.Series, seasonal_period: int, trend: str, seasonal: str):
    return ETSModel(series, trend=trend, seasonal=seasonal, seasonal_periods=seasonal_period).fit(disp=False)


def make_ets_forecaster(seasonal_period: int = 7, trend: str = "add", seasonal: str = "add"):
    """Returns a (train_df, horizon) -> np.ndarray forecaster matching the
    common backtesting interface (app.forecasting.backtesting.Forecaster).
    Falls back to a flat trailing-window mean — a documented, conservative
    fallback, not a silent success — when there's insufficient history for
    a seasonal fit, or when ETS fails to converge on a particular fold
    (this happens occasionally on short/sparse early folds; failing the
    whole backtest run for one non-convergent fold would be worse)."""

    def _forecaster(train_df: pd.DataFrame, horizon: int) -> np.ndarray:
        values = train_df[TARGET_COL].to_numpy(dtype=float)
        if len(values) < MIN_TRAIN_DAYS_FOR_SEASONAL_FIT * 2:
            return np.full(horizon, float(np.mean(values)), dtype=float)
        try:
            fit = _fit_ets(_as_dated_series(train_df), seasonal_period, trend, seasonal)
            forecast = np.asarray(fit.forecast(horizon), dtype=float)
        except Exception:
            forecast = np.full(horizon, float(np.mean(values[-seasonal_period:])), dtype=float)
        return np.clip(forecast, a_min=0.0, a_max=None)  # demand volume cannot be negative

    return _forecaster


def ets_forecast_with_interval(
    train_df: pd.DataFrame, horizon: int, seasonal_period: int = 7, alpha: float = 0.1
) -> pd.DataFrame:
    """Used only for the FINAL forecast (app.forecasting.predictions), not
    during backtesting. Returns statsmodels' native prediction interval —
    `alpha=0.1` -> a 90% interval. Raises rather than silently falling
    back, since a failed final forecast should be visible, not masked."""
    values = train_df[TARGET_COL].to_numpy(dtype=float)
    if len(values) < MIN_TRAIN_DAYS_FOR_SEASONAL_FIT * 2:
        raise ValueError(f"Insufficient history ({len(values)} days) for an ETS seasonal fit.")
    series = _as_dated_series(train_df)
    fit = _fit_ets(series, seasonal_period, "add", "add")
    forecast_index = pd.date_range(series.index[-1] + pd.Timedelta(days=1), periods=horizon, freq="D")
    pred = fit.get_prediction(start=forecast_index[0], end=forecast_index[-1])
    summary = pred.summary_frame(alpha=alpha)
    summary[["mean", "pi_lower", "pi_upper"]] = summary[["mean", "pi_lower", "pi_upper"]].clip(lower=0.0)
    return summary.reset_index(drop=True)
