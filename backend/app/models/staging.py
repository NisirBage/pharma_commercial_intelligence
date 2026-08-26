"""Staging tables — one per raw source file, mirroring each CSV's own
(wide) column layout for source fidelity. These are full-refresh (truncated
and reloaded every ETL run, see app/etl/load.py) since the source is a
fixed historical export, not an incremental feed. Nothing here is
normalized or melted — that happens in the canonical layer (app/models/fact.py)."""

from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

PRODUCT_COLUMNS = ("m01ab", "m01ae", "n02ba", "n02be", "n05b", "n05c", "r03", "r06")


class StgSalesHourly(Base):
    """Mirrors saleshourly.csv — the canonical base grain (see docs/data-quality-decisions.md)."""

    __tablename__ = "stg_sales_hourly"
    __table_args__ = (UniqueConstraint("observation_ts", name="uq_stg_sales_hourly_ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datum_raw: Mapped[str] = mapped_column(String(30), nullable=False)
    observation_ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    m01ab: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    m01ae: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n02ba: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n02be: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n05b: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n05c: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    r03: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    r06: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    hour_of_day: Mapped[int] = mapped_column(Integer, nullable=False)
    weekday_name: Mapped[str] = mapped_column(String(20), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class StgSalesDaily(Base):
    """Mirrors salesdaily.csv. `hour_sum_artifact` is the raw source `Hour`
    column, renamed to document Decision 1 (docs/data-quality-decisions.md)
    — it is NOT an hour-of-day and must never be used analytically."""

    __tablename__ = "stg_sales_daily"
    __table_args__ = (UniqueConstraint("observation_date", name="uq_stg_sales_daily_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datum_raw: Mapped[str] = mapped_column(String(30), nullable=False)
    observation_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    m01ab: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    m01ae: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n02ba: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n02be: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n05b: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n05c: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    r03: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    r06: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    hour_sum_artifact: Mapped[int] = mapped_column(Integer, nullable=False)
    weekday_name: Mapped[str] = mapped_column(String(20), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class StgSalesWeekly(Base):
    """Mirrors salesweekly.csv. Week-ending convention verified as
    Sunday-ending, trailing 7 days (see docs/data-quality-decisions.md)."""

    __tablename__ = "stg_sales_weekly"
    __table_args__ = (UniqueConstraint("week_ending_date", name="uq_stg_sales_weekly_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datum_raw: Mapped[str] = mapped_column(String(30), nullable=False)
    week_ending_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    m01ab: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    m01ae: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n02ba: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n02be: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n05b: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n05c: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    r03: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    r06: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class StgSalesMonthly(Base):
    """Mirrors salesmonthly.csv. `is_reconciled` is always False — this file
    was found NOT to reconcile with the daily-grain sum for 33/70 months,
    including a severe Jan/Feb 2017 boundary defect (see
    docs/data-quality-decisions.md, Decision 2). Loaded for audit/reference
    only; excluded from the canonical model."""

    __tablename__ = "stg_sales_monthly"
    __table_args__ = (UniqueConstraint("month_end_date", name="uq_stg_sales_monthly_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    datum_raw: Mapped[str] = mapped_column(String(30), nullable=False)
    month_end_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    m01ab: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    m01ae: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n02ba: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n02be: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n05b: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    n05c: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    r03: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    r06: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    is_reconciled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
