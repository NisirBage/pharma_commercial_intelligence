"""Wraps app.optimization (M5) for POST /api/v1/optimization/run,
GET /api/v1/optimization/scenarios, and GET /api/v1/optimization/sensitivity.
Every number is produced by M5's existing runner/scenarios/sensitivity
modules — this file only translates between HTTP request/response shapes
and the domain layer (M6 Sec. 33).
"""

import dataclasses

from app.api.errors import NotFoundError, OptimizationInfeasibleError, ServiceUnavailableError
from app.optimization import scenarios as scenarios_module
from app.optimization import sensitivity as sensitivity_module
from app.optimization.demand_input import DemandInput
from app.optimization.outputs import build_optimization_run_result
from app.optimization.recommendations import build_all_recommendations
from app.optimization.reorder_point import compute_scenario_order_quantity
from app.schemas.optimization import (
    AllocationPolicySchema,
    AssumptionRow,
    ATCPlanningResultSchema,
    OptimizationRunRequest,
    OptimizationRunResponse,
    ScenarioInfo,
    ScenarioName,
    ScenariosResponse,
    SensitivityParameter,
    SensitivityPointSchema,
    SensitivityResponse,
)
from app.services import cache
from app.services.atc_registry import KNOWN_ATC_CLASSES

_INFEASIBLE_STATUSES = {"infeasible", "unbounded", "unknown"}

_SWEEP_FUNCS = {
    SensitivityParameter.lead_time_days: lambda di, params: sensitivity_module.sweep_lead_time(
        di, params.service_level_target
    ),
    SensitivityParameter.service_level_target: lambda di, params: sensitivity_module.sweep_service_level(
        di, params.lead_time_days
    ),
    SensitivityParameter.demand_uncertainty_scale: lambda di, params: sensitivity_module.sweep_demand_uncertainty(
        di, params.lead_time_days, params.service_level_target
    ),
    SensitivityParameter.stockout_cost_weight: lambda di, params: sensitivity_module.sweep_stockout_cost_weight(
        di, params.lead_time_days, params.holding_cost_weight
    ),
}


def per_class_demand_inputs_or_503() -> dict[str, DemandInput]:
    try:
        inputs = cache.get_demand_inputs()
    except ValueError as exc:
        raise ServiceUnavailableError(
            "Optimization inputs are not available yet — run backend/scripts/run_m4_backtest.py first."
        ) from exc
    return {atc: di for atc, di in inputs.items() if atc != "ALL"}


def run_optimization(request: OptimizationRunRequest) -> OptimizationRunResponse:
    demand_inputs = per_class_demand_inputs_or_503()
    base_params = scenarios_module.SCENARIOS[request.scenario.value]

    overrides = {}
    if request.service_level is not None:
        overrides["service_level_target"] = request.service_level
    if request.lead_time_days is not None:
        overrides["lead_time_days"] = request.lead_time_days
    params = dataclasses.replace(base_params, **overrides) if overrides else base_params

    scenario_result = scenarios_module.run_scenario(request.scenario.value, demand_inputs, params=params)

    if scenario_result.optimized_allocation.solver_status in _INFEASIBLE_STATUSES:
        raise OptimizationInfeasibleError(
            "The optimization solver could not find a feasible allocation for the requested parameters "
            f"(status: {scenario_result.optimized_allocation.solver_status})."
        )

    warnings = []
    if scenario_result.baseline_allocation.solver_status in _INFEASIBLE_STATUSES:
        warnings.append(f"Baseline allocation solver status: {scenario_result.baseline_allocation.solver_status}")

    contributions = cache.get_contributions()
    recommendations = build_all_recommendations(
        demand_inputs, scenario_result.independent_reorder_points, request.scenario.value, contributions
    )
    order_quantities = {
        atc: compute_scenario_order_quantity(
            di,
            ordering_cost_weight=params.ordering_cost_weight,
            holding_cost_weight=params.holding_cost_weight,
            minimum_order_quantity=params.minimum_order_quantity,
            maximum_order_quantity=params.maximum_order_quantity,
        )
        for atc, di in demand_inputs.items()
    }
    result = build_optimization_run_result(scenario_result, demand_inputs, recommendations, order_quantities)
    d = result.to_dict()

    return OptimizationRunResponse(
        scenario=d["scenario"],
        assumptions=[AssumptionRow(**a) for a in d["assumptions"]],
        capacity_budget=d["capacity_budget"],
        atc_results={atc: ATCPlanningResultSchema(**v) for atc, v in d["atc_results"].items()},
        allocation_baseline=AllocationPolicySchema(**d["allocation_baseline"]),
        allocation_optimized=AllocationPolicySchema(**d["allocation_optimized"]),
        improvement_pct=d["optimization_summary"]["improvement_pct"],
        warnings=warnings,
    )


def get_scenarios() -> ScenariosResponse:
    return ScenariosResponse(
        scenarios=[
            ScenarioInfo(
                name=name,
                service_level_target=params.service_level_target,
                lead_time_days=params.lead_time_days,
                review_period_days=params.review_period_days,
                rationale=scenarios_module.SCENARIO_RATIONALE.get(name, ""),
            )
            for name, params in scenarios_module.SCENARIOS.items()
        ]
    )


def get_sensitivity(atc_class: str, scenario: ScenarioName, parameter: SensitivityParameter) -> SensitivityResponse:
    if atc_class not in KNOWN_ATC_CLASSES:
        raise NotFoundError(f"Unknown ATC class {atc_class!r}. Known classes: {sorted(KNOWN_ATC_CLASSES)}.")

    demand_inputs = per_class_demand_inputs_or_503()
    di = demand_inputs[atc_class]
    params = scenarios_module.SCENARIOS[scenario.value]
    points = _SWEEP_FUNCS[parameter](di, params)
    elasticity_value = sensitivity_module.elasticity(points)

    return SensitivityResponse(
        atc_class=atc_class,
        parameter=parameter,
        points=[SensitivityPointSchema(value=p.value, safety_stock=p.safety_stock, reorder_point=p.reorder_point) for p in points],
        elasticity=elasticity_value,
    )
