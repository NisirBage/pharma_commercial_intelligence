from fastapi import APIRouter, Query

from app.schemas.common import SuccessResponse
from app.schemas.sales import Grain, SalesTrendsResponse
from app.services import sales_service

router = APIRouter(prefix="/sales", tags=["sales"])


@router.get("/trends", response_model=SuccessResponse[SalesTrendsResponse], summary="Sales demand trend at a chosen grain")
def sales_trends(
    atc_class: str | None = Query(
        None, description="One of the 8 observed ATC classes; omit for the aggregate across all classes."
    ),
    start_date: str | None = Query(None, description="YYYY-MM-DD, inclusive."),
    end_date: str | None = Query(None, description="YYYY-MM-DD, inclusive."),
    grain: Grain = Query(
        Grain.daily,
        description="Rollup grain. Always derived from the canonical hourly fact table (M2) — monthly grain is NEVER sourced from salesmonthly.csv, which does not reconcile (see GET /api/v1/data-quality).",
    ),
) -> SuccessResponse[SalesTrendsResponse]:
    result = sales_service.get_sales_trends(atc_class, start_date, end_date, grain)
    return SuccessResponse(data=result, metadata={"source": "M2/M3 canonical demand model"})
