import pandas as pd

from app.forecasting.datasets import build_all_series, build_daily_series


def _canonical_frame(rows):
    df = pd.DataFrame(rows)
    df["observation_ts"] = pd.to_datetime(df["observation_ts"])
    return df


def test_build_daily_series_is_chronologically_ordered():
    frame = _canonical_frame(
        [
            {"atc_code": "M01AB", "observation_ts": "2020-01-03 08:00", "units_sold": 3.0},
            {"atc_code": "M01AB", "observation_ts": "2020-01-01 08:00", "units_sold": 1.0},
            {"atc_code": "M01AB", "observation_ts": "2020-01-02 08:00", "units_sold": 2.0},
        ]
    )
    result = build_daily_series(frame, "M01AB")
    assert result.frame["observation_date"].is_monotonic_increasing
    assert result.frame["units_sold"].tolist() == [1.0, 2.0, 3.0]


def test_build_daily_series_fills_missing_calendar_dates_with_zero():
    frame = _canonical_frame(
        [
            {"atc_code": "M01AB", "observation_ts": "2020-01-01 08:00", "units_sold": 1.0},
            # 2020-01-02 entirely absent from the source
            {"atc_code": "M01AB", "observation_ts": "2020-01-03 08:00", "units_sold": 3.0},
        ]
    )
    result = build_daily_series(frame, "M01AB")
    assert result.n_days == 3
    assert result.missing_dates_filled == ["2020-01-02"]
    assert result.frame.set_index("observation_date").loc[pd.Timestamp("2020-01-02"), "units_sold"] == 0.0


def test_build_daily_series_no_missing_dates_reports_empty_list():
    frame = _canonical_frame(
        [
            {"atc_code": "M01AB", "observation_ts": "2020-01-01 08:00", "units_sold": 1.0},
            {"atc_code": "M01AB", "observation_ts": "2020-01-02 08:00", "units_sold": 2.0},
        ]
    )
    result = build_daily_series(frame, "M01AB")
    assert result.missing_dates_filled == []
    assert result.duplicate_dates_found == 0


def test_build_daily_series_aggregate_sums_across_atc_classes():
    frame = _canonical_frame(
        [
            {"atc_code": "M01AB", "observation_ts": "2020-01-01 08:00", "units_sold": 1.0},
            {"atc_code": "N05B", "observation_ts": "2020-01-01 09:00", "units_sold": 10.0},
        ]
    )
    result = build_daily_series(frame, "ALL")
    assert result.frame["units_sold"].iloc[0] == 11.0


def test_build_all_series_covers_every_atc_class_plus_aggregate():
    frame = _canonical_frame(
        [
            {"atc_code": "M01AB", "observation_ts": "2020-01-01 08:00", "units_sold": 1.0},
            {"atc_code": "N05B", "observation_ts": "2020-01-01 09:00", "units_sold": 10.0},
        ]
    )
    results = build_all_series(frame)
    assert set(results.keys()) == {"ALL", "M01AB", "N05B"}
    assert results["ALL"].frame["units_sold"].iloc[0] == 11.0
    assert results["M01AB"].frame["units_sold"].iloc[0] == 1.0
