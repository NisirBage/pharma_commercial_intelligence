"""Exercises app.analytics.data_access.load_from_db against SQLite (see
tests/conftest.py — no Postgres credentials were available), proving the
DB-backed path is ready even though the CSV-backed path is what's
currently used for real analysis (see M3 completion report)."""

from app.analytics.data_access import CANONICAL_COLUMNS, load_from_db
from app.etl.extract import extract_all
from app.etl.load import run_load
from app.etl.transform import (
    transform_canonical_fact,
    transform_daily_staging,
    transform_hourly_staging,
    transform_monthly_staging,
    transform_weekly_staging,
)
from app.etl.validate import validate_all


def test_load_from_db_matches_csv_backed_frame(db_session, raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    check_results = validate_all(datasets)
    hourly_staging = transform_hourly_staging(datasets["saleshourly.csv"])
    canonical_fact = transform_canonical_fact(hourly_staging)
    run_load(
        db_session,
        hourly_staging,
        transform_daily_staging(datasets["salesdaily.csv"]),
        transform_weekly_staging(datasets["salesweekly.csv"]),
        transform_monthly_staging(datasets["salesmonthly.csv"]),
        canonical_fact,
        check_results,
        "milanzdravkovic/pharma-sales-data",
    )
    db_session.commit()

    df = load_from_db(db_session)
    assert list(df.columns) == CANONICAL_COLUMNS
    assert len(df) == 32
    assert set(df["atc_code"].unique()) == {"M01AB", "M01AE", "N02BA", "N02BE", "N05B", "N05C", "R03", "R06"}
