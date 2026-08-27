from app.optimization.runner import run_all_scenario_results, run_optimization
from tests.unit.optimization.helpers import make_demand_input


def _inputs():
    return {
        "A": make_demand_input("A", point_forecast=[20.0] * 14, residual_std=3.0, model="ets", wape=25.0),
        "B": make_demand_input("B", point_forecast=[5.0] * 14, residual_std=1.0, model="naive", wape=90.0),
    }


def test_run_optimization_produces_required_output_fields():
    result = run_optimization("balanced", _inputs())
    d = result.to_dict()
    assert d["scenario"] == "balanced"
    assert len(d["assumptions"]) > 0
    for atc, atc_result in d["atc_results"].items():
        for field in (
            "atc_class", "forecast", "forecast_uncertainty", "lead_time_days", "service_level",
            "safety_stock", "reorder_point", "recommended_order_quantity", "inventory_exposure",
            "expected_shortage", "model_used", "recommendation",
        ):
            assert field in atc_result, f"missing field {field} for {atc}"


def test_run_optimization_forecast_matches_input_unmodified():
    inputs = _inputs()
    result = run_optimization("balanced", inputs)
    assert result.atc_results["A"].forecast == inputs["A"].point_forecast


def test_run_optimization_includes_both_allocation_policies():
    result = run_optimization("balanced", _inputs())
    assert "allocation_baseline" in result.to_dict()
    assert "allocation_optimized" in result.to_dict()
    assert result.allocation_baseline["policy_name"] != result.allocation_optimized["policy_name"]


def test_run_all_scenario_results_covers_three_scenarios():
    results = run_all_scenario_results(_inputs())
    assert set(results.keys()) == {"conservative", "balanced", "lean"}


def test_recommended_order_quantity_is_nonzero_for_nonzero_demand():
    result = run_optimization("balanced", _inputs())
    assert result.atc_results["A"].recommended_order_quantity > 0
