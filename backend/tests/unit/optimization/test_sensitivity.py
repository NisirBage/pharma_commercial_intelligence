from app.optimization.sensitivity import (
    elasticity,
    sensitivity_report,
    sweep_demand_uncertainty,
    sweep_lead_time,
    sweep_service_level,
    sweep_stockout_cost_weight,
)
from tests.unit.optimization.helpers import make_demand_input


def test_sweep_lead_time_is_monotonically_increasing():
    di = make_demand_input(residual_std=2.0)
    points = sweep_lead_time(di, service_level_target=0.95)
    values = [p.safety_stock for p in points]
    assert values == sorted(values)


def test_sweep_service_level_is_monotonically_increasing():
    di = make_demand_input(residual_std=2.0)
    points = sweep_service_level(di, lead_time_days=7)
    values = [p.safety_stock for p in points]
    assert values == sorted(values)


def test_sweep_demand_uncertainty_is_monotonically_increasing():
    di = make_demand_input(residual_std=2.0)
    points = sweep_demand_uncertainty(di, lead_time_days=7, service_level_target=0.95)
    values = [p.safety_stock for p in points]
    assert values == sorted(values)


def test_sweep_stockout_cost_weight_is_monotonically_non_decreasing():
    di = make_demand_input(residual_std=2.0)
    points = sweep_stockout_cost_weight(di, lead_time_days=7, holding_cost_weight=1.0)
    values = [p.safety_stock for p in points]
    assert values == sorted(values)


def test_sensitivity_report_covers_all_four_parameters():
    di = make_demand_input(residual_std=2.0)
    report = sensitivity_report(di, lead_time_days=7, service_level_target=0.95)
    assert set(report.keys()) == {"lead_time_days", "service_level_target", "demand_uncertainty_scale", "stockout_cost_weight"}


def test_elasticity_of_service_level_is_positive():
    di = make_demand_input(residual_std=2.0)
    points = sweep_service_level(di, lead_time_days=7)
    assert elasticity(points) > 0


def test_elasticity_none_for_single_point():
    assert elasticity([]) is None
    di = make_demand_input()
    points = sweep_lead_time(di, 0.95, lead_times=(7,))
    assert elasticity(points) is None
