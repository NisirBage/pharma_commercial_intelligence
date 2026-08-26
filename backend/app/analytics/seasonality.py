"""Seasonality analysis. Day-of-week and hour-of-day effects are tested
with the Kruskal-Wallis H-test (non-parametric — appropriate since demand
distributions are right-skewed/zero-heavy, not normal) rather than
asserted from a chart. Weekly/annual seasonality strength uses STL
decomposition (statsmodels), via the standard "strength of seasonality"
measure from Hyndman & Athanasopoulos, *Forecasting: Principles and
Practice*: strength = max(0, 1 - Var(residual) / Var(seasonal + residual)).

IMPORTANT: hour-of-day analysis uses `hour_of_day` from the canonical
frame, which is sourced from saleshourly.csv's real 0-23 hour column —
NEVER from salesdaily.csv's `Hour`, which M2 proved is an aggregation
artifact (docs/data-quality-decisions.md Decision 1), not an hour value.
"""

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from statsmodels.tsa.seasonal import STL

from app.analytics.aggregate import period_label, to_daily, to_monthly
from app.analytics.types import MetricResult

SIGNIFICANCE_ALPHA = 0.05


def _filter_entity(df: pd.DataFrame, entity: str | None) -> pd.DataFrame:
    return df if entity is None else df[df["atc_code"] == entity]


def day_of_week_effect(df: pd.DataFrame, entity: str | None = None) -> MetricResult:
    """Business question: does demand vary systematically by day of week?
    Formula: group daily total demand by weekday name; Kruskal-Wallis
    H-test across the (up to) 7 groups. H0: all weekdays are drawn from
    the same distribution. Grain: daily (rolled up from hourly)."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("day_of_week_effect", None, None, entity or "ALL", "daily", {"reason": "no_data"})

    daily = to_daily(frame, by_atc=False)
    daily["weekday"] = daily["observation_date"].dt.day_name()
    groups = {name: g["units_sold"].to_numpy() for name, g in daily.groupby("weekday")}
    if len(groups) < 2 or any(len(g) < 2 for g in groups.values()):
        return MetricResult(
            "day_of_week_effect", None, period_label(frame), entity or "ALL", "daily", {"reason": "insufficient_groups"}
        )

    h_stat, p_value = scipy_stats.kruskal(*groups.values())
    means = {name: float(g.mean()) for name, g in groups.items()}
    return MetricResult(
        "day_of_week_effect",
        float(h_stat),
        period_label(frame),
        entity or "ALL",
        "daily",
        {
            "p_value": float(p_value),
            "significant": bool(p_value < SIGNIFICANCE_ALPHA),
            "mean_units_by_weekday": means,
            "test": "kruskal-wallis",
            "alpha": SIGNIFICANCE_ALPHA,
        },
    )


def hour_of_day_effect(df: pd.DataFrame, entity: str | None = None) -> MetricResult:
    """Business question: does demand vary systematically by hour of day?
    Formula: group hourly observations by `hour_of_day` (0-23, from real
    hourly timestamps — see module docstring); Kruskal-Wallis H-test
    across the groups. Grain: hourly."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("hour_of_day_effect", None, None, entity or "ALL", "hourly", {"reason": "no_data"})

    groups = {int(h): g["units_sold"].to_numpy() for h, g in frame.groupby("hour_of_day")}
    if len(groups) < 2 or any(len(g) < 2 for g in groups.values()):
        return MetricResult(
            "hour_of_day_effect", None, period_label(frame), entity or "ALL", "hourly", {"reason": "insufficient_groups"}
        )

    h_stat, p_value = scipy_stats.kruskal(*groups.values())
    means = {h: float(g.mean()) for h, g in groups.items()}
    return MetricResult(
        "hour_of_day_effect",
        float(h_stat),
        period_label(frame),
        entity or "ALL",
        "hourly",
        {
            "p_value": float(p_value),
            "significant": bool(p_value < SIGNIFICANCE_ALPHA),
            "mean_units_by_hour": means,
            "test": "kruskal-wallis",
            "alpha": SIGNIFICANCE_ALPHA,
            "source": "saleshourly.csv hour_of_day (NOT salesdaily.csv's Hour artifact)",
        },
    )


def seasonal_strength(
    df: pd.DataFrame, entity: str | None = None, grain: str = "daily", period: int = 7
) -> MetricResult:
    """Business question: is there real, decomposable seasonality at this
    cycle length, or does an apparently-cyclical chart not hold up
    statistically? Formula: STL decomposition of the {grain} series with
    the given `period` (default 7 for weekly seasonality within a daily
    series; use period=12, grain='monthly' for annual seasonality);
    strength = max(0, 1 - Var(resid) / Var(seasonal + resid))
    (Hyndman & Athanasopoulos). 0 = no seasonal pattern; close to 1 = very
    strong, highly regular seasonal pattern.
    Limitation: requires at least 2 full cycles of history to fit at all —
    reported as `insufficient_periods` rather than a forced/unstable fit."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("seasonal_strength", None, None, entity or "ALL", grain, {"reason": "no_data"})

    if grain == "daily":
        rolled = to_daily(frame, by_atc=False).sort_values("observation_date")
        s = rolled.set_index("observation_date")["units_sold"]
    elif grain == "monthly":
        rolled = to_monthly(frame, by_atc=False).sort_values("month_start_date")
        s = rolled.set_index("month_start_date")["units_sold"]
    else:
        raise ValueError(f"unsupported grain for seasonal_strength: {grain!r} (use 'daily' or 'monthly')")

    if len(s) < period * 2:
        return MetricResult(
            "seasonal_strength",
            None,
            period_label(frame),
            entity or "ALL",
            grain,
            {"reason": "insufficient_periods", "n_periods": int(len(s)), "required_minimum": period * 2},
        )

    stl_result = STL(s, period=period, robust=True).fit()
    resid_var = float(np.var(stl_result.resid))
    seasonal_plus_resid_var = float(np.var(stl_result.seasonal + stl_result.resid))
    strength = max(0.0, 1 - resid_var / seasonal_plus_resid_var) if seasonal_plus_resid_var > 0 else 0.0

    return MetricResult(
        "seasonal_strength",
        float(strength),
        f"{s.index.min().date()}/{s.index.max().date()}",
        entity or "ALL",
        grain,
        {
            "cycle_period": period,
            "n_periods": int(len(s)),
            "method": "STL",
            "interpretation": "0 = no seasonality, ~1 = strong seasonality (Hyndman & Athanasopoulos)",
        },
    )
