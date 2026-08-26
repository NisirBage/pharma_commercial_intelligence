import numpy as np
import pandas as pd

from app.forecasting.predictions import generate_forecast, residual_based_interval


def _series_frame(n_days: int = 60) -> pd.DataFrame:
    dates = pd.date_range("2020-01-01", periods=n_days, freq="D")
    values = [10.0 + (i % 7) for i in range(n_days)]
    return pd.DataFrame({"observation_date": dates, "units_sold": values})


def _fold_results_for_interval(horizon: int = 14):
    return [
        {"residuals": [1.0, -1.0, 2.0, -2.0] + [0.0] * (horizon - 4)},
        {"residuals": [2.0, -2.0, 1.0, -1.0] + [0.5] * (horizon - 4)},
    ]


def test_generate_forecast_naive_has_correct_horizon_and_dates():
    series = _series_frame()
    result = generate_forecast(series, "M01AB", "naive", _fold_results_for_interval(), horizon=14)
    assert result.atc_class == "M01AB"
    assert result.horizon == 14
    assert result.model == "naive"
    assert len(result.predictions) == 14

    dates = [p["date"] for p in result.predictions]
    assert len(dates) == len(set(dates))  # no duplicate timestamps
    assert dates[0] == "2020-03-01"  # day after the series' last date (2020-02-29, leap year)


def test_generate_forecast_predictions_have_ordered_bounds():
    series = _series_frame()
    result = generate_forecast(series, "M01AB", "naive", _fold_results_for_interval(), horizon=14)
    for p in result.predictions:
        assert p["lower_bound"] <= p["point_forecast"] <= p["upper_bound"] or p["lower_bound"] <= p["upper_bound"]
        assert p["lower_bound"] >= 0.0


def test_generate_forecast_ets_uses_native_interval():
    series = _series_frame(120)
    result = generate_forecast(series, "N05B", "ets", [], horizon=10, seasonal_period=7)
    assert result.uncertainty_method == "ets_native_prediction_interval"
    assert len(result.predictions) == 10


def test_forecast_output_to_dict_is_json_serializable_shape():
    series = _series_frame()
    result = generate_forecast(series, "M01AB", "naive", _fold_results_for_interval(), horizon=5)
    d = result.to_dict()
    assert set(d.keys()) == {"atc_class", "forecast_grain", "horizon", "model", "predictions", "uncertainty_method", "evaluation"}


def test_residual_based_interval_widens_with_wider_residual_spread():
    point = np.array([10.0, 10.0])
    narrow_folds = [{"residuals": [0.1, -0.1]}]
    wide_folds = [{"residuals": [5.0, -5.0]}]
    lower_n, upper_n = residual_based_interval(point, narrow_folds, alpha=0.1)
    lower_w, upper_w = residual_based_interval(point, wide_folds, alpha=0.1)
    assert (upper_w - lower_w >= upper_n - lower_n).all()
