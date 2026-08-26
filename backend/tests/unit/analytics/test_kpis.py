import pandas as pd

from app.analytics import kpis
from app.analytics.aggregate import to_monthly
from tests.unit.analytics.helpers import daily_series_frame, make_frame


def test_total_demand_empty_dataset_returns_zero_not_error():
    empty = make_frame([])
    result = kpis.total_demand(empty)
    assert result.value == 0.0
    assert result.metadata["n_observations"] == 0


def test_total_demand_single_record():
    frame = daily_series_frame("M01AB", "2020-01-01", [7.0])
    result = kpis.total_demand(frame)
    assert result.value == 7.0


def test_total_demand_is_grain_invariant():
    frame = daily_series_frame("M01AB", "2020-01-01", [1, 2, 3, 4, 5])
    totals = {g: kpis.total_demand(frame, grain=g).value for g in ("hourly", "daily", "weekly", "monthly")}
    assert len(set(totals.values())) == 1  # every grain sums to the same total
    assert totals["hourly"] == 15.0


def test_average_median_peak_min_demand_daily_grain():
    frame = daily_series_frame("M01AB", "2020-01-01", [1, 2, 3, 4, 100])
    assert kpis.average_demand(frame, grain="daily").value == 22.0
    assert kpis.median_demand(frame, grain="daily").value == 3.0
    peak = kpis.peak_demand(frame, grain="daily")
    assert peak.value == 100.0
    assert peak.metadata["peak_period"] == "2020-01-05 00:00:00"
    trough = kpis.min_demand(frame, grain="daily")
    assert trough.value == 1.0


def test_average_demand_on_empty_dataset_returns_none_with_reason():
    result = kpis.average_demand(make_frame([]))
    assert result.value is None
    assert result.metadata["reason"] == "no_data"


def _two_full_months_frame(jan_value: float, feb_value: float) -> pd.DataFrame:
    """2020 is a leap year: Jan has 31 days, Feb has 29 — both built as
    exactly one real calendar month each, so to_monthly's rollup produces
    exactly two clean periods without any partial-month edge effects."""
    return pd.concat(
        [
            daily_series_frame("M01AB", "2020-01-01", [jan_value] * 31),
            daily_series_frame("M01AB", "2020-02-01", [feb_value] * 29),
        ]
    )


def test_period_over_period_growth_positive_and_negative():
    growing = _two_full_months_frame(10, 20)
    rolled = to_monthly(growing, by_atc=False).sort_values("month_start_date")
    expected_growth = float((rolled["units_sold"].iloc[1] - rolled["units_sold"].iloc[0]) / rolled["units_sold"].iloc[0] * 100)
    result = kpis.period_over_period_growth(growing, grain="monthly")
    assert abs(result.value - expected_growth) < 1e-9

    shrinking = _two_full_months_frame(20, 10)
    result2 = kpis.period_over_period_growth(shrinking, grain="monthly")
    assert result2.value < 0  # demand fell month over month


def test_period_over_period_growth_previous_zero_returns_none_not_inf():
    frame = _two_full_months_frame(0, 10)
    result = kpis.period_over_period_growth(frame, grain="monthly")
    assert result.value is None
    assert result.metadata["reason"] == "previous_period_zero"


def test_period_over_period_growth_insufficient_periods():
    frame = daily_series_frame("M01AB", "2020-01-01", [10] * 5)  # < 1 month
    result = kpis.period_over_period_growth(frame, grain="monthly")
    assert result.value is None
    assert result.metadata["reason"] == "insufficient_periods"


def test_contribution_by_atc_shares_sum_to_100():
    frame = pd.concat(
        [
            daily_series_frame("M01AB", "2020-01-01", [60]),
            daily_series_frame("N05B", "2020-01-01", [40]),
        ]
    )
    results = kpis.contribution_by_atc(frame)
    shares = {r.entity: r.value for r in results}
    assert shares["M01AB"] == 60.0
    assert shares["N05B"] == 40.0
    assert abs(sum(shares.values()) - 100.0) < 1e-9


def test_contribution_by_atc_empty_dataset():
    assert kpis.contribution_by_atc(make_frame([])) == []
