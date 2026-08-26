"""Canonical analytical model. Built once, from stg_sales_hourly only (the
finest, fully-reconciling grain) — daily/weekly/monthly analytics are
computed as SQL views over this table (see the Alembic migration), never by
loading the coarser CSVs a second time, which is what prevents double
counting across grains. See docs/data-quality-decisions.md."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FactDemandHourly(Base):
    __tablename__ = "fact_demand_hourly"
    __table_args__ = (
        UniqueConstraint("atc_code", "observation_ts", name="uq_fact_demand_hourly_atc_ts"),
        CheckConstraint("units_sold >= 0", name="ck_fact_demand_hourly_units_nonneg"),
        CheckConstraint("hour_of_day BETWEEN 0 AND 23", name="ck_fact_demand_hourly_hour_range"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    atc_code: Mapped[str] = mapped_column(
        String(10), ForeignKey("dim_atc_class.atc_code"), nullable=False
    )
    observation_ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    units_sold: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    hour_of_day: Mapped[int] = mapped_column(Integer, nullable=False)
    weekday_name: Mapped[str] = mapped_column(String(20), nullable=False)
    stg_sales_hourly_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("stg_sales_hourly.id"), nullable=False
    )
    loaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
