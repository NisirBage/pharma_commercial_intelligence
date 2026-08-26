"""Leakage-safe feature engineering for the ML forecasting candidates
(app.forecasting.ml_models). Every lag/rolling feature for date `t` uses
ONLY information available up to and including date `t-1` — see
docs/forecasting-leakage-audit.md for the full, per-feature audit and the
automated leakage test in tests/unit/forecasting/test_features.py.
Calendar features are the one deliberate exception: they're derived from
the date itself, which is always known in advance for any future date, so
using them at date `t` is not leakage.
"""

import pandas as pd

DATE_COL = "observation_date"
TARGET_COL = "units_sold"

LAGS = (1, 7, 14, 28)
ROLLING_WINDOWS = (7, 14, 28)
ROLLING_STATS = ("mean", "median", "std", "min", "max")

FEATURE_COLUMNS = (
    [f"lag_{lag}" for lag in LAGS]
    + [f"rolling_{stat}_{w}" for w in ROLLING_WINDOWS for stat in ROLLING_STATS]
    + ["day_of_week", "day_of_month", "month", "week_of_year", "is_weekend"]
)

# Minimum trailing history required before the longest lag/rolling window
# has a non-NaN value.
MIN_WARMUP_DAYS = max(max(LAGS), max(ROLLING_WINDOWS))


def add_lag_features(df: pd.DataFrame, target_col: str = TARGET_COL, lags: tuple[int, ...] = LAGS) -> pd.DataFrame:
    df = df.copy()
    for lag in lags:
        df[f"lag_{lag}"] = df[target_col].shift(lag)
    return df


def add_rolling_features(
    df: pd.DataFrame, target_col: str = TARGET_COL, windows: tuple[int, ...] = ROLLING_WINDOWS
) -> pd.DataFrame:
    df = df.copy()
    # .shift(1) FIRST, then .rolling(): the window for date t covers
    # [t-w, t-1] — date t's own (unknown-at-prediction-time) value is
    # never included. This is the one line in the whole codebase where
    # getting the order wrong silently creates leakage — see the audit doc.
    shifted = df[target_col].shift(1)
    for w in windows:
        rolling = shifted.rolling(window=w, min_periods=w)
        df[f"rolling_mean_{w}"] = rolling.mean()
        df[f"rolling_median_{w}"] = rolling.median()
        df[f"rolling_std_{w}"] = rolling.std()
        df[f"rolling_min_{w}"] = rolling.min()
        df[f"rolling_max_{w}"] = rolling.max()
    return df


def add_calendar_features(df: pd.DataFrame, date_col: str = DATE_COL) -> pd.DataFrame:
    df = df.copy()
    d = df[date_col]
    df["day_of_week"] = d.dt.dayofweek
    df["day_of_month"] = d.dt.day
    df["month"] = d.dt.month
    df["week_of_year"] = d.dt.isocalendar().week.astype(int)
    df["is_weekend"] = (d.dt.dayofweek >= 5).astype(int)
    return df


def build_feature_frame(series_df: pd.DataFrame, target_col: str = TARGET_COL, date_col: str = DATE_COL) -> pd.DataFrame:
    """series_df: columns [date_col, target_col], one row per calendar day,
    strictly chronologically ordered (app.forecasting.datasets guarantees
    this). Returns the same frame with every feature column appended."""
    df = add_lag_features(series_df, target_col)
    df = add_rolling_features(df, target_col)
    df = add_calendar_features(df, date_col)
    return df


def make_training_table(
    feature_df: pd.DataFrame, target_col: str = TARGET_COL
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Drops rows with any NaN lag/rolling feature (insufficient warm-up
    history — the first MIN_WARMUP_DAYS rows of any series) — required
    before fitting a supervised model, since sklearn estimators reject
    NaN input."""
    feature_cols = [c for c in FEATURE_COLUMNS if c in feature_df.columns]
    clean = feature_df.dropna(subset=feature_cols)
    return clean[feature_cols], clean[target_col], feature_cols
