import pandas as pd
import pytest

from app.etl.extract import RawDataset, extract_all
from app.etl.validate import has_blocking_failures, validate_all


@pytest.fixture
def datasets(raw_fixture_dir):
    return extract_all(raw_fixture_dir)


def _result(results, check_name, file_name):
    matches = [r for r in results if r.check_name == check_name and r.file_name == file_name]
    assert matches, f"no result for {check_name}/{file_name}"
    return matches[0]


def test_clean_fixture_passes_schema_date_null_duplicate_range_checks(datasets):
    results = validate_all(datasets)
    for check in ("schema_columns", "date_parse", "null_values", "duplicate_datum", "nonnegative_units_sold"):
        for file_name in datasets:
            assert _result(results, check, file_name).status == "pass", f"{check}/{file_name} unexpectedly failed"


def test_hourly_hour_range_check_passes_and_is_skipped_for_other_files(datasets):
    results = validate_all(datasets)
    assert _result(results, "hour_of_day_range", "saleshourly.csv").status == "pass"
    for other in ("salesdaily.csv", "salesweekly.csv", "salesmonthly.csv"):
        r = _result(results, "hour_of_day_range", other)
        assert r.status == "pass"
        assert r.details.get("skipped") == "not applicable"


def test_daily_hour_artifact_formula_confirmed_on_fixture(datasets):
    """Fixture was hand-built so daily.Hour == sum(hourly.Hour) for both
    days (17 = 8+9 in both cases) — this is the exact formula documented in
    docs/data-quality-decisions.md Decision 1."""
    results = validate_all(datasets)
    r = _result(results, "daily_hour_artifact_formula", "salesdaily.csv")
    assert r.status == "pass"
    assert r.details["n_mismatches"] == 0


def test_daily_vs_hourly_and_weekly_vs_daily_reconcile_exactly(datasets):
    results = validate_all(datasets)
    assert _result(results, "reconciliation_daily_vs_hourly", "salesdaily.csv").status == "pass"
    assert _result(results, "reconciliation_weekly_vs_daily", "salesweekly.csv").status == "pass"


def test_monthly_reconciliation_catches_the_deliberate_fixture_mismatch(datasets):
    """The fixture's salesmonthly.csv deliberately sets M01AB=999 instead of
    the correct 2 (matching the real dataset's Decision 2 pattern of
    monthly not reconciling) — this must be caught as a "warn", not
    silently passed and not a blocking "fail"."""
    results = validate_all(datasets)
    r = _result(results, "reconciliation_monthly_vs_daily", "salesmonthly.csv")
    assert r.status == "warn"
    assert r.details["n_cell_mismatches"] == 1
    assert not has_blocking_failures(results)


def test_schema_check_fails_on_missing_column():
    from app.etl.validate import _check_schema

    frame = pd.DataFrame({"datum": ["1/1/2020"], "M01AB": [1.0]})  # missing most columns
    ds = RawDataset(name="salesdaily.csv", path=None, frame=frame)
    result = _check_schema(ds)
    assert result.status == "fail"
    assert "M01AE" in result.details["missing"]


def test_null_check_fails_on_nulls():
    from app.etl.validate import _check_nulls

    frame = pd.DataFrame({"datum": ["1/1/2020", None], "M01AB": [1.0, 2.0]})
    ds = RawDataset(name="salesdaily.csv", path=None, frame=frame)
    result = _check_nulls(ds)
    assert result.status == "fail"
    assert result.details["null_counts"]["datum"] == 1


def test_nonnegative_check_fails_on_negative_units():
    from app.etl.validate import _check_numeric_ranges

    frame = pd.DataFrame({"M01AB": [1.0, -5.0], "M01AE": [0.0, 0.0]})
    ds = RawDataset(name="salesdaily.csv", path=None, frame=frame)
    result = _check_numeric_ranges(ds)
    assert result.status == "fail"
    assert result.details["negative_counts"]["M01AB"] == 1
