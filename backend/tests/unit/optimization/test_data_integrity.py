"""Data-integrity tests (M5 Sec. 16): observed data is never overwritten,
scenario assumptions stay separate from observed data, forecasts are not
mutated by optimization, and optimization never reaches into historical/
future actual demand it shouldn't."""

import copy
import dataclasses

import pytest

from app.optimization.allocation_optimizer import optimize_allocation
from app.optimization.assumptions import ScenarioParameters
from app.optimization.reorder_point import compute_reorder_point
from app.optimization.safety_stock import compute_safety_stock
from tests.unit.optimization.helpers import make_demand_input


def test_compute_safety_stock_does_not_mutate_demand_input():
    di = make_demand_input(residual_std=2.0)
    before = copy.deepcopy(di.residual_std_by_step)
    compute_safety_stock(di, 7, 0.95)
    assert di.residual_std_by_step == before


def test_compute_reorder_point_does_not_mutate_forecast():
    di = make_demand_input(point_forecast=[10.0] * 14)
    before = list(di.point_forecast)
    compute_reorder_point(di, 7, 0.95)
    assert di.point_forecast == before


def test_optimize_allocation_does_not_mutate_any_demand_input():
    inputs = {"A": make_demand_input("A", residual_std=2.0), "B": make_demand_input("B", residual_std=4.0)}
    before = {k: copy.deepcopy(v) for k, v in inputs.items()}
    optimize_allocation(inputs, lead_time_days=7, capacity_budget=20.0)
    for k in inputs:
        assert inputs[k].point_forecast == before[k].point_forecast
        assert inputs[k].residual_std_by_step == before[k].residual_std_by_step


def test_scenario_parameters_are_immutable():
    params = ScenarioParameters()
    with pytest.raises(dataclasses.FrozenInstanceError):
        params.lead_time_days = 99


def test_every_assumption_row_is_labeled_assumption_not_observed():
    params = ScenarioParameters()
    rows = params.as_assumption_rows()
    assert len(rows) > 0
    for row in rows:
        assert row["source"] == "scenario"
        assert row["type"] == "assumption"


def test_reorder_point_uses_forecast_not_historical_demand():
    """The lead-time-demand component must come from the FORECAST, not
    from historical actuals -- proven by changing historical_daily_demand
    (which should have zero effect) while leaving point_forecast fixed."""
    di = make_demand_input(point_forecast=[10.0] * 14)
    baseline = compute_reorder_point(di, 7, 0.95)

    mutated = dataclasses.replace(di, historical_daily_demand=[99999.0] * 100)
    mutated_result = compute_reorder_point(mutated, 7, 0.95)

    assert mutated_result.expected_demand_during_lead_time == baseline.expected_demand_during_lead_time
    assert mutated_result.reorder_point == baseline.reorder_point


def test_lead_time_demand_never_exceeds_the_forecast_horizon_available():
    """Structural guarantee against reaching past the M4 forecast window
    into any actual future demand: lead_time_days beyond the forecast
    horizon must raise, never silently pull in extra (real) data."""
    di = make_demand_input(horizon=14)
    with pytest.raises(ValueError):
        compute_reorder_point(di, lead_time_days=15, service_level_target=0.95)
