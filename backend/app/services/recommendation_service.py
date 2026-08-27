"""Wraps app.optimization.recommendations (M5) for GET /api/v1/recommendations."""

from app.optimization import scenarios as scenarios_module
from app.optimization.recommendations import build_all_recommendations
from app.optimization.reorder_point import compute_reorder_point
from app.schemas.optimization import ScenarioName
from app.schemas.recommendations import RecommendationItem, RecommendationsResponse
from app.services import cache
from app.services.optimization_service import per_class_demand_inputs_or_503


def get_recommendations(scenario: ScenarioName) -> RecommendationsResponse:
    demand_inputs = per_class_demand_inputs_or_503()
    params = scenarios_module.SCENARIOS[scenario.value]
    reorder_points = {
        atc: compute_reorder_point(di, params.lead_time_days, params.service_level_target)
        for atc, di in demand_inputs.items()
    }
    contributions = cache.get_contributions()
    recs = build_all_recommendations(demand_inputs, reorder_points, scenario.value, contributions)

    return RecommendationsResponse(
        scenario=scenario,
        recommendations=[
            RecommendationItem(
                atc_class=r.atc_class,
                recommendation=r.recommendation,
                evidence=r.evidence,
                assumptions=r.assumptions,
                expected_effect=r.expected_effect,
                confidence=r.confidence,
                limitations=r.limitations,
            )
            for r in recs.values()
        ],
    )
