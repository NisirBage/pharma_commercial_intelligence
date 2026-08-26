import pandas as pd

from app.analytics import atc_analysis
from tests.unit.analytics.helpers import daily_series_frame, make_frame


def _two_class_frame():
    return pd.concat(
        [
            daily_series_frame("M01AB", "2020-01-01", [90] * 10),  # dominant class
            daily_series_frame("N05B", "2020-01-01", [10] * 10),
        ]
    )


def test_build_atc_profiles_covers_every_class_present():
    frame = _two_class_frame()
    profiles = atc_analysis.build_atc_profiles(frame)
    codes = {p["atc_code"] for p in profiles}
    assert codes == {"M01AB", "N05B"}
    m01ab = next(p for p in profiles if p["atc_code"] == "M01AB")
    assert m01ab["total_demand"].value == 900.0
    assert m01ab["contribution"].value == 90.0


def test_build_atc_profiles_empty_dataset():
    assert atc_analysis.build_atc_profiles(make_frame([])) == []


def test_classify_by_trend_buckets_growing_and_flat_classes():
    # 152 days from 2020-01-01 = exactly 5 complete calendar months (Jan-May,
    # 2020 being a leap year) — avoids a partial trailing month distorting
    # the monthly-grain trend regression with a low-total final point.
    growing_values = [10 + i for i in range(152)]  # clear upward ramp
    flat_values = [50, 40] * 76  # oscillating, no net trend
    frame = pd.concat(
        [
            daily_series_frame("M01AB", "2020-01-01", growing_values),
            daily_series_frame("N05B", "2020-01-01", flat_values),
        ]
    )
    profiles = atc_analysis.build_atc_profiles(frame)
    buckets = atc_analysis.classify_by_trend(profiles)
    assert "M01AB" in buckets.get("growing", [])
    assert "N05B" not in buckets.get("growing", [])


def test_rank_by_contribution_orders_descending():
    frame = _two_class_frame()
    profiles = atc_analysis.build_atc_profiles(frame)
    ranked = atc_analysis.rank_by_contribution(profiles)
    assert [p["atc_code"] for p in ranked] == ["M01AB", "N05B"]


def test_demand_concentration_two_class_split():
    frame = _two_class_frame()  # 90/10 split
    result = atc_analysis.demand_concentration(frame)
    ranked = {r["atc_code"]: r for r in result["ranked"]}
    assert abs(ranked["M01AB"]["share_pct"] - 90.0) < 1e-9
    assert abs(ranked["M01AB"]["cumulative_share_pct"] - 90.0) < 1e-9
    assert abs(ranked["N05B"]["cumulative_share_pct"] - 100.0) < 1e-9
    # HHI = 90^2 + 10^2 = 8200
    assert abs(result["hhi"] - 8200.0) < 1e-6
    # only 2 classes exist, so CR3 (top 3) == 100% of total
    assert abs(result["concentration_ratio_top3_pct"] - 100.0) < 1e-9


def test_demand_concentration_empty_dataset():
    result = atc_analysis.demand_concentration(make_frame([]))
    assert result["reason"] == "no_data"
