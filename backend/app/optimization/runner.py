"""Top-level orchestration — the function a future
`POST /api/v1/optimization/run` handler would call directly (M5 Sec. 15).
Wires together every other module in this package; introduces no new
planning logic of its own.
"""

from app.optimization import scenarios as scenarios_module
from app.optimization.demand_input import DemandInput
from app.optimization.outputs import OptimizationRunResult, build_optimization_run_result
from app.optimization.recommendations import build_all_recommendations
from app.optimization.reorder_point import compute_scenario_order_quantity


def run_optimization(
    scenario_name: str, demand_inputs: dict[str, DemandInput], contributions: dict[str, float] | None = None
) -> OptimizationRunResult:
    scenario_result = scenarios_module.run_scenario(scenario_name, demand_inputs)
    recommendations = build_all_recommendations(
        demand_inputs, scenario_result.independent_reorder_points, scenario_name, contributions
    )
    order_quantities = {
        atc: compute_scenario_order_quantity(
            di,
            ordering_cost_weight=scenario_result.parameters.ordering_cost_weight,
            holding_cost_weight=scenario_result.parameters.holding_cost_weight,
            minimum_order_quantity=scenario_result.parameters.minimum_order_quantity,
            maximum_order_quantity=scenario_result.parameters.maximum_order_quantity,
        )
        for atc, di in demand_inputs.items()
    }
    return build_optimization_run_result(scenario_result, demand_inputs, recommendations, order_quantities)


def run_all_scenario_results(
    demand_inputs: dict[str, DemandInput], contributions: dict[str, float] | None = None
) -> dict[str, OptimizationRunResult]:
    return {name: run_optimization(name, demand_inputs, contributions) for name in scenarios_module.SCENARIOS}
