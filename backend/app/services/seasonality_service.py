"""Wraps app.analytics.seasonality (M3) for GET /api/v1/analytics/seasonality
— day-of-week effect, hour-of-day effect (sourced from saleshourly.csv's
real hour column, never salesdaily.csv's `Hour` artifact — M2 Decision 1),
and STL-based seasonal strength at weekly (period=7, daily grain) and
annual (period=12, monthly grain, derived from the canonical hourly frame,
never salesmonthly.csv — M2 Decision 2) cycles. No new statistics are
computed here — every number comes from M3's existing functions."""

from app.analytics import seasonality as seasonality_module
from app.api.errors import NotFoundError
from app.schemas.seasonality import DayOfWeekEffect, HourOfDayEffect, SeasonalityResponse, SeasonalStrengthInfo
from app.services import cache
from app.services.atc_registry import KNOWN_ATC_CLASSES


def get_seasonality(atc_class: str | None) -> SeasonalityResponse:
    if atc_class is not None and atc_class not in KNOWN_ATC_CLASSES:
        raise NotFoundError(f"Unknown ATC class {atc_class!r}. Known classes: {sorted(KNOWN_ATC_CLASSES)}.")

    df = cache.get_canonical_frame()

    dow = seasonality_module.day_of_week_effect(df, entity=atc_class)
    hod = seasonality_module.hour_of_day_effect(df, entity=atc_class)
    weekly = seasonality_module.seasonal_strength(df, entity=atc_class, grain="daily", period=7)
    annual = seasonality_module.seasonal_strength(df, entity=atc_class, grain="monthly", period=12)

    mean_by_hour = hod.metadata.get("mean_units_by_hour")

    return SeasonalityResponse(
        atc_class=atc_class or "ALL",
        day_of_week_effect=DayOfWeekEffect(
            h_statistic=dow.value,
            p_value=dow.metadata.get("p_value"),
            significant=dow.metadata.get("significant"),
            mean_units_by_weekday=dow.metadata.get("mean_units_by_weekday"),
            available=dow.value is not None,
            reason=dow.metadata.get("reason"),
        ),
        hour_of_day_effect=HourOfDayEffect(
            h_statistic=hod.value,
            p_value=hod.metadata.get("p_value"),
            significant=hod.metadata.get("significant"),
            mean_units_by_hour={str(k): v for k, v in mean_by_hour.items()} if mean_by_hour else None,
            available=hod.value is not None,
            reason=hod.metadata.get("reason"),
        ),
        weekly_seasonal_strength=SeasonalStrengthInfo(
            strength=weekly.value,
            cycle_period=weekly.metadata.get("cycle_period"),
            n_periods=weekly.metadata.get("n_periods"),
            interpretation=weekly.metadata.get("interpretation"),
            available=weekly.value is not None,
            reason=weekly.metadata.get("reason"),
        ),
        annual_seasonal_strength=SeasonalStrengthInfo(
            strength=annual.value,
            cycle_period=annual.metadata.get("cycle_period"),
            n_periods=annual.metadata.get("n_periods"),
            interpretation=annual.metadata.get("interpretation"),
            available=annual.value is not None,
            reason=annual.metadata.get("reason"),
        ),
    )
