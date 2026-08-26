"""Long-term trend analysis. Uses OLS linear regression (scipy.stats.linregress)
against monthly-rolled-up demand (derived from the canonical hourly frame —
never from salesmonthly.csv, see docs/data-quality-decisions.md Decision 2)
so trend claims are backed by slope + p-value, not "the chart looks like
it's going up." See docs/analytics-methodology.md.
"""

import calendar

import numpy as np
import pandas as pd
from scipy import stats

from app.analytics.aggregate import to_monthly
from app.analytics.types import MetricResult

SIGNIFICANCE_ALPHA = 0.05


def _filter_entity(df: pd.DataFrame, entity: str | None) -> pd.DataFrame:
    return df if entity is None else df[df["atc_code"] == entity]


def linear_trend(df: pd.DataFrame, entity: str | None = None) -> MetricResult:
    """Business question: is there a statistically defensible long-term
    trend (growth or decline), or none detectable? Formula: OLS regression
    of monthly total demand against a monthly time index (0, 1, 2, ...).
    Classification requires BOTH a slope of the claimed sign AND p < 0.05
    — a slope alone is not treated as evidence of a trend.
    Limitation: linear regression assumes a roughly linear relationship;
    it will under-describe a series with strong curvature or regime
    changes — see app.analytics.anomalies for structural-change detection."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("trend_slope", None, None, entity or "ALL", "monthly", {"reason": "no_data"})

    rolled = to_monthly(frame, by_atc=False).sort_values("month_start_date").reset_index(drop=True)
    if len(rolled) < 3:
        return MetricResult(
            "trend_slope",
            None,
            None,
            entity or "ALL",
            "monthly",
            {"reason": "insufficient_periods", "n_periods": int(len(rolled))},
        )

    x = np.arange(len(rolled))
    y = rolled["units_sold"].to_numpy()
    slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

    if p_value < SIGNIFICANCE_ALPHA and slope > 0:
        classification = "growing"
    elif p_value < SIGNIFICANCE_ALPHA and slope < 0:
        classification = "declining"
    else:
        classification = "stable_or_no_significant_trend"

    period = f"{rolled['month_start_date'].min().date()}/{rolled['month_start_date'].max().date()}"
    return MetricResult(
        "trend_slope",
        float(slope),
        period,
        entity or "ALL",
        "monthly",
        {
            "r_squared": float(r_value**2),
            "p_value": float(p_value),
            "std_err": float(std_err),
            "n_periods": int(len(rolled)),
            "classification": classification,
            "alpha": SIGNIFICANCE_ALPHA,
        },
    )


def yearly_totals(df: pd.DataFrame, entity: str | None = None) -> list[MetricResult]:
    """Business question: which years had more/less total demand, and by
    how much year-over-year? Formula: SUM(units_sold) grouped by calendar
    year; YoY = (year_total - prior_year_total) / prior_year_total * 100.
    Limitation: the source data's first (2014, starts 2014-01-02) and last
    (2019, ends 2019-10-08) calendar years are PARTIAL — `is_complete_year`
    flags this explicitly so a YoY comparison touching either isn't
    misread as a full-year change."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return []

    frame = frame.copy()
    frame["year"] = frame["observation_ts"].dt.year
    yearly_total = frame.groupby("year")["units_sold"].sum().sort_index()
    n_days_observed = frame.groupby("year")["observation_ts"].apply(lambda s: s.dt.normalize().nunique())

    results: list[MetricResult] = []
    prev_total = None
    for year, total in yearly_total.items():
        expected_days = 366 if calendar.isleap(int(year)) else 365
        is_complete = bool(n_days_observed[year] >= expected_days - 2)
        yoy_growth_pct = None
        if prev_total is not None and prev_total != 0:
            yoy_growth_pct = float((total - prev_total) / prev_total * 100)
        results.append(
            MetricResult(
                "yearly_total_demand",
                float(total),
                str(year),
                entity or "ALL",
                "yearly",
                {
                    "yoy_growth_pct": yoy_growth_pct,
                    "n_days_observed": int(n_days_observed[year]),
                    "is_complete_year": is_complete,
                },
            )
        )
        prev_total = total
    return results
