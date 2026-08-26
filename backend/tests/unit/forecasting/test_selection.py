import pytest

from app.forecasting.selection import IMPROVEMENT_THRESHOLD_PCT, select_model


def _summaries(**wapes):
    return {name: {"mae": 1.0, "rmse": 1.0, "wape": wape, "mase": 1.0} for name, wape in wapes.items()}


def test_baseline_selected_when_no_candidate_clears_the_threshold():
    summaries = _summaries(naive=10.0, seasonal_naive_7=9.0, moving_average_14=11.0, linear_regression=8.8)  # <5% better
    result = select_model("M01AB", summaries)
    assert result.selected_model == "seasonal_naive_7"
    assert "No candidate model improved" in result.reason


def test_candidate_selected_when_it_clears_the_threshold():
    summaries = _summaries(naive=10.0, seasonal_naive_7=10.0, moving_average_14=10.0, random_forest=8.0)  # 20% better
    result = select_model("M01AB", summaries)
    assert result.selected_model == "random_forest"
    assert result.improvement_pct == pytest.approx(20.0)


def test_parsimony_tiebreak_prefers_simpler_model_within_tolerance():
    # random_forest is marginally best, but linear_regression is within the
    # 2% parsimony tolerance and is simpler -> linear_regression should win
    summaries = _summaries(naive=10.0, seasonal_naive_7=10.0, moving_average_14=10.0, linear_regression=8.0, random_forest=7.9)
    result = select_model("M01AB", summaries)
    assert result.selected_model == "linear_regression"


def test_clear_winner_outside_tolerance_beats_simpler_model():
    summaries = _summaries(naive=10.0, seasonal_naive_7=10.0, moving_average_14=10.0, linear_regression=9.0, random_forest=6.0)
    result = select_model("M01AB", summaries)
    assert result.selected_model == "random_forest"


def test_raises_without_any_baseline_wape():
    with pytest.raises(ValueError, match="No baseline WAPE"):
        select_model("M01AB", {"random_forest": {"mae": 1, "rmse": 1, "wape": 5.0, "mase": 1}})


def test_improvement_threshold_constant_is_reasonable():
    assert 0 < IMPROVEMENT_THRESHOLD_PCT < 50
