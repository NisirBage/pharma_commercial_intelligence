"""Wraps app.analytics.atc_analysis (M3) for GET /api/v1/analytics/atc."""

from app.analytics import atc_analysis
from app.schemas.analytics import ATCPerformance, ATCPerformanceResponse, ConcentrationEntry, DemandConcentration
from app.services import cache


def get_atc_performance() -> ATCPerformanceResponse:
    df = cache.get_canonical_frame()
    profiles = atc_analysis.build_atc_profiles(df)
    concentration = atc_analysis.demand_concentration(df)
    dominant = [p["atc_code"] for p in atc_analysis.rank_by_contribution(profiles)[:3]]

    classes = []
    for p in profiles:
        trend = p["trend"]
        classes.append(
            ATCPerformance(
                atc_class=p["atc_code"],
                total_demand=p["total_demand"].value,
                average_daily_demand=p["average_daily_demand"].value,
                peak_daily_demand=p["peak_daily_demand"].value,
                trough_daily_demand=p["trough_daily_demand"].value,
                contribution_pct=p["contribution"].value if p["contribution"] else None,
                trend_slope=trend.value,
                trend_classification=trend.metadata.get("classification") or trend.metadata.get("reason", "unknown"),
                trend_p_value=trend.metadata.get("p_value"),
                volatility_cv=p["volatility_cv"].value,
            )
        )

    return ATCPerformanceResponse(
        classes=classes,
        dominant_classes=dominant,
        concentration=DemandConcentration(
            ranked=[ConcentrationEntry(**r) for r in concentration["ranked"]],
            concentration_ratio_top3_pct=concentration["concentration_ratio_top3_pct"],
            hhi=concentration["hhi"],
            hhi_scale_note=concentration["hhi_scale_note"],
        ),
    )
