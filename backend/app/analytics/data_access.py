"""Loads the canonical hourly demand frame that every analytics module
operates on. Two equivalent sources:

1. `load_from_db(session)` — queries `fact_demand_hourly` directly. This is
   what production/API code should use once a database is reachable.
2. `load_from_raw_csv(raw_data_dir)` — rebuilds the identical frame from
   the raw CSVs via the *exact same* `app.etl.transform` functions used to
   populate `fact_demand_hourly` (`transform_hourly_staging` +
   `transform_canonical_fact`).

No Postgres credentials were available in this environment (same
limitation noted in the M2 completion report), so `load_canonical_frame()`
defaults to (2). This is NOT an independent or approximate data source —
it is bit-for-bit the same transformation M2 proved correct
(`tests/integration/test_load.py`), just computed in-process instead of
read back from a table. `load_from_db` exists and is tested against
SQLite so it's ready the moment a real database is available.
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.etl.extract import extract_all
from app.etl.transform import transform_canonical_fact, transform_hourly_staging
from app.models.fact import FactDemandHourly

CANONICAL_COLUMNS = [
    "atc_code",
    "observation_ts",
    "units_sold",
    "year",
    "month",
    "hour_of_day",
    "weekday_name",
]


def load_from_raw_csv(raw_data_dir: Path | None = None) -> pd.DataFrame:
    raw_data_dir = raw_data_dir or settings.raw_data_dir
    datasets = extract_all(raw_data_dir)
    hourly_staging = transform_hourly_staging(datasets["saleshourly.csv"])
    long_df = transform_canonical_fact(hourly_staging)
    long_df["units_sold"] = long_df["units_sold"].astype(float)
    return long_df[CANONICAL_COLUMNS].sort_values("observation_ts").reset_index(drop=True)


def load_from_db(session: Session) -> pd.DataFrame:
    rows = session.execute(
        select(
            FactDemandHourly.atc_code,
            FactDemandHourly.observation_ts,
            FactDemandHourly.units_sold,
            FactDemandHourly.year,
            FactDemandHourly.month,
            FactDemandHourly.hour_of_day,
            FactDemandHourly.weekday_name,
        )
    ).all()
    df = pd.DataFrame(rows, columns=CANONICAL_COLUMNS)
    df["units_sold"] = df["units_sold"].astype(float)
    df["observation_ts"] = pd.to_datetime(df["observation_ts"])
    return df.sort_values("observation_ts").reset_index(drop=True)


def load_canonical_frame(
    session: Session | None = None, raw_data_dir: Path | None = None
) -> pd.DataFrame:
    """The single entry point every analytics module/service should call."""
    if session is not None:
        return load_from_db(session)
    return load_from_raw_csv(raw_data_dir)
