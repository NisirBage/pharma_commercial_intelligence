import pytest

from app.optimization.reorder_point import (
    compute_order_up_to_level,
    compute_reorder_point,
    compute_scenario_order_quantity,
)
from tests.unit.optimization.helpers import make_demand_input


def test_reorder_point_equals_lead_time_demand_plus_safety_stock():
    di = make_demand_input(point_forecast=[10.0] * 14, residual_std=2.0)
    result = compute_reorder_point(di, lead_time_days=5, service_level_target=0.95)
    assert result.expected_demand_during_lead_time == pytest.approx(50.0)
    assert result.reorder_point == pytest.approx(50.0 + result.safety_stock)


def test_reorder_point_varies_with_lead_time():
    di = make_demand_input(point_forecast=[10.0] * 14, residual_std=2.0)
    values = [compute_reorder_point(di, lt, 0.95).reorder_point for lt in (1, 3, 7, 14)]
    assert values == sorted(values)
    assert len(set(values)) == len(values)


def test_zero_lead_time_reorder_point_is_zero():
    di = make_demand_input(point_forecast=[10.0] * 14)
    result = compute_reorder_point(di, lead_time_days=0, service_level_target=0.95)
    assert result.reorder_point == 0.0


def test_reorder_point_scales_with_demand_level():
    low_demand = make_demand_input(point_forecast=[5.0] * 14, residual_std=1.0)
    high_demand = make_demand_input(point_forecast=[50.0] * 14, residual_std=1.0)
    r_low = compute_reorder_point(low_demand, 7, 0.95)
    r_high = compute_reorder_point(high_demand, 7, 0.95)
    assert r_high.reorder_point > r_low.reorder_point
    assert r_high.expected_demand_during_lead_time == pytest.approx(10 * r_low.expected_demand_during_lead_time)


def test_order_up_to_level_covers_lead_time_plus_review_period():
    di = make_demand_input(point_forecast=[10.0] * 14, residual_std=2.0)
    result = compute_order_up_to_level(di, lead_time_days=5, review_period_days=5, service_level_target=0.95)
    assert result.expected_demand_during_protection_interval == pytest.approx(100.0)  # 10 days * 10 units


def test_order_up_to_level_beyond_horizon_raises():
    di = make_demand_input(horizon=14)
    with pytest.raises(ValueError, match="forecast horizon"):
        compute_order_up_to_level(di, lead_time_days=10, review_period_days=10, service_level_target=0.95)


def test_scenario_order_quantity_increases_with_demand_and_ordering_cost():
    di_low = make_demand_input(point_forecast=[10.0] * 14)
    di_high = make_demand_input(point_forecast=[40.0] * 14)
    q_low = compute_scenario_order_quantity(di_low, ordering_cost_weight=1.0, holding_cost_weight=1.0)
    q_high = compute_scenario_order_quantity(di_high, ordering_cost_weight=1.0, holding_cost_weight=1.0)
    assert q_high > q_low

    q_more_ordering_cost = compute_scenario_order_quantity(di_low, ordering_cost_weight=10.0, holding_cost_weight=1.0)
    assert q_more_ordering_cost > q_low


def test_scenario_order_quantity_respects_min_and_max():
    di = make_demand_input(point_forecast=[1.0] * 14)  # tiny demand -> tiny natural EOQ
    q_floored = compute_scenario_order_quantity(di, 1.0, 1.0, minimum_order_quantity=100.0)
    assert q_floored == 100.0

    di_big = make_demand_input(point_forecast=[1000.0] * 14)
    q_capped = compute_scenario_order_quantity(di_big, 1.0, 1.0, maximum_order_quantity=5.0)
    assert q_capped == 5.0


def test_scenario_order_quantity_requires_positive_holding_weight():
    di = make_demand_input()
    with pytest.raises(ValueError):
        compute_scenario_order_quantity(di, ordering_cost_weight=1.0, holding_cost_weight=0.0)
