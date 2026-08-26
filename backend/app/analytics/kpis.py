"""Executive KPI layer.

Every function takes the canonical hourly frame (see
app.analytics.data_access — columns: atc_code, observation_ts, units_sold,
year, month, hour_of_day, weekday_name) and returns MetricResult(s).

Terminology: every number here is an observed **sales/demand volume**
(units sold, an integer-like quantity that happens to be stored as float
because the source data itself contains fractional values — see
docs/01-data-dictionary.md). None of it is revenue, profit, market share,
or prescription volume — the source dataset contains none of those, so
none of these functions claim to measure them. See
docs/analytics-methodology.md for the full write-up per metric.
"""

import pandas as pd

from app.analytics.aggregate import GRAIN_FUNCS, period_label
from app.analytics.types import MetricResult

_GRAIN_PERIOD_COL = {"daily": "observation_date", "weekly": "week_ending_date", "monthly": "month_start_date"}


def _period_series(frame: pd.DataFrame, grain: str) -> pd.Series:
    """One total-demand-across-all-ATC-classes value per period, at the
    requested grain. `grain='hourly'` uses the raw observation timestamps
    directly (no rollup); every other grain goes through
    app.analytics.aggregate, the single rollup path shared across the
    whole analytics layer."""
    if grain == "hourly":
        return frame.groupby("observation_ts")["units_sold"].sum().sort_index()
    if grain not in GRAIN_FUNCS:
        raise ValueError(f"unknown grain: {grain!r} (expected 'hourly', 'daily', 'weekly', or 'monthly')")
    rolled = GRAIN_FUNCS[grain](frame, by_atc=False)
    period_col = _GRAIN_PERIOD_COL[grain]
    return rolled.set_index(period_col)["units_sold"].sort_index()


def _filter_entity(df: pd.DataFrame, entity: str | None) -> pd.DataFrame:
    return df if entity is None else df[df["atc_code"] == entity]


def total_demand(df: pd.DataFrame, grain: str = "hourly", entity: str | None = None) -> MetricResult:
    """Business question: how much total volume was sold, overall or for
    one ATC class, across the observed history? Formula: SUM(units_sold).
    Grain-invariant by construction — summing at any grain yields the same
    total (conservation of volume across a rollup), which
    tests/unit/analytics/test_kpis.py checks explicitly."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("total_demand", 0.0, None, entity or "ALL", grain, {"n_observations": 0})
    return MetricResult(
        "total_demand",
        float(frame["units_sold"].sum()),
        period_label(frame),
        entity or "ALL",
        grain,
        {"n_observations": int(len(frame))},
    )


def average_demand(df: pd.DataFrame, grain: str = "hourly", entity: str | None = None) -> MetricResult:
    """Business question: what is typical demand per period (hour/day/week/
    month)? Formula: MEAN(period totals)."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("average_demand", None, None, entity or "ALL", grain, {"reason": "no_data"})
    s = _period_series(frame, grain)
    return MetricResult(
        "average_demand", float(s.mean()), period_label(frame), entity or "ALL", grain, {"n_periods": int(len(s))}
    )


def median_demand(df: pd.DataFrame, grain: str = "hourly", entity: str | None = None) -> MetricResult:
    """Business question: what's the typical period, robust to outlier
    spikes/troughs that would skew a mean? Formula: MEDIAN(period totals)."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("median_demand", None, None, entity or "ALL", grain, {"reason": "no_data"})
    s = _period_series(frame, grain)
    return MetricResult(
        "median_demand", float(s.median()), period_label(frame), entity or "ALL", grain, {"n_periods": int(len(s))}
    )


def peak_demand(df: pd.DataFrame, grain: str = "hourly", entity: str | None = None) -> MetricResult:
    """Business question: what was the single highest-demand period —
    relevant for capacity/supply planning. Formula: MAX(period totals);
    metadata carries which period it was."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("peak_demand", None, None, entity or "ALL", grain, {"reason": "no_data"})
    s = _period_series(frame, grain)
    return MetricResult(
        "peak_demand",
        float(s.max()),
        period_label(frame),
        entity or "ALL",
        grain,
        {"n_periods": int(len(s)), "peak_period": str(s.idxmax())},
    )


def min_demand(df: pd.DataFrame, grain: str = "hourly", entity: str | None = None) -> MetricResult:
    """Business question: what was the lowest-demand period (stockout risk
    read backwards: was there ever near-zero demand?). Formula: MIN(period
    totals); metadata carries which period it was."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("min_demand", None, None, entity or "ALL", grain, {"reason": "no_data"})
    s = _period_series(frame, grain)
    return MetricResult(
        "min_demand",
        float(s.min()),
        period_label(frame),
        entity or "ALL",
        grain,
        {"n_periods": int(len(s)), "min_period": str(s.idxmin())},
    )


def period_over_period_growth(
    df: pd.DataFrame, grain: str = "monthly", entity: str | None = None, periods_back: int = 1
) -> MetricResult:
    """Business question: is demand growing or shrinking, period to period?
    Formula: (latest_period_total - previous_period_total) / previous_period_total * 100.
    Limitation: undefined (returned as None, not a fabricated number) when
    the previous period's total is exactly 0, or when there isn't enough
    history to compare — both are reported via metadata rather than
    silently producing inf/NaN."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("period_over_period_growth", None, None, entity or "ALL", grain, {"reason": "no_data"})
    s = _period_series(frame, grain)
    if len(s) < periods_back + 1:
        return MetricResult(
            "period_over_period_growth",
            None,
            None,
            entity or "ALL",
            grain,
            {"reason": "insufficient_periods", "n_periods": int(len(s))},
        )
    latest, previous = s.iloc[-1], s.iloc[-1 - periods_back]
    period_str = f"{s.index[-1 - periods_back]}->{s.index[-1]}"
    if previous == 0:
        return MetricResult(
            "period_over_period_growth",
            None,
            period_str,
            entity or "ALL",
            grain,
            {"reason": "previous_period_zero", "latest": float(latest), "previous": float(previous)},
        )
    growth_pct = float((latest - previous) / previous * 100)
    return MetricResult(
        "period_over_period_growth",
        growth_pct,
        period_str,
        entity or "ALL",
        grain,
        {"latest": float(latest), "previous": float(previous)},
    )


def contribution_by_atc(df: pd.DataFrame) -> list[MetricResult]:
    """Business question: which ATC classes drive total observed demand?
    Formula: class_total / grand_total * 100, ranked descending. This is
    demand contribution WITHIN this dataset, not market share (the dataset
    has no information about a broader market)."""
    if df.empty:
        return []
    totals = df.groupby("atc_code")["units_sold"].sum()
    grand_total = float(totals.sum())
    period = period_label(df)
    results = []
    for atc, total in totals.sort_values(ascending=False).items():
        share = float(total / grand_total * 100) if grand_total > 0 else 0.0
        results.append(MetricResult("contribution_pct", share, period, atc, "overall", {"total_units": float(total)}))
    return results
