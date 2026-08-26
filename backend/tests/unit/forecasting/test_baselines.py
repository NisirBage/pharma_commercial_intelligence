import numpy as np

from app.forecasting.baselines import moving_average_forecast, naive_forecast, seasonal_naive_forecast


def test_naive_forecast_carries_last_value_flat():
    result = naive_forecast(np.array([1.0, 2.0, 3.0, 10.0]), horizon=5)
    assert (result == 10.0).all()
    assert len(result) == 5


def test_seasonal_naive_repeats_the_last_full_cycle():
    train = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])  # one full week
    result = seasonal_naive_forecast(train, horizon=7, period=7)
    np.testing.assert_array_equal(result, train)


def test_seasonal_naive_tiles_for_horizon_longer_than_one_cycle():
    train = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0])
    result = seasonal_naive_forecast(train, horizon=10, period=7)
    expected = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 1.0, 2.0, 3.0])
    np.testing.assert_array_equal(result, expected)


def test_seasonal_naive_falls_back_to_naive_with_insufficient_history():
    train = np.array([1.0, 2.0, 3.0])  # < period=7
    result = seasonal_naive_forecast(train, horizon=4, period=7)
    assert (result == 3.0).all()


def test_moving_average_uses_trailing_window_only():
    train = np.array([10.0, 20.0, 30.0, 100.0, 100.0, 100.0, 100.0, 100.0])  # window=4 excludes the early low values
    result = moving_average_forecast(train, horizon=3, window=4)
    assert (result == 100.0).all()


def test_moving_average_uses_full_series_when_shorter_than_window():
    train = np.array([2.0, 4.0])
    result = moving_average_forecast(train, horizon=2, window=14)
    assert (result == 3.0).all()
