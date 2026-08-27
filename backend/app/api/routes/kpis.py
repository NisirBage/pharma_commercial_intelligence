from fastapi import APIRouter

from app.schemas.common import SuccessResponse
from app.schemas.kpis import KPISummaryResponse
from app.services import kpi_service

router = APIRouter(prefix="/kpis", tags=["kpis"])


@router.get("/summary", response_model=SuccessResponse[KPISummaryResponse], summary="Executive KPI summary")
def kpi_summary() -> SuccessResponse[KPISummaryResponse]:
    """Total/average/peak daily demand and the dominant ATC class — read
    directly from M3's existing analytics, nothing recomputed here."""
    return SuccessResponse(data=kpi_service.get_kpi_summary(), metadata={"source": "M3 analytics"})
