from fastapi import APIRouter, Query

from app.schemas.common import SuccessResponse
from app.schemas.optimization import ScenarioName
from app.schemas.recommendations import RecommendationsResponse
from app.services import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=SuccessResponse[RecommendationsResponse], summary="Explainable per-ATC-class planning recommendations")
def recommendations(
    scenario: ScenarioName = Query(ScenarioName.balanced, description="Which named scenario's assumptions to evaluate recommendations under."),
) -> SuccessResponse[RecommendationsResponse]:
    """Every recommendation names its own evidence, assumptions, expected
    effect, confidence, and limitations (M5/M6) — never a bare conclusion."""
    return SuccessResponse(data=recommendation_service.get_recommendations(scenario), metadata={"source": "M5 optimization"})
