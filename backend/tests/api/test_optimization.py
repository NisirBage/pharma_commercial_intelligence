import pytest

from app.optimization.allocation_optimizer import AllocationResult
from app.optimization.scenarios import ScenarioResult
from app.services import optimization_service


def test_run_balanced_scenario(client):
    response = client.post("/api/v1/optimization/run", json={"scenario": "balanced"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["scenario"] == "balanced"
    assert len(data["atc_results"]) == 8
    assert data["allocation_baseline"]["policy_name"] != data["allocation_optimized"]["policy_name"]


def test_run_conservative_scenario_has_higher_budget_than_lean(client):
    conservative = client.post("/api/v1/optimization/run", json={"scenario": "conservative"}).json()["data"]
    lean = client.post("/api/v1/optimization/run", json={"scenario": "lean"}).json()["data"]
    assert conservative["capacity_budget"] > lean["capacity_budget"]


def test_run_default_scenario_is_balanced(client):
    response = client.post("/api/v1/optimization/run", json={})
    assert response.status_code == 200
    assert response.json()["data"]["scenario"] == "balanced"


def test_run_with_service_level_override(client):
    response = client.post("/api/v1/optimization/run", json={"scenario": "balanced", "service_level": 0.99})
    assert response.status_code == 200
    # a 99% override should require at least as much budget as the 95% default
    default_budget = client.post("/api/v1/optimization/run", json={"scenario": "balanced"}).json()["data"]["capacity_budget"]
    assert response.json()["data"]["capacity_budget"] >= default_budget


def test_run_assumptions_are_disclosed_and_labeled(client):
    response = client.post("/api/v1/optimization/run", json={"scenario": "balanced"})
    assumptions = response.json()["data"]["assumptions"]
    assert len(assumptions) > 0
    for row in assumptions:
        assert row["source"] == "scenario"
        assert row["type"] == "assumption"


def test_run_invalid_scenario_returns_422(client):
    response = client.post("/api/v1/optimization/run", json={"scenario": "aggressive"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_run_invalid_service_level_returns_422(client):
    response = client.post("/api/v1/optimization/run", json={"scenario": "balanced", "service_level": 1.5})
    assert response.status_code == 422

    response2 = client.post("/api/v1/optimization/run", json={"scenario": "balanced", "service_level": 0.0})
    assert response2.status_code == 422


def test_run_invalid_lead_time_returns_422(client):
    response = client.post("/api/v1/optimization/run", json={"scenario": "balanced", "lead_time_days": -1})
    assert response.status_code == 422

    response2 = client.post("/api/v1/optimization/run", json={"scenario": "balanced", "lead_time_days": 100})
    assert response2.status_code == 422


def test_scenarios_endpoint_lists_all_three(client):
    response = client.get("/api/v1/optimization/scenarios")
    assert response.status_code == 200
    names = {s["name"] for s in response.json()["data"]["scenarios"]}
    assert names == {"conservative", "balanced", "lean"}


def test_sensitivity_valid_request(client):
    response = client.get(
        "/api/v1/optimization/sensitivity",
        params={"atc_class": "N02BE", "scenario": "balanced", "parameter": "service_level_target"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["atc_class"] == "N02BE"
    assert len(data["points"]) > 1


def test_sensitivity_invalid_atc_returns_404(client):
    response = client.get(
        "/api/v1/optimization/sensitivity",
        params={"atc_class": "ZZZ", "scenario": "balanced", "parameter": "lead_time_days"},
    )
    assert response.status_code == 404


def test_sensitivity_invalid_parameter_returns_422(client):
    response = client.get(
        "/api/v1/optimization/sensitivity",
        params={"atc_class": "N02BE", "scenario": "balanced", "parameter": "phase_of_the_moon"},
    )
    assert response.status_code == 422


def test_run_optimization_infeasible_status_returns_422(monkeypatch):
    """Simulates the solver reporting infeasibility (this LP formulation
    is always feasible in normal operation, since capacity_budget is
    always derived non-negative and z=0/SS=0 is always a feasible point —
    this test exercises the ERROR-HANDLING path, not a real infeasible
    input, by injecting a rigged solver status)."""
    from app.schemas.optimization import OptimizationRunRequest, ScenarioName

    demand_inputs = optimization_service.per_class_demand_inputs_or_503()
    real_result = optimization_service.scenarios_module.run_scenario("balanced", demand_inputs)
    rigged_optimized = AllocationResult(
        total_capacity_budget=real_result.optimized_allocation.total_capacity_budget,
        total_safety_stock_allocated=0.0,
        total_expected_shortage=0.0,
        total_weighted_expected_shortage=0.0,
        per_class={},
        solver_status="infeasible",
        policy_name="optimized (rigged for test)",
    )
    rigged_result = ScenarioResult(
        scenario_name=real_result.scenario_name,
        parameters=real_result.parameters,
        rationale=real_result.rationale,
        independent_reorder_points=real_result.independent_reorder_points,
        capacity_budget=real_result.capacity_budget,
        baseline_allocation=real_result.baseline_allocation,
        optimized_allocation=rigged_optimized,
    )

    monkeypatch.setattr(optimization_service.scenarios_module, "run_scenario", lambda *a, **k: rigged_result)

    with pytest.raises(Exception) as exc_info:
        optimization_service.run_optimization(OptimizationRunRequest(scenario=ScenarioName.balanced))
    assert getattr(exc_info.value, "code", None) == "optimization_infeasible"
