from enum import Enum

from pydantic import BaseModel

from app.schemas.common import SafeFloat


class Grain(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class TrendPoint(BaseModel):
    period: str
    units_sold: SafeFloat


class SalesTrendsResponse(BaseModel):
    atc_class: str | None
    grain: Grain
    start_date: str
    end_date: str
    points: list[TrendPoint]
