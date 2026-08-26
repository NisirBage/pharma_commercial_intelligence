"""Deep investigation of the `Hour` column anomaly flagged in M1.

salesdaily.csv's `Hour` column only takes 3 values (190, 248, 276), which is
not a valid hour-of-day. This script cross-references salesdaily against
saleshourly (the only other file with a genuine hour-of-day column) to test
every plausible hypothesis before docs/data-quality-decisions.md is written.
Findings are printed, not assumed.
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PRODUCT_COLS = ["M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"]


def load_daily() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "salesdaily.csv")
    df["date"] = pd.to_datetime(df["datum"], format="%m/%d/%Y")
    return df


def load_hourly() -> pd.DataFrame:
    df = pd.read_csv(RAW_DIR / "saleshourly.csv")
    df["timestamp"] = pd.to_datetime(df["datum"], format="%m/%d/%Y %H:%M")
    df["date"] = df["timestamp"].dt.normalize()
    return df


def main() -> None:
    daily = load_daily()
    hourly = load_hourly()

    print("### 1. Distribution of the anomalous Hour value in salesdaily")
    print(daily["Hour"].value_counts().sort_index())
    print()

    print("### 2. Does the Hour value correlate with Year / Month / Weekday?")
    print(pd.crosstab(daily["Hour"], daily["Year"]))
    print()
    print(pd.crosstab(daily["Hour"], daily["Weekday Name"]))
    print()

    print("### 3. Is Hour constant within a Year (i.e. changes only a few times across the whole series)?")
    transitions = daily[["date", "Hour"]].copy()
    transitions["changed"] = transitions["Hour"].ne(transitions["Hour"].shift())
    change_points = transitions[transitions["changed"]]
    print(change_points.to_string())
    print()

    print("### 4. Per-date aggregates from saleshourly, to compare against daily.Hour")
    per_day_hourly = (
        hourly.groupby("date")
        .agg(
            n_hourly_rows=("Hour", "count"),
            sum_hour_field=("Hour", "sum"),
            min_hour=("Hour", "min"),
            max_hour=("Hour", "max"),
            n_distinct_hours=("Hour", "nunique"),
        )
        .reset_index()
    )
    merged = daily.merge(per_day_hourly, on="date", how="left", suffixes=("_daily", "_hourly"))

    print("-- Does daily.Hour equal the count of hourly rows that day? --")
    print((merged["Hour"] == merged["n_hourly_rows"]).value_counts())

    print("-- Does daily.Hour equal the sum of the hourly Hour field that day? --")
    print((merged["Hour"] == merged["sum_hour_field"]).value_counts())

    print("-- Correlation of daily.Hour with n_hourly_rows / sum_hour_field --")
    print(merged[["Hour", "n_hourly_rows", "sum_hour_field"]].corr())
    print()

    print("### 5. Does daily.Hour correlate with total daily product quantity (sum across ATC columns)?")
    merged["daily_total_qty"] = merged[PRODUCT_COLS].sum(axis=1)
    print(merged[["Hour", "daily_total_qty"]].corr())
    print(merged.groupby("Hour")["daily_total_qty"].describe())
    print()

    print("### 6. Do dates missing from salesdaily exist in saleshourly, or vice versa (coverage check)?")
    daily_dates = set(daily["date"])
    hourly_dates = set(hourly["date"])
    print(f"daily-only dates: {len(daily_dates - hourly_dates)}")
    print(f"hourly-only dates: {len(hourly_dates - daily_dates)}")
    print(f"dates in both: {len(daily_dates & hourly_dates)}")
    print()

    print("### 7. Reconciliation check: does salesdaily == sum of saleshourly for the same date/product? (sanity, not part of Hour investigation)")
    hourly_daily_sum = hourly.groupby("date")[PRODUCT_COLS].sum().reset_index()
    recon = daily.merge(hourly_daily_sum, on="date", how="inner", suffixes=("_daily", "_hourly_sum"))
    for col in PRODUCT_COLS:
        diff = (recon[f"{col}_daily"] - recon[f"{col}_hourly_sum"]).abs()
        print(f"{col}: max abs diff = {diff.max():.4f}, mean abs diff = {diff.mean():.6f}, exact matches = {(diff < 1e-6).sum()}/{len(recon)}")


if __name__ == "__main__":
    main()
