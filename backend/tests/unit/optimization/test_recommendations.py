from app.optimization.recommendations import build_all_recommendations, build_recommendation
from app.optimization.reorder_point import compute_reorder_point
from tests.unit.optimization.helpers import make_demand_input


def test_n02be_is_described_as_high_exposure_not_high_risk():
    di = make_demand_input("N02BE", point_forecast=[300.0] * 14, residual_std=10.0, model="moving_average_14", wape=25.0)
    reorder = compute_reorder_point(di, 7, 0.95)
    rec = build_recommendation("N02BE", di, reorder, "balanced", contribution_pct=49.4)
    assert "high" in rec.recommendation.lower()
    assert "planning exposure" in rec.recommendation.lower() or "PLANNING EXPOSURE" in rec.recommendation
    assert "is high risk" not in rec.recommendation.lower()  # the negated phrasing ("not as 'high risk'") is expected and fine
    assert any("49.4" in e for e in rec.evidence)


def test_n05c_recommendation_checks_absolute_units_not_just_cv():
    di = make_demand_input("N05C", point_forecast=[0.5] * 14, residual_std=0.3, model="naive", wape=100.0)
    reorder = compute_reorder_point(di, 7, 0.95)
    rec = build_recommendation("N05C", di, reorder, "balanced")
    assert any("CV" in e or "cv" in e for e in rec.evidence)
    assert f"{reorder.safety_stock:.2f}" in rec.recommendation
    assert rec.confidence == "low"  # naive model, WAPE > 80 -> low confidence per the evidence rule


def test_r03_recommendation_does_not_cite_growth_as_justification_alone():
    di = make_demand_input("R03", point_forecast=[100.0] * 14, residual_std=15.0, model="moving_average_14", wape=87.6)
    reorder = compute_reorder_point(di, 7, 0.95)
    rec = build_recommendation("R03", di, reorder, "balanced")
    assert any("growth" in e.lower() for e in rec.evidence)
    assert any("worse than" in e.lower() or "not exploitable" in rec.recommendation.lower() for e in rec.evidence + [rec.recommendation])
    assert "not on the m3" in rec.recommendation.lower() or "not based on" in rec.recommendation.lower() or "NOT on the M3" in rec.recommendation


def test_high_uncertainty_class_gets_appropriate_confidence_level():
    high_wape_di = make_demand_input("X", model="linear_regression", wape=45.0)
    low_wape_di = make_demand_input("Y", model="ets", wape=20.0)
    reorder_x = compute_reorder_point(high_wape_di, 7, 0.95)
    reorder_y = compute_reorder_point(low_wape_di, 7, 0.95)
    rec_x = build_recommendation("X", high_wape_di, reorder_x, "balanced")
    rec_y = build_recommendation("Y", low_wape_di, reorder_y, "balanced")
    assert rec_x.confidence in ("low", "medium", "medium-high")
    assert rec_y.confidence == "medium-high"


def test_every_recommendation_has_required_fields_non_empty():
    di = make_demand_input("GENERIC")
    reorder = compute_reorder_point(di, 7, 0.95)
    rec = build_recommendation("GENERIC", di, reorder, "balanced")
    assert rec.recommendation
    assert rec.evidence
    assert rec.assumptions
    assert rec.expected_effect
    assert rec.confidence
    assert rec.limitations
    assert any("Kaggle" in lim for lim in rec.limitations)


def test_build_all_recommendations_covers_every_class():
    inputs = {"A": make_demand_input("A"), "B": make_demand_input("B")}
    reorders = {k: compute_reorder_point(v, 7, 0.95) for k, v in inputs.items()}
    recs = build_all_recommendations(inputs, reorders, "balanced")
    assert set(recs.keys()) == {"A", "B"}
