from fastapi import APIRouter, Query

from app.schemas.anomalies import AnomaliesResponse, AnomalyMethod
from app.schemas.common import SuccessResponse
from app.services import anomaly_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/anomalies", response_model=SuccessResponse[AnomaliesResponse], summary="Statistically flagged demand anomalies")
def anomalies(
    atc_class: str | None = Query(None, description="One of the 8 observed ATC classes; omit to scan all classes."),
    method: AnomalyMethod = Query(AnomalyMethod.rolling_zscore, description="Detection method (M3): 30-day trailing rolling z-score, or IQR/Tukey fence."),
    severity: str | None = Query(None, description="Filter to 'low', 'medium', or 'high'."),
    start_date: str | None = Query(None, description="YYYY-MM-DD, inclusive."),
    end_date: str | None = Query(None, description="YYYY-MM-DD, inclusive."),
) -> SuccessResponse[AnomaliesResponse]:
    result = anomaly_service.get_anomalies(atc_class, method, severity, start_date, end_date)
    return SuccessResponse(data=result, metadata={"source": "M3 analytics"})
