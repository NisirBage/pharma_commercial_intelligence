"""Integration tests for app.etl.load, run against in-memory SQLite (see
tests/conftest.py — no Postgres credentials were available this milestone).
Exercises the full extract -> validate -> transform -> load path end to end."""

from sqlalchemy import func, select

from app.etl.extract import extract_all
from app.etl.load import load_canonical_fact, run_load, seed_atc_reference
from app.etl.reference_data import ATC_REFERENCE
from app.etl.transform import (
    transform_canonical_fact,
    transform_daily_staging,
    transform_hourly_staging,
    transform_monthly_staging,
    transform_weekly_staging,
)
from app.etl.validate import validate_all
from app.models.atc_class import AtcClass
from app.models.fact import FactDemandHourly
from app.models.staging import StgSalesDaily, StgSalesHourly, StgSalesMonthly, StgSalesWeekly


def _load_fixture(session, raw_fixture_dir):
    datasets = extract_all(raw_fixture_dir)
    check_results = validate_all(datasets)
    hourly_staging = transform_hourly_staging(datasets["saleshourly.csv"])
    daily_staging = transform_daily_staging(datasets["salesdaily.csv"])
    weekly_staging = transform_weekly_staging(datasets["salesweekly.csv"])
    monthly_staging = transform_monthly_staging(datasets["salesmonthly.csv"])
    canonical_fact = transform_canonical_fact(hourly_staging)
    return run_load(
        session,
        hourly_staging,
        daily_staging,
        weekly_staging,
        monthly_staging,
        canonical_fact,
        check_results,
        "milanzdravkovic/pharma-sales-data",
    )


def test_seed_atc_reference_inserts_all_8_and_is_idempotent(db_session):
    seed_atc_reference(db_session)
    db_session.flush()
    assert db_session.scalar(select(func.count()).select_from(AtcClass)) == len(ATC_REFERENCE)

    seed_atc_reference(db_session)  # run again — must not duplicate or error
    db_session.flush()
    assert db_session.scalar(select(func.count()).select_from(AtcClass)) == len(ATC_REFERENCE)


def test_full_load_produces_expected_row_counts(db_session, raw_fixture_dir):
    result = _load_fixture(db_session, raw_fixture_dir)
    db_session.commit()

    assert result.rows_loaded["stg_sales_hourly"] == 4
    assert result.rows_loaded["stg_sales_daily"] == 2
    assert result.rows_loaded["stg_sales_weekly"] == 1
    assert result.rows_loaded["stg_sales_monthly"] == 1
    assert result.rows_loaded["fact_demand_hourly"] == 4 * 8

    assert db_session.scalar(select(func.count()).select_from(StgSalesHourly)) == 4
    assert db_session.scalar(select(func.count()).select_from(StgSalesDaily)) == 2
    assert db_session.scalar(select(func.count()).select_from(StgSalesWeekly)) == 1
    assert db_session.scalar(select(func.count()).select_from(StgSalesMonthly)) == 1
    assert db_session.scalar(select(func.count()).select_from(FactDemandHourly)) == 32


def test_fact_rows_are_traceable_to_their_staging_row(db_session, raw_fixture_dir):
    """Every fact row must join back to a real stg_sales_hourly row with a
    matching observation_ts — this is the traceability the canonical model
    is designed around (see docs/data-model.md)."""
    _load_fixture(db_session, raw_fixture_dir)
    db_session.commit()

    rows = db_session.execute(
        select(FactDemandHourly.observation_ts, StgSalesHourly.observation_ts)
        .join(StgSalesHourly, FactDemandHourly.stg_sales_hourly_id == StgSalesHourly.id)
    ).all()
    assert len(rows) == 32
    for fact_ts, stg_ts in rows:
        assert fact_ts == stg_ts


def test_reload_is_idempotent_not_additive(db_session, raw_fixture_dir):
    """Running the pipeline twice against the same (unchanged) source data
    must not double the row counts — full-refresh, not append. This is the
    reproducibility property required by M2 point 6."""
    _load_fixture(db_session, raw_fixture_dir)
    db_session.commit()
    first_fact_count = db_session.scalar(select(func.count()).select_from(FactDemandHourly))

    _load_fixture(db_session, raw_fixture_dir)
    db_session.commit()
    second_fact_count = db_session.scalar(select(func.count()).select_from(FactDemandHourly))

    assert first_fact_count == second_fact_count == 32
    # dim_atc_class must also stay at 8, not be duplicated across runs
    assert db_session.scalar(select(func.count()).select_from(AtcClass)) == len(ATC_REFERENCE)


def test_load_canonical_fact_raises_if_staging_missing(db_session, raw_fixture_dir):
    """If canonical fact rows reference timestamps that were never staged,
    that must fail loudly rather than silently load orphaned/mismatched rows."""
    datasets = extract_all(raw_fixture_dir)
    hourly_staging = transform_hourly_staging(datasets["saleshourly.csv"])
    canonical_fact = transform_canonical_fact(hourly_staging)
    # Note: staging was never inserted this test — load_canonical_fact must
    # find zero matching ids and raise.
    try:
        load_canonical_fact(db_session, canonical_fact)
        assert False, "expected ValueError for unmatched staging rows"
    except ValueError as e:
        assert "could not be matched" in str(e)
