from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AtcClass(Base):
    """Dimension table for the 8 WHO ATC drug classes observed in the source
    data. atc_name/therapeutic_group are external domain reference
    knowledge (WHO ATC classification), NOT present in the Kaggle CSVs —
    `source` documents that distinction explicitly rather than presenting
    them as observed data. See docs/01-data-dictionary.md."""

    __tablename__ = "dim_atc_class"

    atc_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    atc_name: Mapped[str] = mapped_column(String(255), nullable=False)
    therapeutic_group: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="external_who_atc_reference"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
