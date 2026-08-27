"""Optimization validation: monotonicity sanity checks (M5 Sec. 17).
These are executable checks used both in production runs and in the test
suite — not just assertions written in documentation.
"""

import dataclasses

from app.optimization.demand_input import DemandInput
from app.optimization.reorder_point import compute_reorder_point

DEFAULT_SERVICE_LEVEL_GRID: tuple[float, ...] = (0.80, 0.90, 0.95, 0.98, 0.99)
DEFAULT_LEAD_TIME_GRID: tuple[int, ...] = (1, 3, 5, 7, 10, 14)
DEFAULT_UNCERTAINTY_SCALE_GRID: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0)
_TOLERANCE = 1e-9


def check_service_level_monotonic(
    demand_input: DemandInput, lead_time_days: int, service_levels: tuple[float, ...] = DEFAULT_SERVICE_LEVEL_GRID
) -> tuple[bool, str]:
    """Increasing the service-level target must never DECREASE safety
    stock (z is monotonic increasing in service level above 50%)."""
    values = [compute_reorder_point(demand_input, lead_time_days, sl).safety_stock for sl in service_levels]
    ok = all(b >= a - _TOLERANCE for a, b in zip(values, values[1:]))
    return ok, f"safety_stock by service_level: {list(zip(service_levels, values))}"


def check_lead_time_monotonic(
    demand_input: DemandInput, service_level_target: float, lead_times: tuple[int, ...] = DEFAULT_LEAD_TIME_GRID
) -> tuple[bool, str]:
    """Increasing lead time must not decrease the reorder point (more
    days of expected demand, plus a wider uncertainty window to protect
    against)."""
    values = [compute_reorder_point(demand_input, lt, service_level_target).reorder_point for lt in lead_times]
    ok = all(b >= a - _TOLERANCE for a, b in zip(values, values[1:]))
    return ok, f"reorder_point by lead_time: {list(zip(lead_times, values))}"


def check_uncertainty_monotonic(
    demand_input: DemandInput,
    lead_time_days: int,
    service_level_target: float,
    scale_factors: tuple[float, ...] = DEFAULT_UNCERTAINTY_SCALE_GRID,
) -> tuple[bool, str]:
    """Increasing demand-forecast uncertainty must not decrease the
    required safety stock."""
    values = []
    for scale in scale_factors:
        scaled = dataclasses.replace(
            demand_input, residual_std_by_step=[s * scale for s in demand_input.residual_std_by_step]
        )
        values.append(compute_reorder_point(scaled, lead_time_days, service_level_target).safety_stock)
    ok = all(b >= a - _TOLERANCE for a, b in zip(values, values[1:]))
    return ok, f"safety_stock by uncertainty_scale: {list(zip(scale_factors, values))}"


def run_all_validations(demand_input: DemandInput, lead_time_days: int, service_level_target: float) -> dict[str, dict]:
    checks = {
        "service_level_monotonic": check_service_level_monotonic(demand_input, lead_time_days),
        "lead_time_monotonic": check_lead_time_monotonic(demand_input, service_level_target),
        "uncertainty_monotonic": check_uncertainty_monotonic(demand_input, lead_time_days, service_level_target),
    }
    return {name: {"passed": ok, "detail": detail} for name, (ok, detail) in checks.items()}
