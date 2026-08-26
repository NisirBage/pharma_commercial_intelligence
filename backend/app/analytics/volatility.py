"""Demand volatility. Coefficient of variation (CV = std/mean) is the
primary cross-class comparison metric because it's scale-free — comparing
raw standard deviations across ATC classes with very different volumes
(e.g. N02BE vs N05C, whose total volumes differ by roughly an order of
magnitude — see docs/business-insights.md) would just rank the
highest-volume class as "most volatile" regardless of its actual
variability. Rolling std and IQR are provided for time-local and
outlier-robust views respectively.
"""

import pandas as pd

from app.analytics.aggregate import period_label, to_daily
from app.analytics.types import MetricResult


def _filter_entity(df: pd.DataFrame, entity: str | None) -> pd.DataFrame:
    return df if entity is None else df[df["atc_code"] == entity]


def coefficient_of_variation(df: pd.DataFrame, grain: str = "daily", entity: str | None = None) -> MetricResult:
    """Business question: how variable is demand relative to its own
    average, in a way that's comparable across classes of very different
    volume? Formula: CV = std(period totals) / mean(period totals).
    Limitation: undefined when mean is exactly 0 (an all-zero series) —
    reported via metadata reason, never returned as inf/NaN. Low-volume
    classes with many zero periods will mechanically show a higher CV;
    this is documented, not hidden (see docs/analytics-methodology.md)."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("coefficient_of_variation", None, None, entity or "ALL", grain, {"reason": "no_data"})

    if grain == "daily":
        rolled = to_daily(frame, by_atc=False)
        s = rolled["units_sold"]
    elif grain == "hourly":
        s = frame["units_sold"]
    else:
        raise ValueError(f"unsupported grain for coefficient_of_variation: {grain!r}")

    if len(s) < 2:
        return MetricResult(
            "coefficient_of_variation", None, period_label(frame), entity or "ALL", grain, {"reason": "insufficient_periods"}
        )
    mean = float(s.mean())
    if mean == 0:
        return MetricResult(
            "coefficient_of_variation",
            None,
            period_label(frame),
            entity or "ALL",
            grain,
            {"reason": "zero_mean", "std": float(s.std())},
        )
    cv = float(s.std() / mean)
    return MetricResult(
        "coefficient_of_variation",
        cv,
        period_label(frame),
        entity or "ALL",
        grain,
        {"mean": mean, "std": float(s.std()), "n_periods": int(len(s))},
    )


def rolling_std(df: pd.DataFrame, entity: str | None = None, window_days: int = 7) -> pd.DataFrame:
    """Business question: how has volatility itself changed over time
    (rather than a single number for the whole history)? Formula: rolling
    standard deviation of daily total demand over a `window_days`-day
    trailing window. Returns a DataFrame (observation_date, rolling_std),
    not a MetricResult, since it's an unavoidably time-indexed series
    meant for charting rather than a single number — used as an input to
    app.analytics.anomalies, not a standalone KPI."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return pd.DataFrame(columns=["observation_date", "rolling_std"])
    rolled = to_daily(frame, by_atc=False).sort_values("observation_date")
    rolled["rolling_std"] = rolled["units_sold"].rolling(window=window_days, min_periods=window_days).std()
    return rolled[["observation_date", "rolling_std"]]


def interquartile_range(df: pd.DataFrame, grain: str = "daily", entity: str | None = None) -> MetricResult:
    """Business question: what's the spread of "typical" demand, ignoring
    extreme outliers? Formula: IQR = Q3 - Q1 of period totals (25th/75th
    percentile). More outlier-robust than std, at the cost of ignoring the
    tails entirely — a real supply spike wouldn't move this number."""
    frame = _filter_entity(df, entity)
    if frame.empty:
        return MetricResult("interquartile_range", None, None, entity or "ALL", grain, {"reason": "no_data"})

    if grain == "daily":
        s = to_daily(frame, by_atc=False)["units_sold"]
    elif grain == "hourly":
        s = frame["units_sold"]
    else:
        raise ValueError(f"unsupported grain for interquartile_range: {grain!r}")

    if len(s) < 4:
        return MetricResult(
            "interquartile_range", None, period_label(frame), entity or "ALL", grain, {"reason": "insufficient_periods"}
        )
    q1, q3 = float(s.quantile(0.25)), float(s.quantile(0.75))
    return MetricResult(
        "interquartile_range",
        q3 - q1,
        period_label(frame),
        entity or "ALL",
        grain,
        {"q1": q1, "q3": q3, "n_periods": int(len(s))},
    )


def rank_by_volatility(df: pd.DataFrame, grain: str = "daily") -> list[MetricResult]:
    """All 8 ATC classes' CV, ranked most- to least-volatile. Classes with
    an undefined CV (zero-mean / insufficient data) are ranked last, not
    dropped, so the ranking is complete and auditable."""
    if df.empty:
        return []
    results = [coefficient_of_variation(df, grain=grain, entity=atc) for atc in sorted(df["atc_code"].unique())]
    return sorted(results, key=lambda m: (m.value is None, -(m.value or 0)))
