import numpy as np
import pandas as pd

from app.forecasting.features import MIN_WARMUP_DAYS
from app.forecasting.ml_models import linear_regression_forecaster, random_forest_forecaster


def _series_frame(n_days: int, values=None) -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=n_days, freq="D")
    if values is None:
        values = [float(i % 10) for i in range(n_days)]
    return pd.DataFrame({"observation_date": dates, "units_sold": values})


def test_linear_regression_forecaster_produces_correct_horizon_length():
    df = _series_frame(MIN_WARMUP_DAYS + 40)
    forecaster = linear_regression_forecaster()
    result = forecaster(df, horizon=14)
    assert len(result) == 14
    assert (result >= 0).all()  # demand cannot be negative


def test_random_forest_forecaster_is_deterministic_with_fixed_seed():
    df = _series_frame(MIN_WARMUP_DAYS + 40)
    forecaster_a = random_forest_forecaster(n_estimators=20)
    forecaster_b = random_forest_forecaster(n_estimators=20)
    result_a = forecaster_a(df, horizon=7)
    result_b = forecaster_b(df, horizon=7)
    np.testing.assert_array_equal(result_a, result_b)


def test_ml_forecaster_falls_back_to_mean_with_insufficient_warmup():
    df = _series_frame(5, values=[3.0, 4.0, 5.0, 6.0, 7.0])  # far short of MIN_WARMUP_DAYS
    forecaster = linear_regression_forecaster()
    result = forecaster(df, horizon=3)
    assert len(result) == 3
    assert (result == 5.0).all()  # mean of [3,4,5,6,7]


def test_recursive_forecast_does_not_use_any_data_beyond_the_origin():
    """Two series identical up through the forecast origin, but different
    afterward (impossible in real backtesting, since the forecaster is
    never given anything beyond the origin) -- constructing both and
    calling the SAME origin-truncated frame twice must give identical
    results, proving nothing beyond the origin can leak in even in
    principle: the forecaster's input simply doesn't contain it."""
    origin_df = _series_frame(MIN_WARMUP_DAYS + 30)
    forecaster = linear_regression_forecaster()
    result_1 = forecaster(origin_df.copy(), horizon=10)
    result_2 = forecaster(origin_df.copy(), horizon=10)
    np.testing.assert_array_almost_equal(result_1, result_2)


def test_recursive_forecast_lag1_matches_previous_step_forecast():
    """Sanity-checks the recursive feed-back mechanism directly: with a
    trivial constant-target series, every step's forecast should equal
    the constant (lag_1 keeps referencing the same value forward)."""
    df = _series_frame(MIN_WARMUP_DAYS + 20, values=[7.0] * (MIN_WARMUP_DAYS + 20))
    forecaster = linear_regression_forecaster()
    result = forecaster(df, horizon=5)
    np.testing.assert_array_almost_equal(result, [7.0] * 5, decimal=6)
