from fastapi import APIRouter, Query

from app.schemas.common import SuccessResponse
from app.schemas.optimization import (
    OptimizationRunRequest,
    OptimizationRunResponse,
    ScenarioName,
    ScenariosResponse,
    SensitivityParameter,
    SensitivityResponse,
)
from app.services import optimization_service
from app.services.atc_registry import KNOWN_ATC_CLASSES

router = APIRouter(prefix="/optimization", tags=["optimization"])


@router.get("/scenarios", response_model=SuccessResponse[ScenariosResponse], summary="Available planning scenarios")
def scenarios() -> SuccessResponse[ScenariosResponse]:
    """The 3 named scenarios (conservative/balanced/lean) and their
    parameters — read directly from M5's existing scenario definitions,
    never duplicated here."""
    return SuccessResponse(data=optimization_service.get_scenarios(), metadata={"source": "M5 optimization"})


@router.get(
    "/sensitivity",
    response_model=SuccessResponse[SensitivityResponse],
    summary="Sensitivity of safety stock/reorder point to one planning assumption",
)
def sensitivity(
    atc_class: str = Query(..., description=f"One of: {sorted(KNOWN_ATC_CLASSES)}"),
    scenario: ScenarioName = Query(ScenarioName.balanced, description="Scenario whose non-swept parameters are held fixed."),
    parameter: SensitivityParameter = Query(..., description="Which of M5's 4 sensitivity dimensions to sweep."),
) -> SuccessResponse[SensitivityResponse]:
    result = optimization_service.get_sensitivity(atc_class, scenario, parameter)
    return SuccessResponse(data=result, metadata={"source": "M5 optimization"})


@router.post("/run", response_model=SuccessResponse[OptimizationRunResponse], summary="Run the M5 optimization engine for a planning scenario")
def run(request: OptimizationRunRequest) -> SuccessResponse[OptimizationRunResponse]:
    """Runs M5's safety-stock/reorder-point/allocation engine for the
    requested scenario (optionally overriding service level and/or lead
    time). Every returned number is either read from M2-M4's observed
    data or explicitly labeled a scenario assumption (see the
    `assumptions` field) — never presented as an observed dataset fact."""
    result = optimization_service.run_optimization(request)
    return SuccessResponse(data=result, metadata={"source": "M5 optimization"})
