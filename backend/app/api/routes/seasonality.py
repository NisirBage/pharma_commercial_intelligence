from fastapi import APIRouter, Query

from app.schemas.common import SuccessResponse
from app.schemas.seasonality import SeasonalityResponse
from app.services import seasonality_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/seasonality",
    response_model=SuccessResponse[SeasonalityResponse],
    summary="Day-of-week effect, hour-of-day effect, and seasonal strength",
)
def seasonality(
    atc_class: str | None = Query(
        None, description="One of the 8 observed ATC classes; omit for the aggregate across all classes."
    ),
) -> SuccessResponse[SeasonalityResponse]:
    """Kruskal-Wallis day-of-week/hour-of-day effects and STL-decomposition
    seasonal strength (weekly: period=7 on daily grain; annual: period=12
    on monthly grain, always derived from the canonical hourly frame —
    never salesmonthly.csv) — all from M3's existing analytics, unchanged."""
    result = seasonality_service.get_seasonality(atc_class)
    return SuccessResponse(data=result, metadata={"source": "M3 analytics"})
