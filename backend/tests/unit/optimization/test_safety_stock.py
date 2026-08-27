import pytest
from scipy.stats import norm

from app.optimization.safety_stock import (
    compute_safety_stock,
    newsvendor_critical_fractile_z,
    sigma_lead_time_additive,
    sigma_lead_time_empirical_fold,
    sigma_lead_time_flat_sqrt,
)
from tests.unit.optimization.helpers import make_demand_input


def test_normal_demand_safety_stock_is_positive_and_uses_correct_z():
    di = make_demand_input(residual_std=2.0)
    result = compute_safety_stock(di, lead_time_days=7, service_level_target=0.95)
    expected_z = norm.ppf(0.95)
    assert result.z_score == pytest.approx(expected_z)
    assert result.safety_stock > 0
    assert result.safety_stock == pytest.approx(expected_z * result.sigma_lead_time_primary)


def test_high_volatility_gives_higher_safety_stock_than_low_volatility():
    low = compute_safety_stock(make_demand_input(residual_std=1.0), 7, 0.95)
    high = compute_safety_stock(make_demand_input(residual_std=5.0), 7, 0.95)
    assert high.safety_stock > low.safety_stock


def test_zero_volatility_gives_zero_safety_stock():
    di = make_demand_input(residual_std=0.0)
    result = compute_safety_stock(di, lead_time_days=7, service_level_target=0.95)
    assert result.safety_stock == 0.0
    assert result.sigma_lead_time_primary == 0.0


def test_different_service_levels_change_safety_stock_monotonically():
    di = make_demand_input(residual_std=2.0)
    values = [compute_safety_stock(di, 7, sl).safety_stock for sl in (0.80, 0.90, 0.95, 0.98, 0.99)]
    assert values == sorted(values)
    assert len(set(values)) == len(values)  # strictly increasing, not flat


def test_zero_lead_time_gives_zero_safety_stock():
    di = make_demand_input(residual_std=2.0)
    result = compute_safety_stock(di, lead_time_days=0, service_level_target=0.95)
    assert result.safety_stock == 0.0
    assert result.lead_time_days == 0


def test_lead_time_beyond_forecast_horizon_raises():
    di = make_demand_input(horizon=14)
    with pytest.raises(ValueError, match="forecast horizon"):
        compute_safety_stock(di, lead_time_days=15, service_level_target=0.95)


def test_invalid_service_level_raises():
    di = make_demand_input()
    with pytest.raises(ValueError):
        compute_safety_stock(di, 7, 1.5)
    with pytest.raises(ValueError):
        compute_safety_stock(di, 7, 0.0)


def test_negative_lead_time_raises():
    di = make_demand_input()
    with pytest.raises(ValueError):
        compute_safety_stock(di, -1, 0.95)


def test_sigma_estimators_agree_on_constant_step_std():
    """When every horizon step has the SAME residual std, the additive
    and flat-sqrt estimators must produce identical results (both reduce
    to std_1 * sqrt(L) in that special case)."""
    di = make_demand_input(residual_std=3.0)
    additive = sigma_lead_time_additive(di, 7)
    flat = sigma_lead_time_flat_sqrt(di, 7)
    assert additive == pytest.approx(flat)


def test_empirical_fold_estimator_none_with_insufficient_folds():
    di = make_demand_input(n_folds=1)
    assert sigma_lead_time_empirical_fold(di, 7) is None


def test_newsvendor_critical_fractile_symmetric_costs_gives_z_zero():
    z = newsvendor_critical_fractile_z(stockout_cost_weight=1.0, holding_cost_weight=1.0)
    assert z == pytest.approx(0.0, abs=1e-9)


def test_newsvendor_critical_fractile_higher_stockout_weight_gives_higher_z():
    z_low = newsvendor_critical_fractile_z(1.0, 1.0)
    z_high = newsvendor_critical_fractile_z(4.0, 1.0)
    assert z_high > z_low


def test_newsvendor_critical_fractile_requires_positive_weights():
    with pytest.raises(ValueError):
        newsvendor_critical_fractile_z(0.0, 0.0)
    with pytest.raises(ValueError):
        newsvendor_critical_fractile_z(-1.0, 1.0)
