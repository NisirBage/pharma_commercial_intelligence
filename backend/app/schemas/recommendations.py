from pydantic import BaseModel

from app.schemas.optimization import ScenarioName


class RecommendationItem(BaseModel):
    atc_class: str
    recommendation: str
    evidence: list[str]
    assumptions: list[str]
    expected_effect: str
    confidence: str
    limitations: list[str]


class RecommendationsResponse(BaseModel):
    scenario: ScenarioName
    recommendations: list[RecommendationItem]
