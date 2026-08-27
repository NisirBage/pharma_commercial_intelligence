from fastapi import APIRouter

from app.schemas.common import SuccessResponse
from app.schemas.data_quality import DataQualityResponse
from app.services import data_quality_service

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


@router.get("", response_model=SuccessResponse[DataQualityResponse], summary="Source data quality and cross-granularity reconciliation status")
def data_quality() -> SuccessResponse[DataQualityResponse]:
    """Per-file record counts and the M2 cross-granularity reconciliation
    status — including the documented `salesmonthly.csv` inconsistency,
    which is always reported here, never hidden (M6 Sec. 19)."""
    return SuccessResponse(data=data_quality_service.get_data_quality(), metadata={"source": "M2 data quality"})
