"""Cross-class, capacity-constrained safety-stock allocation — the ONE
genuine optimization problem in this milestone. See
docs/optimization-methodology.md Sec. 7 for why the per-class reorder-
point/safety-stock calculation (app.optimization.safety_stock,
app.optimization.reorder_point) is deterministic/closed-form and does
NOT need a solver, while this cross-class allocation genuinely does.

**The problem.** Given a shared, hypothetical inventory capacity budget
(total safety-stock units across all ATC classes — a scenario
assumption, never observed), decide how much of that budget each class
gets, to MINIMIZE total PLANNING-EXPOSURE-WEIGHTED expected shortage.

**Why weighted, not a plain unweighted sum — a real finding, not a
stylistic choice.** For safety stock SS with z = SS/sigma_L, expected
shortage is `sigma_L * L(z)` (Hadley & Whitin's unit-normal loss
function), and its derivative w.r.t. SS is `-(1 - Phi(z))` — INDEPENDENT
OF sigma_L. That means minimizing an *unweighted* sum of per-class
expected shortage has, as its exact mathematical optimum, giving EVERY
class the same implied service level — which is precisely what the naive
"same target for everyone, scaled to fit the budget" baseline already
does. An early implementation of this module used an unweighted objective
and a synthetic sanity check (`tests/unit/optimization/test_allocation_optimizer.py`)
showed the LP could not beat that baseline even in principle — not a bug,
a mathematical fact about the unweighted formulation. Weighting each
class's shortage by its OWN planning exposure (`class_weight`, default:
average forecast daily demand normalized to a mean of 1.0 across the
classes being allocated — i.e. "a stockout unit in a higher-volume class
counts for more," directly operationalizing M5's own framing of N02BE as
high planning exposure) breaks that degeneracy: the optimum then
allocates a HIGHER implied service level to higher-weight classes, which
a same-service-level-for-everyone baseline cannot replicate. This weight
is a SCENARIO CHOICE (a proxy for exposure, not a real cost) — see
docs/optimization-methodology.md and docs/planning-assumptions.md.

**Formulation.** Reformulated as a linear program via the standard convex
piecewise-linear trick: precompute expected shortage at a DENSE grid of
z-values per class (`_LP_Z_GRID`, step 0.1 from z=0 to z=2.5), then let
each class pick a CONTINUOUS convex combination of grid points. Because
`L(z)` is convex and the LP MINIMIZES a linear combination of it subject
to a linear resource constraint, the LP relaxation is exact — no
integer/SOS2 variables needed — PROVIDED the grid is fine enough that
chord-interpolation error is negligible (a coarser 6-point grid was tried
first and found NOT fine enough; see the module history in version
control / the docstring in earlier commits).

Solved with OR-Tools' GLOP linear solver — a genuine LP, not a
keyword-driven use of the library. The dense-grid values are used only
internally to drive the solver; every REPORTED expected-shortage number
(for both the optimized and baseline policies) is recomputed from the
solved safety stock using the exact normal-loss formula, so the two
policies are compared on the same accurate metric.
"""

from dataclasses import dataclass

import numpy as np
from ortools.linear_solver import pywraplp
from scipy.stats import norm

from app.optimization.assumptions import SERVICE_LEVEL_TIERS
from app.optimization.demand_input import DemandInput
from app.optimization.safety_stock import sigma_lead_time_additive

# Dense z-grid for the LP's internal piecewise-linear approximation of the
# (convex) unit-normal-loss function — see module docstring. Capped at
# z=3.5 (implied service level ~99.98%) for a finite LP; any scenario
# whose capacity budget would need a HIGHER per-class service level than
# that for every class combined is far outside the realistic 90-99%
# range this project's scenarios use (docs/optimization-methodology.md) —
# documented as a modeling boundary, not silently extended indefinitely.
_LP_Z_GRID: tuple[float, ...] = tuple(np.round(np.linspace(0.0, 3.5, 36), 4))


def unit_normal_loss(z: float) -> float:
    """L(z) = phi(z) - z*(1 - Phi(z)) — expected units short per cycle,
    in standard-deviation units, for a safety factor z."""
    return float(norm.pdf(z) - z * (1 - norm.cdf(z)))


def default_class_weights(demand_inputs: dict[str, DemandInput]) -> dict[str, float]:
    """Planning-exposure weight per class: average forecast daily demand,
    normalized so the mean weight across classes is 1.0 — a class with
    twice the average volume gets weight 2.0. This is a SCENARIO PROXY
    for "how much a stockout unit matters," not a real cost (see module
    docstring and docs/planning-assumptions.md)."""
    avg_demand = {atc: sum(di.point_forecast) / len(di.point_forecast) for atc, di in demand_inputs.items()}
    mean_of_means = sum(avg_demand.values()) / len(avg_demand) if avg_demand else 1.0
    if mean_of_means <= 0:
        return {atc: 1.0 for atc in demand_inputs}
    return {atc: v / mean_of_means for atc, v in avg_demand.items()}


@dataclass
class ClassAllocationTier:
    service_level: float
    z_score: float
    safety_stock: float
    expected_shortage: float  # exact normal-loss value at this tier


@dataclass
class ClassAllocationResult:
    atc_class: str
    safety_stock: float
    expected_shortage: float  # exact normal-loss value at the solved safety_stock (not the LP's internal linear approx)
    implied_service_level: float
    class_weight: float


@dataclass
class AllocationResult:
    total_capacity_budget: float
    total_safety_stock_allocated: float
    total_expected_shortage: float
    total_weighted_expected_shortage: float
    per_class: dict[str, ClassAllocationResult]
    solver_status: str
    policy_name: str


_STATUS_NAMES = {
    pywraplp.Solver.OPTIMAL: "optimal",
    pywraplp.Solver.FEASIBLE: "feasible",
    pywraplp.Solver.INFEASIBLE: "infeasible",
    pywraplp.Solver.UNBOUNDED: "unbounded",
}


def build_tiers(sigma_lead_time: float, z_grid: tuple[float, ...] = _LP_Z_GRID) -> list[ClassAllocationTier]:
    result = []
    for z in z_grid:
        ss = z * sigma_lead_time
        shortage = sigma_lead_time * unit_normal_loss(z) if sigma_lead_time > 0 else 0.0
        result.append(ClassAllocationTier(service_level=float(norm.cdf(z)), z_score=z, safety_stock=ss, expected_shortage=shortage))
    return result


def _exact_shortage_and_service_level(safety_stock: float, sigma_lead_time: float) -> tuple[float, float]:
    if sigma_lead_time <= 0:
        return 0.0, 1.0
    implied_z = safety_stock / sigma_lead_time
    return sigma_lead_time * unit_normal_loss(implied_z), float(norm.cdf(implied_z))


def optimize_allocation(
    demand_inputs: dict[str, DemandInput],
    lead_time_days: int,
    capacity_budget: float,
    stockout_cost_weight: float = 1.0,
    class_weights: dict[str, float] | None = None,
) -> AllocationResult:
    """OPTIMIZED policy: minimizes
    `sum_i(stockout_cost_weight * class_weight_i * expected_shortage_i)`
    subject to `sum_i(safety_stock_i) <= capacity_budget`. `class_weights`
    defaults to `default_class_weights` (volume-proportional planning
    exposure) — see the module docstring for why an unweighted objective
    would make this optimization mathematically pointless."""
    weights = class_weights or default_class_weights(demand_inputs)

    solver = pywraplp.Solver.CreateSolver("GLOP")
    if solver is None:
        raise RuntimeError("OR-Tools GLOP solver unavailable in this environment.")

    class_tiers: dict[str, list[ClassAllocationTier]] = {}
    weight_vars: dict[str, list] = {}
    objective = solver.Objective()
    objective.SetMinimization()
    capacity_constraint = solver.Constraint(-solver.infinity(), capacity_budget, "capacity_budget")

    for atc_class, di in demand_inputs.items():
        sigma_lead_time = sigma_lead_time_additive(di, lead_time_days)
        tiers = build_tiers(sigma_lead_time)
        class_tiers[atc_class] = tiers

        convex_combination = solver.Constraint(1.0, 1.0, f"convex_{atc_class}")
        class_vars = []
        for i, tier in enumerate(tiers):
            var = solver.NumVar(0.0, 1.0, f"w_{atc_class}_{i}")
            class_vars.append(var)
            convex_combination.SetCoefficient(var, 1.0)
            capacity_constraint.SetCoefficient(var, tier.safety_stock)
            objective.SetCoefficient(var, stockout_cost_weight * weights[atc_class] * tier.expected_shortage)
        weight_vars[atc_class] = class_vars

    status = solver.Solve()
    status_name = _STATUS_NAMES.get(status, "unknown")

    per_class: dict[str, ClassAllocationResult] = {}
    total_ss, total_shortage, total_weighted_shortage = 0.0, 0.0, 0.0
    for atc_class, tiers in class_tiers.items():
        if status_name not in ("optimal", "feasible"):
            per_class[atc_class] = ClassAllocationResult(atc_class, 0.0, 0.0, 0.0, weights[atc_class])
            continue
        ss = sum(v.solution_value() * t.safety_stock for v, t in zip(weight_vars[atc_class], tiers))
        sigma_lead_time = sigma_lead_time_additive(demand_inputs[atc_class], lead_time_days)
        shortage, implied_service_level = _exact_shortage_and_service_level(ss, sigma_lead_time)
        per_class[atc_class] = ClassAllocationResult(atc_class, float(ss), shortage, implied_service_level, weights[atc_class])
        total_ss += ss
        total_shortage += shortage
        total_weighted_shortage += shortage * weights[atc_class]

    return AllocationResult(
        total_capacity_budget=capacity_budget,
        total_safety_stock_allocated=total_ss,
        total_expected_shortage=total_shortage,
        total_weighted_expected_shortage=total_weighted_shortage,
        per_class=per_class,
        solver_status=status_name,
        policy_name="optimized (LP, OR-Tools GLOP, volume-weighted)",
    )


def proportional_baseline_allocation(
    demand_inputs: dict[str, DemandInput],
    lead_time_days: int,
    capacity_budget: float,
    reference_service_level: float = 0.95,
    class_weights: dict[str, float] | None = None,
) -> AllocationResult:
    """BASELINE policy: give every class the SAME service-level target
    (a simple, non-optimized heuristic — no solver, and critically, NOT
    weighted by volume/exposure), then scale every class's resulting
    safety stock proportionally so the total exactly fits the shared
    capacity budget. Used ONLY as the comparison point for
    optimize_allocation()'s LP result — `class_weights` is accepted only
    so the two policies' WEIGHTED totals are comparable on the same
    weights; it plays no role in the baseline's own allocation decision,
    which is exactly the point of contrast (see module docstring)."""
    if reference_service_level not in SERVICE_LEVEL_TIERS:
        raise ValueError(f"reference_service_level must be one of {sorted(SERVICE_LEVEL_TIERS)}")
    z = SERVICE_LEVEL_TIERS[reference_service_level]
    weights = class_weights or default_class_weights(demand_inputs)

    raw_ss = {
        atc_class: z * sigma_lead_time_additive(di, lead_time_days) for atc_class, di in demand_inputs.items()
    }
    raw_total = sum(raw_ss.values())
    scale = capacity_budget / raw_total if raw_total > 0 else 0.0

    per_class: dict[str, ClassAllocationResult] = {}
    total_ss, total_shortage, total_weighted_shortage = 0.0, 0.0, 0.0
    for atc_class, di in demand_inputs.items():
        ss = raw_ss[atc_class] * scale
        sigma_lead_time = sigma_lead_time_additive(di, lead_time_days)
        shortage, implied_service_level = _exact_shortage_and_service_level(ss, sigma_lead_time)
        per_class[atc_class] = ClassAllocationResult(atc_class, float(ss), shortage, implied_service_level, weights[atc_class])
        total_ss += ss
        total_shortage += shortage
        total_weighted_shortage += shortage * weights[atc_class]

    return AllocationResult(
        total_capacity_budget=capacity_budget,
        total_safety_stock_allocated=total_ss,
        total_expected_shortage=total_shortage,
        total_weighted_expected_shortage=total_weighted_shortage,
        per_class=per_class,
        solver_status="heuristic (no solver)",
        policy_name=f"baseline (equal service level={reference_service_level:.0%}, unweighted)",
    )
