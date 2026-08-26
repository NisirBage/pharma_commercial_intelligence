"""Loading: writes validated/transformed data into Postgres via SQLAlchemy.

Idempotent full-refresh — every run truncates and reloads the staging and
fact tables (this is a fixed historical export, not an incremental feed;
see docs/etl.md). dim_atc_class is upserted, never deleted, since it is
seed reference data independent of any particular ETL run.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.etl.reference_data import ATC_REFERENCE
from app.etl.validate import CheckResult
from app.models.atc_class import AtcClass
from app.models.etl_run import DataQualityCheck, EtlRun
from app.models.fact import FactDemandHourly
from app.models.staging import StgSalesDaily, StgSalesHourly, StgSalesMonthly, StgSalesWeekly


@dataclass
class LoadResult:
    etl_run_id: int
    rows_loaded: dict[str, int] = field(default_factory=dict)


def seed_atc_reference(session: Session) -> None:
    existing = {row.atc_code for row in session.execute(select(AtcClass.atc_code)).all()}
    to_insert = [
        {"atc_code": code, "atc_name": meta["atc_name"], "therapeutic_group": meta["therapeutic_group"]}
        for code, meta in ATC_REFERENCE.items()
        if code not in existing
    ]
    if to_insert:
        session.execute(insert(AtcClass), to_insert)


def _truncate_run_tables(session: Session) -> None:
    # Order matters: fact table FKs to staging, so delete it first.
    session.execute(delete(FactDemandHourly))
    session.execute(delete(StgSalesHourly))
    session.execute(delete(StgSalesDaily))
    session.execute(delete(StgSalesWeekly))
    session.execute(delete(StgSalesMonthly))


def load_staging(
    session: Session,
    hourly_df: pd.DataFrame,
    daily_df: pd.DataFrame,
    weekly_df: pd.DataFrame,
    monthly_df: pd.DataFrame,
) -> dict[str, int]:
    counts = {}
    for table, df, name in (
        (StgSalesHourly, hourly_df, "stg_sales_hourly"),
        (StgSalesDaily, daily_df, "stg_sales_daily"),
        (StgSalesWeekly, weekly_df, "stg_sales_weekly"),
        (StgSalesMonthly, monthly_df, "stg_sales_monthly"),
    ):
        records = df.to_dict(orient="records")
        if records:
            session.execute(insert(table), records)
        counts[name] = len(records)
    return counts


def load_canonical_fact(session: Session, canonical_long_df: pd.DataFrame) -> int:
    """Joins the melted long-format demand rows back to the just-inserted
    stg_sales_hourly.id (looked up by observation_ts) so every fact row is
    traceable to its exact source row."""
    id_rows = session.execute(select(StgSalesHourly.id, StgSalesHourly.observation_ts)).all()
    id_map = pd.DataFrame(id_rows, columns=["stg_sales_hourly_id", "observation_ts"])

    merged = canonical_long_df.merge(id_map, on="observation_ts", how="left")
    if merged["stg_sales_hourly_id"].isna().any():
        n_missing = int(merged["stg_sales_hourly_id"].isna().sum())
        raise ValueError(
            f"{n_missing} canonical fact rows could not be matched back to a staged "
            "hourly row — staging load must have failed or run out of order."
        )
    merged["stg_sales_hourly_id"] = merged["stg_sales_hourly_id"].astype(int)

    records = merged[
        ["atc_code", "observation_ts", "units_sold", "year", "month", "hour_of_day", "weekday_name", "stg_sales_hourly_id"]
    ].to_dict(orient="records")
    if records:
        session.execute(insert(FactDemandHourly), records)
    return len(records)


def persist_quality_checks(session: Session, etl_run_id: int, check_results: list[CheckResult]) -> None:
    records = [
        {
            "etl_run_id": etl_run_id,
            "check_name": r.check_name,
            "file_name": r.file_name,
            "status": r.status,
            "details_json": json.dumps(r.details),
            "checked_at": r.checked_at,
        }
        for r in check_results
    ]
    if records:
        session.execute(insert(DataQualityCheck), records)


def run_load(
    session: Session,
    hourly_staging: pd.DataFrame,
    daily_staging: pd.DataFrame,
    weekly_staging: pd.DataFrame,
    monthly_staging: pd.DataFrame,
    canonical_fact: pd.DataFrame,
    check_results: list[CheckResult],
    kaggle_dataset_id: str,
) -> LoadResult:
    started_at = datetime.now(timezone.utc)
    run = EtlRun(started_at=started_at, status="running", source_dataset_identifier=kaggle_dataset_id)
    session.add(run)
    session.flush()  # assigns run.id

    seed_atc_reference(session)
    _truncate_run_tables(session)
    session.flush()

    staging_counts = load_staging(session, hourly_staging, daily_staging, weekly_staging, monthly_staging)
    session.flush()

    fact_count = load_canonical_fact(session, canonical_fact)

    persist_quality_checks(session, run.id, check_results)

    run.status = "failed" if any(r.status == "fail" for r in check_results) else "success"
    run.finished_at = datetime.now(timezone.utc)
    session.flush()

    result = LoadResult(etl_run_id=run.id, rows_loaded={**staging_counts, "fact_demand_hourly": fact_count})
    return result
