import pandas as pd

from app.analytics import volatility
from tests.unit.analytics.helpers import daily_series_frame, make_frame


def test_coefficient_of_variation_known_values():
    # values: 10, 10, 10, 10, 30 -> mean=14, population-ish sample std computed by pandas (ddof=1)
    frame = daily_series_frame("M01AB", "2020-01-01", [10, 10, 10, 10, 30])
    result = volatility.coefficient_of_variation(frame, grain="daily")
    s = pd.Series([10, 10, 10, 10, 30])
    expected_cv = float(s.std() / s.mean())
    assert abs(result.value - expected_cv) < 1e-9


def test_coefficient_of_variation_zero_mean():
    frame = daily_series_frame("M01AB", "2020-01-01", [0, 0, 0, 0])
    result = volatility.coefficient_of_variation(frame, grain="daily")
    assert result.value is None
    assert result.metadata["reason"] == "zero_mean"


def test_coefficient_of_variation_insufficient_periods():
    frame = daily_series_frame("M01AB", "2020-01-01", [10])  # single record
    result = volatility.coefficient_of_variation(frame, grain="daily")
    assert result.value is None
    assert result.metadata["reason"] == "insufficient_periods"


def test_coefficient_of_variation_empty_dataset():
    result = volatility.coefficient_of_variation(make_frame([]))
    assert result.value is None
    assert result.metadata["reason"] == "no_data"


def test_rolling_std_shape_and_min_periods():
    frame = daily_series_frame("M01AB", "2020-01-01", list(range(1, 21)))  # 20 days
    out = volatility.rolling_std(frame, window_days=7)
    assert len(out) == 20
    assert out["rolling_std"].iloc[:6].isna().all()  # not enough history for the first 6 days
    assert pd.notna(out["rolling_std"].iloc[6])  # 7th day has a full window


def test_rolling_std_empty_dataset():
    out = volatility.rolling_std(make_frame([]))
    assert out.empty


def test_interquartile_range_known_values():
    frame = daily_series_frame("M01AB", "2020-01-01", [1, 2, 3, 4, 5, 6, 7, 8])
    result = volatility.interquartile_range(frame, grain="daily")
    s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8])
    expected = float(s.quantile(0.75) - s.quantile(0.25))
    assert abs(result.value - expected) < 1e-9


def test_interquartile_range_insufficient_periods():
    frame = daily_series_frame("M01AB", "2020-01-01", [1, 2, 3])  # fewer than 4
    result = volatility.interquartile_range(frame, grain="daily")
    assert result.value is None
    assert result.metadata["reason"] == "insufficient_periods"


def test_rank_by_volatility_orders_descending_and_puts_undefined_last():
    frame = pd.concat(
        [
            daily_series_frame("M01AB", "2020-01-01", [10, 10, 10, 10, 10]),  # CV = 0 (perfectly stable)
            daily_series_frame("N05B", "2020-01-01", [1, 50, 1, 50, 1]),  # high CV
            daily_series_frame("N02BE", "2020-01-01", [0, 0, 0, 0, 0]),  # undefined (zero mean)
        ]
    )
    ranked = volatility.rank_by_volatility(frame, grain="daily")
    codes_in_order = [r.entity for r in ranked]
    assert codes_in_order[0] == "N05B"  # most volatile first
    assert codes_in_order[-1] == "N02BE"  # undefined CV ranked last, not dropped
