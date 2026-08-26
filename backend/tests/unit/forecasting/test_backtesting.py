import numpy as np
import pandas as pd
import pytest

from app.forecasting.backtesting import generate_folds, run_backtest, summarize_backtest, to_array_forecaster


def _dates(n_days: int, start: str = "2020-01-01") -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.date_range(start, periods=n_days, freq="D"))


def test_generate_folds_are_strictly_chronological_and_non_overlapping():
    dates = _dates(200)
    folds = generate_folds(dates, horizon=14, n_folds=5, min_train_days=60)
    assert len(folds) >= 1
    for f in folds:
        assert f.validation_start_date == f.train_end_date + pd.Timedelta(days=1)
        assert f.validation_end_date == f.validation_start_date + pd.Timedelta(days=13)
        assert f.train_end_date < f.validation_start_date  # no leakage of validation into training

    # fold origins must move strictly forward (expanding window, never backward)
    train_ends = [f.train_end_date for f in folds]
    assert train_ends == sorted(train_ends)
    assert len(set(train_ends)) == len(train_ends)


def test_generate_folds_respects_min_train_days():
    dates = _dates(200)
    folds = generate_folds(dates, horizon=14, n_folds=5, min_train_days=60)
    first_train_length = (folds[0].train_end_date - dates[0]).days + 1
    assert first_train_length >= 60


def test_generate_folds_raises_when_history_too_short():
    dates = _dates(30)
    with pytest.raises(ValueError, match="Not enough history"):
        generate_folds(dates, horizon=14, n_folds=5, min_train_days=60)


def test_run_backtest_produces_correct_horizon_and_uses_only_prior_data():
    dates = _dates(100)
    series_df = pd.DataFrame({"observation_date": dates, "units_sold": np.arange(100, dtype=float)})
    folds = generate_folds(dates, horizon=7, n_folds=3, min_train_days=50)

    seen_train_sizes = []

    def spy_forecaster(train_df, horizon):
        seen_train_sizes.append(len(train_df))
        # the forecaster must never see a units_sold value >= the number of
        # training rows it was given (would indicate leaked future data)
        assert train_df["units_sold"].max() == len(train_df) - 1
        return np.zeros(horizon)

    results = run_backtest(series_df, spy_forecaster, folds)
    assert len(results) == len(folds)
    for r in results:
        assert r["horizon"] == 7
        assert len(r["actual"]) == 7
        assert len(r["predicted"]) == 7

    # expanding window: later folds must have strictly more training data
    assert seen_train_sizes == sorted(seen_train_sizes)


def test_run_backtest_with_naive_baseline_via_adapter():
    from app.forecasting.baselines import naive_forecast

    dates = _dates(60)
    series_df = pd.DataFrame({"observation_date": dates, "units_sold": [5.0] * 60})
    folds = generate_folds(dates, horizon=5, n_folds=2, min_train_days=30)
    results = run_backtest(series_df, to_array_forecaster(naive_forecast), folds)
    for r in results:
        assert r["mae"] == 0.0  # constant series -> naive forecast is exact


def test_summarize_backtest_averages_across_folds():
    fold_results = [
        {"mae": 2.0, "rmse": 3.0, "wape": 10.0, "mase": 0.5},
        {"mae": 4.0, "rmse": 5.0, "wape": 20.0, "mase": 1.5},
    ]
    summary = summarize_backtest(fold_results)
    assert summary["mae"] == 3.0
    assert summary["wape"] == 15.0


def test_summarize_backtest_empty_folds():
    summary = summarize_backtest([])
    assert summary == {"mae": None, "rmse": None, "wape": None, "mase": None}
