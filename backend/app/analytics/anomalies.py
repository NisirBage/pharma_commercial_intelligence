"""Explainable anomaly detection and structural-change screening.

Two independent, transparent statistical anomaly methods, applied per ATC
class to the daily-grain series (derived from the canonical hourly fact
table — never salesmonthly.csv):

  Method A/B — rolling mean + rolling std z-score:
      z = (observed - rolling_mean) / rolling_std, computed from a
      trailing window of STRICTLY PRIOR days (the day being evaluated is
      always excluded from its own baseline — no look-ahead/future
      leakage). Flagged at |z| >= Z_MEDIUM; severity escalates at
      |z| >= Z_HIGH. Conventional 2-sigma/3-sigma bands, not tuned to
      this dataset.

  Method C — IQR (Tukey fence) on the same trailing window.

Deliberately NOT Isolation Forest or other ML — M3 explicitly calls for a
transparent baseline first.

An anomaly is never labeled with a business cause (supply disruption,
marketing campaign, epidemic, competitor action, product launch) — the
dataset contains no corroborating evidence for any of those. Every result
is reported as exactly what it is: an observed statistical deviation from
the series' own recent history. See docs/business-insights.md for the
Observed / Analytical finding / Hypothesis / Recommendation framing this
feeds into.
"""

import pandas as pd
from scipy import stats as scipy_stats

from app.analytics.aggregate import to_daily, to_monthly
from app.analytics.types import AnomalyResult, MetricResult

Z_MEDIUM = 2.0
Z_HIGH = 3.0
ROLLING_WINDOW_DAYS = 30
MIN_HISTORY_DAYS = ROLLING_WINDOW_DAYS + 1
IQR_MULTIPLIER = 1.5
MIN_CHANGE_POINT_SEGMENT = 3


def _zscore_severity(z_abs: float) -> str:
    if z_abs >= Z_HIGH:
        return "high"
    if z_abs >= Z_MEDIUM:
        return "medium"
    return "low"


def _iqr_severity(fence_distance_in_iqr_units: float) -> str:
    if fence_distance_in_iqr_units >= 1.5:
        return "high"
    if fence_distance_in_iqr_units >= 0.5:
        return "medium"
    return "low"


def detect_rolling_zscore(
    df: pd.DataFrame, entity: str, window_days: int = ROLLING_WINDOW_DAYS, z_threshold: float = Z_MEDIUM
) -> list[AnomalyResult]:
    frame = df[df["atc_code"] == entity]
    if frame.empty:
        return []
    daily = to_daily(frame, by_atc=False).sort_values("observation_date").reset_index(drop=True)
    if len(daily) < MIN_HISTORY_DAYS:
        return []

    s = daily["units_sold"]
    # .shift(1) guarantees the rolling window covers only days strictly
    # before the one being scored.
    rolling_mean = s.shift(1).rolling(window=window_days, min_periods=window_days).mean()
    rolling_std = s.shift(1).rolling(window=window_days, min_periods=window_days).std()

    results: list[AnomalyResult] = []
    for i in range(len(daily)):
        mean_i, std_i = rolling_mean.iloc[i], rolling_std.iloc[i]
        if pd.isna(mean_i) or pd.isna(std_i) or std_i == 0:
            # Either insufficient history yet, or a zero-variance baseline
            # (a perfectly flat run of prior days) — this method cannot
            # compute a meaningful z-score in either case. Documented
            # limitation, not silently approximated.
            continue
        observed = float(s.iloc[i])
        z = (observed - mean_i) / std_i
        if abs(z) < z_threshold:
            continue
        deviation_pct = float((observed - mean_i) / mean_i * 100) if mean_i != 0 else float("inf")
        results.append(
            AnomalyResult(
                atc_class=entity,
                timestamp=str(daily["observation_date"].iloc[i].date()),
                observed=observed,
                expected=float(mean_i),
                deviation_pct=deviation_pct,
                anomaly_score=float(z),
                direction="above" if z > 0 else "below",
                severity=_zscore_severity(abs(z)),
                method="rolling_zscore",
                metadata={"window_days": window_days, "rolling_std": float(std_i)},
            )
        )
    return results


def detect_iqr(
    df: pd.DataFrame, entity: str, window_days: int = ROLLING_WINDOW_DAYS, multiplier: float = IQR_MULTIPLIER
) -> list[AnomalyResult]:
    frame = df[df["atc_code"] == entity]
    if frame.empty:
        return []
    daily = to_daily(frame, by_atc=False).sort_values("observation_date").reset_index(drop=True)
    if len(daily) < MIN_HISTORY_DAYS:
        return []

    s = daily["units_sold"]
    results: list[AnomalyResult] = []
    for i in range(len(daily)):
        window = s.iloc[max(0, i - window_days) : i]  # strictly prior days only
        if len(window) < window_days:
            continue
        q1, q3 = window.quantile(0.25), window.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower, upper = q1 - multiplier * iqr, q3 + multiplier * iqr
        observed = float(s.iloc[i])
        if lower <= observed <= upper:
            continue
        median = float(window.median())
        deviation_pct = float((observed - median) / median * 100) if median != 0 else float("inf")
        fence_distance = (observed - upper) if observed > upper else (lower - observed)
        score = float(fence_distance / iqr)
        results.append(
            AnomalyResult(
                atc_class=entity,
                timestamp=str(daily["observation_date"].iloc[i].date()),
                observed=observed,
                expected=median,
                deviation_pct=deviation_pct,
                anomaly_score=score,
                direction="above" if observed > upper else "below",
                severity=_iqr_severity(score),
                method="iqr",
                metadata={"window_days": window_days, "q1": float(q1), "q3": float(q3), "iqr": float(iqr), "multiplier": multiplier},
            )
        )
    return results


def detect_anomalies(df: pd.DataFrame, methods: tuple[str, ...] = ("rolling_zscore", "iqr")) -> list[AnomalyResult]:
    """Runs the requested method(s) across every ATC class present."""
    if df.empty:
        return []
    results: list[AnomalyResult] = []
    for atc in sorted(df["atc_code"].unique()):
        if "rolling_zscore" in methods:
            results.extend(detect_rolling_zscore(df, atc))
        if "iqr" in methods:
            results.extend(detect_iqr(df, atc))
    return results


def detect_mean_shift(df: pd.DataFrame, entity: str | None = None, grain: str = "monthly") -> MetricResult:
    """Business question: did the overall LEVEL of demand shift at some
    point in history (a structural change), as distinct from a continuous
    trend or a short-lived anomaly? Method: grid search over every
    candidate split point in the {grain} series; Welch's t-test between
    the "before" and "after" segments at each split; report the split
    with the largest |t-statistic| as the candidate change point.

    This is a STATISTICAL candidate change point only — it identifies
    WHERE the series' mean level differs before vs. after a date. It does
    NOT identify WHY; this dataset contains no external-event data that
    could explain a cause (see docs/business-insights.md).

    Limitation: grid-searching many candidate splits and reporting only
    the best one is a multiple-comparisons problem — the reported p-value
    is NOT corrected for this and should be read as indicative screening,
    not a rigorous hypothesis test."""
    frame = df if entity is None else df[df["atc_code"] == entity]
    if frame.empty:
        return MetricResult("mean_shift_candidate", None, None, entity or "ALL", grain, {"reason": "no_data"})

    if grain == "monthly":
        rolled = to_monthly(frame, by_atc=False).sort_values("month_start_date").reset_index(drop=True)
        period_col = "month_start_date"
    elif grain == "daily":
        rolled = to_daily(frame, by_atc=False).sort_values("observation_date").reset_index(drop=True)
        period_col = "observation_date"
    else:
        raise ValueError(f"unsupported grain for detect_mean_shift: {grain!r} (use 'monthly' or 'daily')")

    n = len(rolled)
    if n < MIN_CHANGE_POINT_SEGMENT * 2:
        return MetricResult(
            "mean_shift_candidate", None, None, entity or "ALL", grain, {"reason": "insufficient_periods", "n_periods": n}
        )

    values = rolled["units_sold"].to_numpy()
    best_t, best_p, best_idx = 0.0, 1.0, None
    for split in range(MIN_CHANGE_POINT_SEGMENT, n - MIN_CHANGE_POINT_SEGMENT + 1):
        before, after = values[:split], values[split:]
        t_stat, p_val = scipy_stats.ttest_ind(before, after, equal_var=False)
        if abs(t_stat) > abs(best_t):
            best_t, best_p, best_idx = float(t_stat), float(p_val), split

    if best_idx is None:
        return MetricResult(
            "mean_shift_candidate", None, None, entity or "ALL", grain, {"reason": "no_candidate_found", "n_periods": n}
        )

    split_period = str(rolled[period_col].iloc[best_idx])
    return MetricResult(
        "mean_shift_candidate",
        best_t,
        split_period,
        entity or "ALL",
        grain,
        {
            "p_value_uncorrected": best_p,
            "n_periods": n,
            "split_index": best_idx,
            "mean_before": float(values[:best_idx].mean()),
            "mean_after": float(values[best_idx:].mean()),
            "note": "Statistical candidate change point (grid-search t-test, p-value NOT multiple-comparisons "
            "corrected). Does not imply a business cause.",
        },
    )
