import numpy as np

from app.forecasting.metrics import evaluate, mae, mase, rmse, wape


def test_mae_and_rmse_known_values():
    actual = np.array([10.0, 20.0, 30.0])
    predicted = np.array([12.0, 18.0, 33.0])
    assert mae(actual, predicted) == np.mean([2, 2, 3])
    assert abs(rmse(actual, predicted) - np.sqrt(np.mean([4, 4, 9]))) < 1e-9


def test_wape_known_value():
    actual = np.array([10.0, 20.0, 30.0])
    predicted = np.array([15.0, 20.0, 25.0])
    # sum(|err|) = 5+0+5 = 10; sum(|actual|) = 60 -> 16.666...%
    assert abs(wape(actual, predicted) - (10 / 60 * 100)) < 1e-9


def test_wape_undefined_when_all_actuals_zero():
    assert wape(np.array([0.0, 0.0]), np.array([1.0, 2.0])) is None


def test_wape_handles_some_zero_actuals_without_error():
    # a single zero-demand day among nonzero ones must not blow up WAPE
    # (this is exactly why MAPE was rejected in favor of WAPE -- see
    # app/forecasting/metrics.py's module docstring)
    result = wape(np.array([0.0, 10.0]), np.array([1.0, 9.0]))
    assert result is not None
    assert abs(result - (2 / 10 * 100)) < 1e-9


def test_mase_beats_naive_when_forecast_is_better_than_in_sample_naive():
    train = np.array([10.0, 12.0, 8.0, 11.0, 9.0, 13.0, 10.0, 12.0])
    actual = np.array([10.0, 10.0])
    perfect_predicted = actual.copy()
    result = mase(actual, perfect_predicted, train, seasonal_period=1)
    assert result == 0.0


def test_mase_undefined_for_constant_training_series():
    train = np.array([5.0, 5.0, 5.0, 5.0])  # naive in-sample MAE = 0 -> division by zero
    result = mase(np.array([5.0]), np.array([6.0]), train, seasonal_period=1)
    assert result is None


def test_mase_undefined_when_training_series_too_short():
    train = np.array([5.0])  # shorter than seasonal_period
    result = mase(np.array([5.0]), np.array([6.0]), train, seasonal_period=7)
    assert result is None


def test_evaluate_returns_all_four_metrics():
    train = np.array([10.0, 12.0, 8.0, 11.0, 9.0, 13.0, 10.0, 12.0, 11.0, 10.0])
    actual = np.array([10.0, 11.0])
    predicted = np.array([9.0, 12.0])
    result = evaluate(actual, predicted, train, seasonal_period=7)
    assert set(result.keys()) == {"mae", "rmse", "wape", "mase"}
    assert all(v is not None for v in result.values())
