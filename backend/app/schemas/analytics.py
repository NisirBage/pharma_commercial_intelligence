from pydantic import BaseModel

from app.schemas.common import SafeFloat


class ATCPerformance(BaseModel):
    atc_class: str
    total_demand: SafeFloat
    average_daily_demand: SafeFloat
    peak_daily_demand: SafeFloat
    trough_daily_demand: SafeFloat
    contribution_pct: SafeFloat
    trend_slope: SafeFloat
    trend_classification: str
    trend_p_value: SafeFloat
    volatility_cv: SafeFloat


class ConcentrationEntry(BaseModel):
    atc_code: str
    share_pct: SafeFloat
    cumulative_share_pct: SafeFloat


class DemandConcentration(BaseModel):
    ranked: list[ConcentrationEntry]
    concentration_ratio_top3_pct: SafeFloat
    hhi: SafeFloat
    hhi_scale_note: str


class ATCPerformanceResponse(BaseModel):
    classes: list[ATCPerformance]
    dominant_classes: list[str]
    concentration: DemandConcentration
