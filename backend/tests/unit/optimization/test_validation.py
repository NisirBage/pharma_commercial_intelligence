from app.optimization.validation import (
    check_lead_time_monotonic,
    check_service_level_monotonic,
    check_uncertainty_monotonic,
    run_all_validations,
)
from tests.unit.optimization.helpers import make_demand_input


def test_service_level_monotonic_passes_for_well_behaved_input():
    di = make_demand_input(residual_std=2.0)
    ok, _ = check_service_level_monotonic(di, lead_time_days=7)
    assert ok


def test_lead_time_monotonic_passes_for_well_behaved_input():
    di = make_demand_input(point_forecast=[10.0] * 14, residual_std=2.0)
    ok, _ = check_lead_time_monotonic(di, service_level_target=0.95)
    assert ok


def test_uncertainty_monotonic_passes_for_well_behaved_input():
    di = make_demand_input(residual_std=2.0)
    ok, _ = check_uncertainty_monotonic(di, lead_time_days=7, service_level_target=0.95)
    assert ok


def test_run_all_validations_returns_all_three_checks_passing():
    di = make_demand_input(point_forecast=[10.0] * 14, residual_std=2.0)
    results = run_all_validations(di, lead_time_days=7, service_level_target=0.95)
    assert set(results.keys()) == {"service_level_monotonic", "lead_time_monotonic", "uncertainty_monotonic"}
    assert all(r["passed"] for r in results.values())


def test_zero_volatility_series_still_passes_monotonicity_trivially():
    di = make_demand_input(residual_std=0.0)
    results = run_all_validations(di, lead_time_days=7, service_level_target=0.95)
    assert all(r["passed"] for r in results.values())
