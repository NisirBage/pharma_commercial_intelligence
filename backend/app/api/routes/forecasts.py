from fastapi import APIRouter, Path

from app.schemas.common import SuccessResponse
from app.schemas.forecasts import ForecastDiagnosticsResponse, ForecastResponse
from app.services import forecast_service
from app.services.atc_registry import KNOWN_ATC_CLASSES

router = APIRouter(prefix="/forecast", tags=["forecast"])


# NOTE: "/aggregate" must be registered BEFORE "/{atc_class}" — Starlette
# matches path routes in registration order, and a dynamic {atc_class}
# segment would otherwise greedily swallow "aggregate" as if it were an
# ATC code.
@router.get("/aggregate", response_model=SuccessResponse[ForecastResponse], summary="Aggregate (all-class) 14-day demand forecast")
def aggregate_forecast() -> SuccessResponse[ForecastResponse]:
    """The DIRECT aggregate model — never a sum of the 8 per-class
    forecasts. M4 found the direct model materially more accurate (test
    WAPE ~16.27% vs. ~18.26% for the summed alternative) — see
    docs/model-selection.md. That distinction is preserved here, not
    silently replaced (M6 Sec. 12)."""
    return SuccessResponse(data=forecast_service.get_aggregate_forecast(), metadata={"source": "M4 forecasting"})


@router.get("/{atc_class}", response_model=SuccessResponse[ForecastResponse], summary="14-day demand forecast for one ATC class")
def forecast(atc_class: str = Path(..., description=f"One of: {sorted(KNOWN_ATC_CLASSES)}")) -> SuccessResponse[ForecastResponse]:
    """Point forecast + uncertainty interval for the next 14 days, using
    M4's already-selected, already-backtested model for this class — never
    retrained or re-backtested per request."""
    return SuccessResponse(data=forecast_service.get_forecast(atc_class), metadata={"source": "M4 forecasting"})


@router.get(
    "/{atc_class}/diagnostics",
    response_model=SuccessResponse[ForecastDiagnosticsResponse],
    summary="Residual diagnostics for one ATC class's forecast",
)
def forecast_diagnostics(
    atc_class: str = Path(..., description=f"One of: {sorted(KNOWN_ATC_CLASSES)}, or 'ALL' for the aggregate."),
) -> SuccessResponse[ForecastDiagnosticsResponse]:
    """Residual bias/spread, autocorrelation (Ljung-Box), per-horizon-step
    error, and explicit limitations — everything a frontend needs to
    explain why a given forecast should or should not be trusted (M6
    Sec. 13)."""
    return SuccessResponse(data=forecast_service.get_forecast_diagnostics(atc_class), metadata={"source": "M4 forecasting"})
