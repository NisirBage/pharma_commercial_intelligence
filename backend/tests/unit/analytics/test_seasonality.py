import pandas as pd

from app.analytics import seasonality
from tests.unit.analytics.helpers import daily_series_frame, hourly_pattern_frame, make_frame


def _weekday_pattern_frame(atc_code: str, n_weeks: int = 8, weekday_value: float = 10, weekend_value: float = 100):
    dates = pd.date_range(start="2020-01-06", periods=n_weeks * 7, freq="D")  # starts on a Monday
    values = [weekend_value if d.dayofweek >= 5 else weekday_value for d in dates]
    return daily_series_frame(atc_code, "2020-01-06", values)


def test_day_of_week_effect_detects_strong_weekend_pattern():
    frame = _weekday_pattern_frame("M01AB")
    result = seasonality.day_of_week_effect(frame)
    assert result.metadata["significant"] is True
    assert result.metadata["p_value"] < seasonality.SIGNIFICANCE_ALPHA
    assert result.metadata["mean_units_by_weekday"]["Sunday"] > result.metadata["mean_units_by_weekday"]["Monday"]


def test_day_of_week_effect_empty_dataset():
    result = seasonality.day_of_week_effect(make_frame([]))
    assert result.metadata["reason"] == "no_data"


def test_hour_of_day_effect_detects_diurnal_pattern():
    frame = hourly_pattern_frame("M01AB", n_days=20, hour_values={8: 5.0, 14: 50.0, 20: 5.0})
    result = seasonality.hour_of_day_effect(frame)
    assert result.metadata["significant"] is True
    assert result.metadata["mean_units_by_hour"][14] > result.metadata["mean_units_by_hour"][8]
    assert "salesdaily.csv" in result.metadata["source"]  # documents it is NOT using the Hour artifact


def test_hour_of_day_effect_empty_dataset():
    result = seasonality.hour_of_day_effect(make_frame([]))
    assert result.metadata["reason"] == "no_data"


def test_seasonal_strength_higher_for_repeating_pattern_than_pure_trend():
    weekly_pattern = [10, 20, 30, 40, 50, 60, 70] * 12  # 84 days, strong 7-day cycle
    cyclical = daily_series_frame("M01AB", "2020-01-01", weekly_pattern)
    linear_ramp = daily_series_frame("N05B", "2020-01-01", list(range(84)))  # no real weekly cycle

    cyclical_result = seasonality.seasonal_strength(cyclical, entity="M01AB", grain="daily", period=7)
    ramp_result = seasonality.seasonal_strength(linear_ramp, entity="N05B", grain="daily", period=7)

    assert cyclical_result.value is not None and ramp_result.value is not None
    assert 0.0 <= cyclical_result.value <= 1.0
    assert 0.0 <= ramp_result.value <= 1.0
    assert cyclical_result.value > ramp_result.value


def test_seasonal_strength_insufficient_periods():
    short = daily_series_frame("M01AB", "2020-01-01", [10] * 5)  # far fewer than 2*period=14
    result = seasonality.seasonal_strength(short, grain="daily", period=7)
    assert result.value is None
    assert result.metadata["reason"] == "insufficient_periods"


def test_seasonal_strength_empty_dataset():
    result = seasonality.seasonal_strength(make_frame([]))
    assert result.metadata["reason"] == "no_data"
