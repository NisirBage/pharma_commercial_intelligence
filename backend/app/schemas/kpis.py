from pydantic import BaseModel

from app.schemas.common import SafeFloat


class PeriodRange(BaseModel):
    start: str | None
    end: str | None


class KPISummaryResponse(BaseModel):
    total_demand: SafeFloat
    average_daily_demand: SafeFloat
    peak_daily_demand: SafeFloat
    peak_date: str | None
    dominant_atc_class: str | None
    dominant_atc_share_pct: SafeFloat
    period: PeriodRange
