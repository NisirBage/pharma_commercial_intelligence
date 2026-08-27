"""Named planning scenarios: Conservative / Balanced / Lean. They differ
ONLY in `service_level_target` (and, downstream, the shared capacity
budget that target implies) — every other assumption
(app.optimization.assumptions.ScenarioParameters defaults) stays fixed,
so any difference in the results is attributable to the service-level
choice alone, not a mix of confounded changes.

Each scenario's shared capacity budget is derived from its OWN
service-level target, applied independently to every class and summed —
i.e. "what would an uncoordinated, everyone-gets-this-target policy cost
in total safety stock?" The optimized (LP) allocation is then given that
SAME total budget, so its comparison against the baseline is always
apples to apples: same total inventory exposure, different allocation
across classes.
"""

from dataclasses import dataclass

from app.optimization.allocation_optimizer import (
    AllocationResult,
    default_class_weights,
    optimize_allocation,
    proportional_baseline_allocation,
)
from app.optimization.assumptions import ScenarioParameters
from app.optimization.demand_input import DemandInput
from app.optimization.reorder_point import ReorderPointResult, compute_reorder_point

SCENARIOS: dict[str, ScenarioParameters] = {
    "conservative": ScenarioParameters(service_level_target=0.98),
    "balanced": ScenarioParameters(service_level_target=0.95),
    "lean": ScenarioParameters(service_level_target=0.90),
}

SCENARIO_RATIONALE: dict[str, str] = {
    "conservative": (
        "Highest service-level target (98%) — prioritizes stockout avoidance over inventory exposure. "
        "A planner who weights the operational/patient-access cost of a stockout heavily would choose this."
    ),
    "balanced": (
        "Middle service-level target (95%) — this project's default; a conventional 'reasonable' target used "
        "in inventory-planning teaching material absent other information about actual business priorities."
    ),
    "lean": (
        "Lowest service-level target (90%) — prioritizes minimizing inventory exposure over stockout avoidance. "
        "A capital- or space-constrained planner would choose this, accepting more frequent (small) shortfalls."
    ),
}


@dataclass
class ScenarioResult:
    scenario_name: str
    parameters: ScenarioParameters
    rationale: str
    independent_reorder_points: dict[str, ReorderPointResult]  # per-class, uncoordinated (no shared-budget constraint)
    capacity_budget: float  # sum of the independent safety stocks above
    baseline_allocation: AllocationResult
    optimized_allocation: AllocationResult


def run_scenario(
    scenario_name: str, demand_inputs: dict[str, DemandInput], params: ScenarioParameters | None = None
) -> ScenarioResult:
    params = params or SCENARIOS[scenario_name]

    independent_rop = {
        atc: compute_reorder_point(di, params.lead_time_days, params.service_level_target)
        for atc, di in demand_inputs.items()
    }
    capacity_budget = (
        params.shared_capacity_budget
        if params.shared_capacity_budget is not None
        else sum(r.safety_stock for r in independent_rop.values())
    )

    weights = default_class_weights(demand_inputs)
    baseline = proportional_baseline_allocation(
        demand_inputs, params.lead_time_days, capacity_budget, reference_service_level=params.service_level_target, class_weights=weights
    )
    optimized = optimize_allocation(
        demand_inputs, params.lead_time_days, capacity_budget, stockout_cost_weight=params.stockout_cost_weight, class_weights=weights
    )

    return ScenarioResult(
        scenario_name=scenario_name,
        parameters=params,
        rationale=SCENARIO_RATIONALE.get(scenario_name, "custom scenario"),
        independent_reorder_points=independent_rop,
        capacity_budget=capacity_budget,
        baseline_allocation=baseline,
        optimized_allocation=optimized,
    )


def run_all_scenarios(demand_inputs: dict[str, DemandInput]) -> dict[str, ScenarioResult]:
    return {name: run_scenario(name, demand_inputs) for name in SCENARIOS}
