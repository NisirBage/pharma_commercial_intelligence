"""Structured optimization output — the exact shape a future
`POST /api/v1/optimization/run` endpoint would serialize (M5 Sec. 14/15).
"""

from dataclasses import asdict, dataclass, field
from typing import Any

from app.optimization.assumptions import ScenarioParameters
from app.optimization.demand_input import DemandInput
from app.optimization.recommendations import Recommendation
from app.optimization.reorder_point import ReorderPointResult
from app.optimization.scenarios import ScenarioResult


@dataclass
class ATCPlanningResult:
    atc_class: str
    scenario: str
    model_used: str
    forecast: list[float]
    forecast_dates: list[str]
    forecast_uncertainty: dict[str, Any]
    lead_time_days: int
    service_level: float
    safety_stock: float
    reorder_point: float
    recommended_order_quantity: float
    inventory_exposure: float
    expected_shortage: float
    recommendation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OptimizationRunResult:
    scenario: str
    assumptions: list[dict[str, Any]]
    capacity_budget: float
    atc_results: dict[str, ATCPlanningResult]
    allocation_baseline: dict[str, Any]
    allocation_optimized: dict[str, Any]
    optimization_summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "assumptions": self.assumptions,
            "capacity_budget": self.capacity_budget,
            "atc_results": {k: v.to_dict() for k, v in self.atc_results.items()},
            "allocation_baseline": self.allocation_baseline,
            "allocation_optimized": self.allocation_optimized,
            "optimization_summary": self.optimization_summary,
        }


def _allocation_result_to_dict(allocation_result) -> dict[str, Any]:
    return {
        "policy_name": allocation_result.policy_name,
        "solver_status": allocation_result.solver_status,
        "total_capacity_budget": allocation_result.total_capacity_budget,
        "total_safety_stock_allocated": allocation_result.total_safety_stock_allocated,
        "total_expected_shortage": allocation_result.total_expected_shortage,
        "total_weighted_expected_shortage": allocation_result.total_weighted_expected_shortage,
        "per_class": {k: asdict(v) for k, v in allocation_result.per_class.items()},
    }


def build_optimization_run_result(
    scenario_result: ScenarioResult,
    demand_inputs: dict[str, DemandInput],
    recommendations: dict[str, Recommendation],
    order_quantities: dict[str, float],
) -> OptimizationRunResult:
    """Assembles every prior module's output into the final structured
    result — uses the OPTIMIZED (LP) allocation's per-class safety stock/
    reorder point as the "official" recommended policy (the baseline is
    retained in the output purely for comparison, per M5 Sec. 8)."""
    params: ScenarioParameters = scenario_result.parameters
    atc_results: dict[str, ATCPlanningResult] = {}

    for atc, di in demand_inputs.items():
        independent_rop: ReorderPointResult = scenario_result.independent_reorder_points[atc]
        optimized_class = scenario_result.optimized_allocation.per_class[atc]

        atc_results[atc] = ATCPlanningResult(
            atc_class=atc,
            scenario=scenario_result.scenario_name,
            model_used=di.selected_model,
            forecast=di.point_forecast,
            forecast_dates=di.forecast_dates,
            forecast_uncertainty={
                "sigma_lead_time_primary": independent_rop.safety_stock_detail.sigma_lead_time_primary,
                "sigma_lead_time_flat_sqrt": independent_rop.safety_stock_detail.sigma_lead_time_flat_sqrt,
                "sigma_lead_time_empirical_fold": independent_rop.safety_stock_detail.sigma_lead_time_empirical_fold,
                "estimator_spread_pct": independent_rop.safety_stock_detail.uncertainty_estimator_spread_pct,
            },
            lead_time_days=params.lead_time_days,
            service_level=optimized_class.implied_service_level,
            safety_stock=optimized_class.safety_stock,
            reorder_point=float(independent_rop.expected_demand_during_lead_time + optimized_class.safety_stock),
            recommended_order_quantity=order_quantities.get(atc, 0.0),
            inventory_exposure=optimized_class.safety_stock,
            expected_shortage=optimized_class.expected_shortage,
            recommendation=asdict(recommendations[atc]) if atc in recommendations else {},
        )

    improvement_pct = None
    baseline_shortage = scenario_result.baseline_allocation.total_weighted_expected_shortage
    optimized_shortage = scenario_result.optimized_allocation.total_weighted_expected_shortage
    if baseline_shortage > 0:
        improvement_pct = float((baseline_shortage - optimized_shortage) / baseline_shortage * 100)

    return OptimizationRunResult(
        scenario=scenario_result.scenario_name,
        assumptions=params.as_assumption_rows(),
        capacity_budget=scenario_result.capacity_budget,
        atc_results=atc_results,
        allocation_baseline=_allocation_result_to_dict(scenario_result.baseline_allocation),
        allocation_optimized=_allocation_result_to_dict(scenario_result.optimized_allocation),
        optimization_summary={
            "baseline_total_weighted_expected_shortage": baseline_shortage,
            "optimized_total_weighted_expected_shortage": optimized_shortage,
            "improvement_pct": improvement_pct,
            "same_total_inventory_exposure": True,
        },
    )
