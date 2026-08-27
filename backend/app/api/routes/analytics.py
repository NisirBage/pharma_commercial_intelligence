from fastapi import APIRouter

from app.schemas.analytics import ATCPerformanceResponse
from app.schemas.common import SuccessResponse
from app.services import atc_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/atc", response_model=SuccessResponse[ATCPerformanceResponse], summary="Per-ATC-class performance and demand concentration")
def atc_performance() -> SuccessResponse[ATCPerformanceResponse]:
    """Total/average/peak demand, contribution share, statistical trend
    (with significance), volatility (CV), and dataset-wide concentration
    (CR3/HHI) per ATC class — all from M3's existing analytics."""
    return SuccessResponse(data=atc_service.get_atc_performance(), metadata={"source": "M3 analytics"})
