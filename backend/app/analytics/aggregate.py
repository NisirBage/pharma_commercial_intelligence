"""Grain-rollup helpers. Every analytics module that needs daily/weekly/
monthly figures gets them from here — one aggregation path, computed from
the canonical hourly frame, matching the SQL views defined in the M2
migration (vw_demand_daily/weekly/monthly). This is what "do not mix
grains without an explicit, documented transformation" (M3 instructions
Sec. 2) means in code: nothing downstream does its own ad hoc groupby.
"""

import pandas as pd


def period_label(frame: pd.DataFrame) -> str | None:
    """Shared "start/end" label used across every analytics module's
    MetricResult.period field, so callers don't each reimplement it."""
    if frame.empty:
        return None
    start = frame["observation_ts"].min()
    end = frame["observation_ts"].max()
    return f"{start.date()}/{end.date()}"


def to_daily(df: pd.DataFrame, by_atc: bool = True) -> pd.DataFrame:
    """Grain: 1 row per (atc_code, calendar date). Matches vw_demand_daily."""
    d = df.copy()
    d["observation_date"] = d["observation_ts"].dt.normalize()
    group_cols = ["atc_code", "observation_date"] if by_atc else ["observation_date"]
    return d.groupby(group_cols, as_index=False)["units_sold"].sum()


def to_weekly(df: pd.DataFrame, by_atc: bool = True) -> pd.DataFrame:
    """Grain: 1 row per (atc_code, week_ending_date). Sunday-ending week,
    matching the convention verified in docs/data-quality-decisions.md
    Decision 2. Matches vw_demand_weekly."""
    d = df.copy()
    date = d["observation_ts"].dt.normalize()
    dow = date.dt.dayofweek  # Monday=0 ... Sunday=6
    days_to_sunday = (6 - dow) % 7
    d["week_ending_date"] = date + pd.to_timedelta(days_to_sunday, unit="D")
    group_cols = ["atc_code", "week_ending_date"] if by_atc else ["week_ending_date"]
    return d.groupby(group_cols, as_index=False)["units_sold"].sum()


def to_monthly(df: pd.DataFrame, by_atc: bool = True) -> pd.DataFrame:
    """Grain: 1 row per (atc_code, month_start_date). Derived ONLY from the
    canonical hourly fact table — NEVER from salesmonthly.csv, which M2
    found does not reconcile (61/560 cells, 33/70 months mismatched; see
    docs/data-quality-decisions.md Decision 2). Matches vw_demand_monthly,
    including its month-START convention (deliberately different from the
    source file's month-END convention, to avoid implying equivalence)."""
    d = df.copy()
    d["month_start_date"] = d["observation_ts"].values.astype("datetime64[M]")
    group_cols = ["atc_code", "month_start_date"] if by_atc else ["month_start_date"]
    return d.groupby(group_cols, as_index=False)["units_sold"].sum()


GRAIN_FUNCS = {"daily": to_daily, "weekly": to_weekly, "monthly": to_monthly}
