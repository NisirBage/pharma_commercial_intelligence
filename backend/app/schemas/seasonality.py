from pydantic import BaseModel

from app.schemas.common import SafeFloat


class DayOfWeekEffect(BaseModel):
    """Kruskal-Wallis test for a day-of-week effect on daily total demand."""

    h_statistic: SafeFloat
    p_value: SafeFloat
    significant: bool | None
    mean_units_by_weekday: dict[str, float] | None
    available: bool
    reason: str | None = None


class HourOfDayEffect(BaseModel):
    """Kruskal-Wallis test for an hour-of-day effect — sourced from
    saleshourly.csv's real hour column, NEVER salesdaily.csv's `Hour`
    artifact (see docs/data-quality-decisions.md Decision 1)."""

    h_statistic: SafeFloat
    p_value: SafeFloat
    significant: bool | None
    mean_units_by_hour: dict[str, float] | None
    available: bool
    reason: str | None = None


class SeasonalStrengthInfo(BaseModel):
    """STL-decomposition seasonal strength (Hyndman & Athanasopoulos):
    0 = no seasonal pattern, ~1 = strong, regular seasonal pattern."""

    strength: SafeFloat
    cycle_period: int | None
    n_periods: int | None
    interpretation: str | None
    available: bool
    reason: str | None = None


class SeasonalityResponse(BaseModel):
    atc_class: str  # "ALL" or one of the 8 observed ATC classes
    day_of_week_effect: DayOfWeekEffect
    hour_of_day_effect: HourOfDayEffect
    weekly_seasonal_strength: SeasonalStrengthInfo
    annual_seasonal_strength: SeasonalStrengthInfo
