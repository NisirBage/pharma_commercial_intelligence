import numpy as np
import pandas as pd

from app.forecasting.statistical_models import ets_forecast_with_interval, make_ets_forecaster


def _series_frame(n_days: int, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2018-01-01", periods=n_days, freq="D")
    # deterministic weekly-seasonal-ish series with mild noise
    base = 20 + 5 * np.sin(np.arange(n_days) * 2 * np.pi / 7)
    values = np.clip(base + rng.normal(0, 1, n_days), 0, None)
    return pd.DataFrame({"observation_date": dates, "units_sold": values})


def test_ets_forecaster_produces_correct_horizon_and_nonnegative_values():
    df = _series_frame(120)
    forecaster = make_ets_forecaster(seasonal_period=7)
    result = forecaster(df, horizon=14)
    assert len(result) == 14
    assert (result >= 0).all()


def test_ets_forecaster_falls_back_to_flat_mean_with_short_history():
    df = _series_frame(10)  # well under MIN_TRAIN_DAYS_FOR_SEASONAL_FIT * 2
    forecaster = make_ets_forecaster(seasonal_period=7)
    result = forecaster(df, horizon=5)
    expected = float(df["units_sold"].mean())
    assert np.allclose(result, expected)


def test_ets_forecast_with_interval_bounds_are_ordered_and_contain_point_forecast():
    df = _series_frame(120)
    summary = ets_forecast_with_interval(df, horizon=10, seasonal_period=7, alpha=0.1)
    assert len(summary) == 10
    assert (summary["pi_lower"] <= summary["mean"]).all()
    assert (summary["mean"] <= summary["pi_upper"]).all()
    assert (summary["pi_lower"] >= 0).all()  # demand cannot be negative
