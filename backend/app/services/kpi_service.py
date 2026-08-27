"""Wraps app.analytics.kpis (M3) for GET /api/v1/kpis/summary — no metric
is recomputed here, only assembled from M3's existing functions."""

from app.analytics import kpis
from app.schemas.kpis import KPISummaryResponse, PeriodRange
from app.services import cache


def get_kpi_summary() -> KPISummaryResponse:
    df = cache.get_canonical_frame()
    total = kpis.total_demand(df, grain="daily")
    average = kpis.average_demand(df, grain="daily")
    peak = kpis.peak_demand(df, grain="daily")
    contributions = kpis.contribution_by_atc(df)
    dominant = contributions[0] if contributions else None

    start, end = (None, None)
    if total.period:
        start, end = total.period.split("/")

    return KPISummaryResponse(
        total_demand=total.value,
        average_daily_demand=average.value,
        peak_daily_demand=peak.value,
        peak_date=peak.metadata.get("peak_period"),
        dominant_atc_class=dominant.entity if dominant else None,
        dominant_atc_share_pct=dominant.value if dominant else None,
        period=PeriodRange(start=start, end=end),
    )
