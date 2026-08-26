"""Transformation: type/rename raw columns into each staging table's shape,
and melt the hourly staging frame (wide, one column per ATC class) into the
long/tidy canonical fact shape. Every transformation here is justified by
an actual finding in docs/01-data-dictionary.md or
docs/data-quality-decisions.md — nothing is reshaped "because it seemed
tidier."
"""

import pandas as pd

from app.etl.extract import DATE_FORMATS, RawDataset
from app.etl.reference_data import ATC_REFERENCE

PRODUCT_COLUMNS = list(ATC_REFERENCE.keys())
_PRODUCT_COL_RENAME = {c: c.lower() for c in PRODUCT_COLUMNS}


def transform_hourly_staging(ds: RawDataset) -> pd.DataFrame:
    df = ds.frame.copy()
    df["observation_ts"] = pd.to_datetime(df["datum"], format=DATE_FORMATS[ds.name])
    df = df.rename(columns=_PRODUCT_COL_RENAME)
    df = df.rename(
        columns={"datum": "datum_raw", "Year": "year", "Month": "month", "Hour": "hour_of_day", "Weekday Name": "weekday_name"}
    )
    cols = ["datum_raw", "observation_ts", *_PRODUCT_COL_RENAME.values(), "year", "month", "hour_of_day", "weekday_name"]
    return df[cols]


def transform_daily_staging(ds: RawDataset) -> pd.DataFrame:
    df = ds.frame.copy()
    df["observation_date"] = pd.to_datetime(df["datum"], format=DATE_FORMATS[ds.name]).dt.date
    df = df.rename(columns=_PRODUCT_COL_RENAME)
    # "Hour" is the aggregation artifact documented in Decision 1 — renamed,
    # never treated as a real hour-of-day.
    df = df.rename(
        columns={
            "datum": "datum_raw",
            "Year": "year",
            "Month": "month",
            "Hour": "hour_sum_artifact",
            "Weekday Name": "weekday_name",
        }
    )
    cols = ["datum_raw", "observation_date", *_PRODUCT_COL_RENAME.values(), "year", "month", "hour_sum_artifact", "weekday_name"]
    return df[cols]


def transform_weekly_staging(ds: RawDataset) -> pd.DataFrame:
    df = ds.frame.copy()
    df["week_ending_date"] = pd.to_datetime(df["datum"], format=DATE_FORMATS[ds.name]).dt.date
    df = df.rename(columns=_PRODUCT_COL_RENAME)
    df = df.rename(columns={"datum": "datum_raw"})
    cols = ["datum_raw", "week_ending_date", *_PRODUCT_COL_RENAME.values()]
    return df[cols]


def transform_monthly_staging(ds: RawDataset) -> pd.DataFrame:
    df = ds.frame.copy()
    df["month_end_date"] = pd.to_datetime(df["datum"], format=DATE_FORMATS[ds.name]).dt.date
    df = df.rename(columns=_PRODUCT_COL_RENAME)
    df = df.rename(columns={"datum": "datum_raw"})
    df["is_reconciled"] = False  # per Decision 2 — always False, see docs/data-quality-decisions.md
    cols = ["datum_raw", "month_end_date", *_PRODUCT_COL_RENAME.values(), "is_reconciled"]
    return df[cols]


def transform_canonical_fact(hourly_staging: pd.DataFrame) -> pd.DataFrame:
    """Melts the wide hourly staging frame into the long canonical shape:
    one row per (atc_code, observation_ts). `observation_ts` is carried
    through as the join key back to stg_sales_hourly.id (assigned at load
    time, once rows exist in the DB)."""
    id_vars = ["observation_ts", "year", "month", "hour_of_day", "weekday_name"]
    value_vars = list(_PRODUCT_COL_RENAME.values())
    long_df = hourly_staging.melt(
        id_vars=id_vars, value_vars=value_vars, var_name="atc_code_lower", value_name="units_sold"
    )
    long_df["atc_code"] = long_df["atc_code_lower"].str.upper()
    return long_df[["observation_ts", "atc_code", "units_sold", "year", "month", "hour_of_day", "weekday_name"]]
