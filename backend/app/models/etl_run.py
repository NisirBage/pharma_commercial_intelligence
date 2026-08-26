from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EtlRun(Base):
    __tablename__ = "etl_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    source_dataset_identifier: Mapped[str] = mapped_column(
        String(100), nullable=False, default="milanzdravkovic/pharma-sales-data"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    quality_checks: Mapped[list["DataQualityCheck"]] = relationship(back_populates="etl_run")


class DataQualityCheck(Base):
    __tablename__ = "data_quality_check"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    etl_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("etl_run.id"), nullable=False)
    check_name: Mapped[str] = mapped_column(String(100), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(10), nullable=False)  # pass / fail / warn
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    etl_run: Mapped["EtlRun"] = relationship(back_populates="quality_checks")
