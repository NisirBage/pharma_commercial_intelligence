import calendar

import pandas as pd

from app.analytics import trends
from tests.unit.analytics.helpers import daily_series_frame, make_frame


def _monthly_step_frame(atc_code: str, monthly_values: list[float], start: str = "2020-01-01") -> pd.DataFrame:
    """Builds one real calendar month per value in `monthly_values`, every
    day within a month sharing that month's value — used only to control
    the SIGN and presence/absence of a trend; exact numeric totals aren't
    asserted since month lengths vary."""
    frames = []
    cursor = pd.Timestamp(start)
    for v in monthly_values:
        n_days = calendar.monthrange(cursor.year, cursor.month)[1]
        frames.append(daily_series_frame(atc_code, cursor.strftime("%Y-%m-%d"), [v] * n_days))
        cursor = cursor + pd.offsets.MonthBegin(1)
    return pd.concat(frames)


def test_linear_trend_detects_clear_growth():
    frame = _monthly_step_frame("M01AB", [10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32])
    result = trends.linear_trend(frame)
    assert result.value > 0
    assert result.metadata["classification"] == "growing"
    assert result.metadata["p_value"] < trends.SIGNIFICANCE_ALPHA


def test_linear_trend_detects_clear_decline():
    frame = _monthly_step_frame("M01AB", [32, 30, 28, 26, 24, 22, 20, 18, 16, 14, 12, 10])
    result = trends.linear_trend(frame)
    assert result.value < 0
    assert result.metadata["classification"] == "declining"


def test_linear_trend_flat_series_is_not_significant():
    frame = _monthly_step_frame("M01AB", [10, 20, 10, 20, 10, 20, 10, 20, 10, 20, 10, 20])
    result = trends.linear_trend(frame)
    assert result.metadata["classification"] == "stable_or_no_significant_trend"


def test_linear_trend_insufficient_periods():
    frame = _monthly_step_frame("M01AB", [10, 12])  # only 2 months
    result = trends.linear_trend(frame)
    assert result.value is None
    assert result.metadata["reason"] == "insufficient_periods"


def test_linear_trend_empty_dataset():
    result = trends.linear_trend(make_frame([]))
    assert result.value is None
    assert result.metadata["reason"] == "no_data"


def test_yearly_totals_flags_partial_years_and_computes_yoy():
    # Year 2020: only 5 observed days (partial). Year 2021: a full year.
    frame = pd.concat(
        [
            daily_series_frame("M01AB", "2020-12-27", [10, 10, 10, 10, 10]),  # 5 days -> partial 2020
            daily_series_frame("M01AB", "2021-01-01", [20] * 365),  # full 2021
        ]
    )
    results = trends.yearly_totals(frame)
    by_year = {r.period: r for r in results}

    assert by_year["2020"].metadata["is_complete_year"] is False
    assert by_year["2020"].metadata["n_days_observed"] == 5
    assert by_year["2021"].metadata["is_complete_year"] is True
    assert by_year["2021"].metadata["n_days_observed"] == 365

    expected_yoy = (by_year["2021"].value - by_year["2020"].value) / by_year["2020"].value * 100
    assert abs(by_year["2021"].metadata["yoy_growth_pct"] - expected_yoy) < 1e-9
    assert by_year["2020"].metadata["yoy_growth_pct"] is None  # no prior year to compare


def test_yearly_totals_empty_dataset():
    assert trends.yearly_totals(make_frame([])) == []
