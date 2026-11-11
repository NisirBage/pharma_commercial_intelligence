
from app.optimization.scenarios import SCENARIOS, run_all_scenarios, run_scenario
from tests.unit.optimization.helpers import make_demand_input


def _inputs():
    return {
        "A": make_demand_input("A", point_forecast=[20.0] * 14, residual_std=3.0),
        "B": make_demand_input("B", point_forecast=[5.0] * 14, residual_std=1.0),
    }


def test_conservative_balanced_lean_have_expected_service_levels():
    assert SCENARIOS["conservative"].service_level_target == 0.98
    assert SCENARIOS["balanced"].service_level_target == 0.95
    assert SCENARIOS["lean"].service_level_target == 0.90


def test_conservative_requires_more_capacity_than_lean():
    inputs = _inputs()
    conservative = run_scenario("conservative", inputs)
    balanced = run_scenario("balanced", inputs)
    lean = run_scenario("lean", inputs)
    assert conservative.capacity_budget > balanced.capacity_budget > lean.capacity_budget


def test_run_all_scenarios_covers_all_three():
    results = run_all_scenarios(_inputs())
    assert set(results.keys()) == {"conservative", "balanced", "lean"}
    for result in results.values():
        assert result.optimized_allocation.solver_status == "optimal"


def test_scenario_optimized_never_worse_than_baseline():
    for name, result in run_all_scenarios(_inputs()).items():
        assert result.optimized_allocation.total_weighted_expected_shortage <= (
            result.baseline_allocation.total_weighted_expected_shortage + 1e-6
        ), f"optimized worse than baseline in {name} scenario"


def test_each_scenario_has_a_documented_rationale():
    for name, result in run_all_scenarios(_inputs()).items():
        assert isinstance(result.rationale, str) and len(result.rationale) > 10
