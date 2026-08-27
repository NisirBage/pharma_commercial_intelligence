"""Sensitivity analysis on the 4 assumptions M5 explicitly calls out:
lead time, service level, demand uncertainty, and the stockout-cost
weight. Implemented as direct parameter sweeps through the closed-form
calculations in app.optimization.safety_stock/reorder_point — no solver
needed here, since this is about a SINGLE class's own policy, not the
cross-class allocation (app.optimization.allocation_optimizer covers
sensitivity of THAT to its shared-budget/weight inputs separately, via
the scenario comparison in app.optimization.scenarios).
"""

import dataclasses
from dataclasses import dataclass

from app.optimization.demand_input import DemandInput
from app.optimization.reorder_point import compute_reorder_point
from app.optimization.safety_stock import newsvendor_critical_fractile_z

DEFAULT_LEAD_TIME_GRID: tuple[int, ...] = (1, 3, 5, 7, 10, 14)
DEFAULT_SERVICE_LEVEL_GRID: tuple[float, ...] = (0.80, 0.90, 0.95, 0.98, 0.99)
DEFAULT_UNCERTAINTY_SCALE_GRID: tuple[float, ...] = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
DEFAULT_STOCKOUT_WEIGHT_GRID: tuple[float, ...] = (0.5, 1.0, 2.0, 4.0, 8.0)


@dataclass
class SensitivityPoint:
    parameter: str
    value: float
    safety_stock: float
    reorder_point: float


def sweep_lead_time(
    demand_input: DemandInput, service_level_target: float, lead_times: tuple[int, ...] = DEFAULT_LEAD_TIME_GRID
) -> list[SensitivityPoint]:
    return [
        SensitivityPoint("lead_time_days", lt, r.safety_stock, r.reorder_point)
        for lt in lead_times
        for r in [compute_reorder_point(demand_input, lt, service_level_target)]
    ]


def sweep_service_level(
    demand_input: DemandInput, lead_time_days: int, service_levels: tuple[float, ...] = DEFAULT_SERVICE_LEVEL_GRID
) -> list[SensitivityPoint]:
    return [
        SensitivityPoint("service_level_target", sl, r.safety_stock, r.reorder_point)
        for sl in service_levels
        for r in [compute_reorder_point(demand_input, lead_time_days, sl)]
    ]


def sweep_demand_uncertainty(
    demand_input: DemandInput,
    lead_time_days: int,
    service_level_target: float,
    scale_factors: tuple[float, ...] = DEFAULT_UNCERTAINTY_SCALE_GRID,
) -> list[SensitivityPoint]:
    """Scales the forecast-error std by a factor (simulating "what if our
    forecast were this much more/less uncertain") — a direct scenario
    perturbation of the M4-sourced uncertainty input, NOT a re-forecast."""
    results = []
    for scale in scale_factors:
        scaled = dataclasses.replace(
            demand_input, residual_std_by_step=[s * scale for s in demand_input.residual_std_by_step]
        )
        r = compute_reorder_point(scaled, lead_time_days, service_level_target)
        results.append(SensitivityPoint("demand_uncertainty_scale", scale, r.safety_stock, r.reorder_point))
    return results


def sweep_stockout_cost_weight(
    demand_input: DemandInput,
    lead_time_days: int,
    holding_cost_weight: float,
    stockout_weights: tuple[float, ...] = DEFAULT_STOCKOUT_WEIGHT_GRID,
) -> list[SensitivityPoint]:
    """Uses the newsvendor critical fractile (app.optimization.safety_stock)
    to translate a stockout/holding cost-weight ratio into an IMPLIED
    service level, then the usual reorder-point calculation. This is the
    one place stockout_cost_weight has a non-degenerate effect on a
    single class's own policy — see the note in
    app.optimization.safety_stock.newsvendor_critical_fractile_z about
    why a uniform global weight doesn't change the cross-class LP's
    optimal allocation."""
    results = []
    for stockout_weight in stockout_weights:
        z = newsvendor_critical_fractile_z(stockout_weight, holding_cost_weight)
        from scipy.stats import norm

        implied_service_level = float(norm.cdf(z))
        r = compute_reorder_point(demand_input, lead_time_days, implied_service_level)
        results.append(SensitivityPoint("stockout_cost_weight", stockout_weight, r.safety_stock, r.reorder_point))
    return results


def sensitivity_report(
    demand_input: DemandInput, lead_time_days: int, service_level_target: float, holding_cost_weight: float = 1.0
) -> dict[str, list[SensitivityPoint]]:
    return {
        "lead_time_days": sweep_lead_time(demand_input, service_level_target),
        "service_level_target": sweep_service_level(demand_input, lead_time_days),
        "demand_uncertainty_scale": sweep_demand_uncertainty(demand_input, lead_time_days, service_level_target),
        "stockout_cost_weight": sweep_stockout_cost_weight(demand_input, lead_time_days, holding_cost_weight),
    }


def elasticity(points: list[SensitivityPoint]) -> float | None:
    """Endpoint-to-endpoint % change in safety stock per % change in the
    swept parameter — a simple, comparable summary of "how much does this
    assumption move the recommendation?" across the 4 swept parameters.
    None when either endpoint value is 0 (percentage change undefined)."""
    if len(points) < 2:
        return None
    first, last = points[0], points[-1]
    if first.value == 0 or first.safety_stock == 0:
        return None
    pct_change_ss = (last.safety_stock - first.safety_stock) / first.safety_stock
    pct_change_param = (last.value - first.value) / first.value
    if pct_change_param == 0:
        return None
    return float(pct_change_ss / pct_change_param)
