"""Synthetic canonical-frame builders shared across the analytics test
suite. Deterministic (no randomness) so statistical-test assertions
(Kruskal-Wallis significance, trend p-values, etc.) never flake."""

import pandas as pd


def make_frame(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=["atc_code", "observation_ts", "units_sold", "year", "month", "hour_of_day", "weekday_name"]
        )
    df = pd.DataFrame(rows)
    df["observation_ts"] = pd.to_datetime(df["observation_ts"])
    df["year"] = df["observation_ts"].dt.year
    df["month"] = df["observation_ts"].dt.month
    df["hour_of_day"] = df["observation_ts"].dt.hour
    df["weekday_name"] = df["observation_ts"].dt.day_name()
    return df[["atc_code", "observation_ts", "units_sold", "year", "month", "hour_of_day", "weekday_name"]]


def daily_series_frame(atc_code: str, start_date: str, values: list[float], hour: int = 12) -> pd.DataFrame:
    """One synthetic hourly-row-per-day, so to_daily() rollups reproduce
    `values` exactly — a compact stand-in for real 24-hour-per-day data
    when a test only cares about daily totals."""
    dates = pd.date_range(start=start_date, periods=len(values), freq="D")
    rows = [
        {"atc_code": atc_code, "observation_ts": d + pd.Timedelta(hours=hour), "units_sold": v}
        for d, v in zip(dates, values)
    ]
    return make_frame(rows)


def hourly_pattern_frame(atc_code: str, n_days: int, hour_values: dict[int, float], start_date: str = "2020-01-06") -> pd.DataFrame:
    """`n_days` consecutive days, each with one row per hour in
    `hour_values` (hour_of_day -> units_sold), repeated identically every
    day — a strong, deterministic diurnal pattern for hour-of-day tests.
    start_date defaults to a Monday (2020-01-06) so weekday-derived tests
    built on top of it are also deterministic."""
    dates = pd.date_range(start=start_date, periods=n_days, freq="D")
    rows = []
    for d in dates:
        for hour, value in hour_values.items():
            rows.append({"atc_code": atc_code, "observation_ts": d + pd.Timedelta(hours=hour), "units_sold": value})
    return make_frame(rows)
