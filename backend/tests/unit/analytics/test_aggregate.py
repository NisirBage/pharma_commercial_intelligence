import pandas as pd

from app.analytics.aggregate import to_daily, to_monthly, to_weekly
from tests.unit.analytics.helpers import make_frame


def _tiny_frame():
    # 2020-01-01 is a Wednesday; 2020-01-05 is the following Sunday.
    return make_frame(
        [
            {"atc_code": "M01AB", "observation_ts": "2020-01-01 08:00", "units_sold": 1.0},
            {"atc_code": "M01AB", "observation_ts": "2020-01-01 09:00", "units_sold": 1.0},
            {"atc_code": "M01AB", "observation_ts": "2020-01-02 08:00", "units_sold": 5.0},
            {"atc_code": "N05B", "observation_ts": "2020-01-01 08:00", "units_sold": 10.0},
        ]
    )


def test_to_daily_sums_within_day_per_atc():
    out = to_daily(_tiny_frame(), by_atc=True)
    m01ab_jan1 = out[(out["atc_code"] == "M01AB") & (out["observation_date"] == pd.Timestamp("2020-01-01"))]
    assert m01ab_jan1["units_sold"].iloc[0] == 2.0


def test_to_daily_by_atc_false_sums_across_classes():
    out = to_daily(_tiny_frame(), by_atc=False)
    jan1_total = out[out["observation_date"] == pd.Timestamp("2020-01-01")]["units_sold"].iloc[0]
    assert jan1_total == 2.0 + 10.0  # M01AB (1+1) + N05B (10)


def test_to_weekly_uses_sunday_ending_convention():
    out = to_weekly(_tiny_frame(), by_atc=False)
    # both days fall in the week ending 2020-01-05 (Sunday)
    assert list(out["week_ending_date"]) == [pd.Timestamp("2020-01-05")]
    assert out["units_sold"].iloc[0] == 2.0 + 5.0 + 10.0


def test_to_monthly_uses_month_start_convention():
    out = to_monthly(_tiny_frame(), by_atc=False)
    assert list(out["month_start_date"]) == [pd.Timestamp("2020-01-01")]
    assert out["units_sold"].iloc[0] == 2.0 + 5.0 + 10.0


def test_total_conserved_across_grains():
    """Conservation check: whatever grain you roll up to, the grand total
    must be unchanged — this is the property the whole hybrid architecture
    depends on (see docs/data-model.md)."""
    frame = _tiny_frame()
    raw_total = frame["units_sold"].sum()
    assert to_daily(frame, by_atc=False)["units_sold"].sum() == raw_total
    assert to_weekly(frame, by_atc=False)["units_sold"].sum() == raw_total
    assert to_monthly(frame, by_atc=False)["units_sold"].sum() == raw_total
