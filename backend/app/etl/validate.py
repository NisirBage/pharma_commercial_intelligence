"""Validation: schema, dtype, date, null, duplicate, value-range, and
cross-granularity checks against the raw extracted frames. Pure functions —
no DB, no side effects — so they're cheap to unit test and reusable by both
the pipeline and the data-quality report.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.etl.extract import DATE_FORMATS, RawDataset
from app.etl.reference_data import ATC_REFERENCE

PRODUCT_COLUMNS = list(ATC_REFERENCE.keys())  # ["M01AB", "M01AE", ...]
RECONCILIATION_TOLERANCE = 1e-6

EXPECTED_SCHEMA: dict[str, list[str]] = {
    "saleshourly.csv": ["datum", *PRODUCT_COLUMNS, "Year", "Month", "Hour", "Weekday Name"],
    "salesdaily.csv": ["datum", *PRODUCT_COLUMNS, "Year", "Month", "Hour", "Weekday Name"],
    "salesweekly.csv": ["datum", *PRODUCT_COLUMNS],
    "salesmonthly.csv": ["datum", *PRODUCT_COLUMNS],
}


@dataclass
class CheckResult:
    check_name: str
    file_name: str | None
    status: str  # "pass" | "fail" | "warn"
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _check_schema(ds: RawDataset) -> CheckResult:
    expected = set(EXPECTED_SCHEMA[ds.name])
    actual = set(ds.frame.columns)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    status = "pass" if not missing and not extra else "fail"
    return CheckResult(
        "schema_columns", ds.name, status, {"missing": missing, "extra": extra}
    )


def _check_dates_parse(ds: RawDataset) -> CheckResult:
    fmt = DATE_FORMATS[ds.name]
    parsed = pd.to_datetime(ds.frame["datum"], format=fmt, errors="coerce")
    n_failed = int(parsed.isna().sum())
    status = "pass" if n_failed == 0 else "fail"
    return CheckResult(
        "date_parse",
        ds.name,
        status,
        {"format": fmt, "n_failed": n_failed, "n_rows": len(ds.frame)},
    )


def _check_nulls(ds: RawDataset) -> CheckResult:
    null_counts = ds.frame.isnull().sum()
    nonzero = {col: int(n) for col, n in null_counts.items() if n > 0}
    status = "pass" if not nonzero else "fail"
    return CheckResult("null_values", ds.name, status, {"null_counts": nonzero})


def _check_duplicates(ds: RawDataset) -> CheckResult:
    dupes = ds.frame["datum"].duplicated().sum()
    status = "pass" if dupes == 0 else "fail"
    return CheckResult(
        "duplicate_datum", ds.name, status, {"n_duplicates": int(dupes)}
    )


def _check_numeric_ranges(ds: RawDataset) -> CheckResult:
    present_cols = [c for c in PRODUCT_COLUMNS if c in ds.frame.columns]
    negative_counts = {}
    for col in present_cols:
        n_negative = int((ds.frame[col] < 0).sum())
        if n_negative:
            negative_counts[col] = n_negative
    status = "pass" if not negative_counts else "fail"
    return CheckResult(
        "nonnegative_units_sold", ds.name, status, {"negative_counts": negative_counts}
    )


def _check_hourly_hour_range(ds: RawDataset) -> CheckResult:
    """Only meaningful for saleshourly.csv — the only file where `Hour` is a
    genuine hour-of-day. See docs/data-quality-decisions.md for why
    salesdaily.csv's `Hour` is intentionally NOT range-checked here."""
    if ds.name != "saleshourly.csv":
        return CheckResult("hour_of_day_range", ds.name, "pass", {"skipped": "not applicable"})
    out_of_range = int(((ds.frame["Hour"] < 0) | (ds.frame["Hour"] > 23)).sum())
    status = "pass" if out_of_range == 0 else "fail"
    return CheckResult("hour_of_day_range", ds.name, status, {"n_out_of_range": out_of_range})


def _check_daily_hour_artifact_formula(datasets: dict[str, RawDataset]) -> CheckResult:
    """Confirms salesdaily.Hour == sum(saleshourly.Hour) per date, the exact
    mechanism documented as Decision 1. A regression here would mean the
    dataset changed and the documented explanation needs re-verification."""
    hourly = datasets["saleshourly.csv"].frame.copy()
    daily = datasets["salesdaily.csv"].frame.copy()

    hourly["ts"] = pd.to_datetime(hourly["datum"], format=DATE_FORMATS["saleshourly.csv"])
    hourly["date"] = hourly["ts"].dt.normalize()
    daily["date"] = pd.to_datetime(daily["datum"], format=DATE_FORMATS["salesdaily.csv"])

    hour_sums = hourly.groupby("date")["Hour"].sum().rename("expected_hour_sum")
    merged = daily.merge(hour_sums, on="date", how="left")
    mismatches = merged[merged["Hour"] != merged["expected_hour_sum"]]

    status = "pass" if mismatches.empty else "fail"
    return CheckResult(
        "daily_hour_artifact_formula",
        "salesdaily.csv",
        status,
        {"n_mismatches": int(len(mismatches)), "n_rows": int(len(merged))},
    )


def _check_cross_grain_reconciliation(datasets: dict[str, RawDataset]) -> list[CheckResult]:
    """Sum-up checks: daily==sum(hourly), weekly==sum(daily 7d Sun-ending),
    monthly==sum(daily calendar month). Per docs/data-quality-decisions.md,
    the first two are expected to PASS; monthly is EXPECTED to FAIL (known,
    documented, unfixable source defect) — its status is reported as "warn",
    not "fail", so pipeline runs don't treat a known, already-investigated
    issue as a new failure."""
    results: list[CheckResult] = []

    hourly = datasets["saleshourly.csv"].frame.copy()
    daily = datasets["salesdaily.csv"].frame.copy()
    weekly = datasets["salesweekly.csv"].frame.copy()
    monthly = datasets["salesmonthly.csv"].frame.copy()

    hourly["ts"] = pd.to_datetime(hourly["datum"], format=DATE_FORMATS["saleshourly.csv"])
    hourly["date"] = hourly["ts"].dt.normalize()
    daily["date"] = pd.to_datetime(daily["datum"], format=DATE_FORMATS["salesdaily.csv"])
    weekly["date"] = pd.to_datetime(weekly["datum"], format=DATE_FORMATS["salesweekly.csv"])
    monthly["date"] = pd.to_datetime(monthly["datum"], format=DATE_FORMATS["salesmonthly.csv"])

    daily_idx = daily.set_index("date").sort_index()

    # daily vs hourly
    hourly_sum = hourly.groupby("date")[PRODUCT_COLUMNS].sum()
    d_merged = daily.merge(hourly_sum, on="date", how="left", suffixes=("", "_hourly_sum"))
    n_mismatch = 0
    for col in PRODUCT_COLUMNS:
        n_mismatch += int((d_merged[col] - d_merged[f"{col}_hourly_sum"]).abs().gt(RECONCILIATION_TOLERANCE).sum())
    results.append(
        CheckResult(
            "reconciliation_daily_vs_hourly",
            "salesdaily.csv",
            "pass" if n_mismatch == 0 else "fail",
            {"n_cell_mismatches": n_mismatch},
        )
    )

    # weekly vs daily (trailing 7d, Sunday-ending)
    n_mismatch = 0
    for _, row in weekly.iterrows():
        end, start = row["date"], row["date"] - pd.Timedelta(days=6)
        window = daily_idx.loc[start:end, PRODUCT_COLUMNS].sum()
        for col in PRODUCT_COLUMNS:
            if abs(window[col] - row[col]) > RECONCILIATION_TOLERANCE:
                n_mismatch += 1
    results.append(
        CheckResult(
            "reconciliation_weekly_vs_daily",
            "salesweekly.csv",
            "pass" if n_mismatch == 0 else "fail",
            {"n_cell_mismatches": n_mismatch},
        )
    )

    # monthly vs daily (calendar month) — EXPECTED to fail, reported as warn
    n_mismatch = 0
    affected_periods: set[str] = set()
    for _, row in monthly.iterrows():
        period = row["date"].to_period("M")
        window = daily_idx[daily_idx.index.to_period("M") == period][PRODUCT_COLUMNS].sum()
        for col in PRODUCT_COLUMNS:
            if abs(window[col] - row[col]) > RECONCILIATION_TOLERANCE:
                n_mismatch += 1
                affected_periods.add(str(period))
    results.append(
        CheckResult(
            "reconciliation_monthly_vs_daily",
            "salesmonthly.csv",
            "warn" if n_mismatch else "pass",
            {
                "n_cell_mismatches": n_mismatch,
                "n_affected_months": len(affected_periods),
                "note": "Known unreconciled source file — see docs/data-quality-decisions.md Decision 2. "
                "Excluded from canonical model; loaded to staging for audit only.",
            },
        )
    )
    return results


# Public alias — reused by app.analytics.reconciliation (M3) as an ongoing
# analytical quality-control check, not just a one-time ETL validation step.
check_cross_grain_reconciliation = _check_cross_grain_reconciliation


def validate_all(datasets: dict[str, RawDataset]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for ds in datasets.values():
        results.append(_check_schema(ds))
        results.append(_check_dates_parse(ds))
        results.append(_check_nulls(ds))
        results.append(_check_duplicates(ds))
        results.append(_check_numeric_ranges(ds))
        results.append(_check_hourly_hour_range(ds))

    results.append(_check_daily_hour_artifact_formula(datasets))
    results.extend(_check_cross_grain_reconciliation(datasets))
    return results


def has_blocking_failures(results: list[CheckResult]) -> bool:
    """"warn" (the known monthly reconciliation issue) never blocks the
    pipeline; any "fail" does — it means something changed or was missed."""
    return any(r.status == "fail" for r in results)
