"""Pipeline entrypoint: extract -> validate -> transform -> load, writing a
data-quality report at the end either way.

Usage (from backend/):
    python -m app.etl.run_pipeline

Reads configuration (DB connection, raw data dir) from app.core.config —
nothing here is machine-specific. Requires the raw CSVs to already exist
locally (run scripts/download_data.py from the project root first) and a
reachable Postgres instance per DATABASE_URL / POSTGRES_* env vars.
"""

import sys
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import make_engine, make_session_factory
from app.etl.extract import extract_all
from app.etl.load import persist_quality_checks, run_load
from app.etl.quality_report import build_report, write_report
from app.etl.transform import (
    transform_canonical_fact,
    transform_daily_staging,
    transform_hourly_staging,
    transform_monthly_staging,
    transform_weekly_staging,
)
from app.etl.validate import has_blocking_failures, validate_all
from app.models.etl_run import EtlRun


def run(session: Session) -> int:
    print(f"Extracting raw CSVs from {settings.raw_data_dir} ...")
    datasets = extract_all()

    print("Validating ...")
    check_results = validate_all(datasets)
    for r in check_results:
        print(f"  [{r.status.upper():4}] {r.check_name} ({r.file_name}) {r.details}")

    report = build_report(datasets, check_results, settings.kaggle_dataset_id)
    report_path = write_report(report, settings.quality_report_dir)
    print(f"Quality report written to {report_path}")

    if has_blocking_failures(check_results):
        print("BLOCKING validation failures found — aborting load without writing to the database.")
        failed_run = EtlRun(
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            status="failed",
            source_dataset_identifier=settings.kaggle_dataset_id,
            notes="Aborted before load: blocking validation failures. See quality report.",
        )
        session.add(failed_run)
        session.flush()
        persist_quality_checks(session, failed_run.id, check_results)
        session.commit()
        return 1

    print("Transforming ...")
    hourly_staging = transform_hourly_staging(datasets["saleshourly.csv"])
    daily_staging = transform_daily_staging(datasets["salesdaily.csv"])
    weekly_staging = transform_weekly_staging(datasets["salesweekly.csv"])
    monthly_staging = transform_monthly_staging(datasets["salesmonthly.csv"])
    canonical_fact = transform_canonical_fact(hourly_staging)

    print("Loading ...")
    result = run_load(
        session,
        hourly_staging,
        daily_staging,
        weekly_staging,
        monthly_staging,
        canonical_fact,
        check_results,
        settings.kaggle_dataset_id,
    )
    session.commit()

    print(f"ETL run {result.etl_run_id} complete. Rows loaded: {result.rows_loaded}")
    return 0


def main() -> None:
    engine = make_engine()
    SessionLocal = make_session_factory(engine)
    with SessionLocal() as session:
        exit_code = run(session)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
