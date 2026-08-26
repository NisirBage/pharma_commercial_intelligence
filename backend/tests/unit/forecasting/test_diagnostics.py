import pytest

from app.forecasting.diagnostics import performance_by_fold, performance_by_horizon_step, residual_summary


def _fold_results():
    return [
        {
            "fold_id": 1,
            "validation_start_date": "2020-01-01",
            "validation_end_date": "2020-01-03",
            "mae": 1.0,
            "wape": 10.0,
            "residuals": [1.0, -1.0, 2.0],  # actual - predicted
        },
        {
            "fold_id": 2,
            "validation_start_date": "2020-02-01",
            "validation_end_date": "2020-02-03",
            "mae": 2.0,
            "wape": 20.0,
            "residuals": [3.0, -3.0, 0.0],
        },
    ]


def test_residual_summary_computes_bias_and_spread():
    summary = residual_summary(_fold_results())
    assert summary["n_residuals"] == 6
    assert summary["mean_residual"] == (1 - 1 + 2 + 3 - 3 + 0) / 6
    assert summary["pct_days_underpredicted"] == pytest.approx(3 / 6 * 100)  # residuals > 0: 1,2,3 -> 3 of 6
    assert summary["pct_days_overpredicted"] == pytest.approx(2 / 6 * 100)  # residuals < 0: -1,-3 -> 2 of 6


def test_residual_summary_empty_input():
    assert residual_summary([]) == {"reason": "no_data"}


def test_performance_by_fold_returns_one_row_per_fold():
    rows = performance_by_fold(_fold_results())
    assert len(rows) == 2
    assert rows[0]["fold_id"] == 1
    assert rows[1]["mae"] == 2.0


def test_performance_by_horizon_step_pools_across_folds_per_step():
    rows = performance_by_horizon_step(_fold_results())
    assert len(rows) == 3  # horizon = 3
    # step 1 (index 0): |1.0| and |3.0| -> mean 2.0
    assert rows[0]["horizon_step"] == 1
    assert rows[0]["mae"] == 2.0
    assert rows[0]["n_observations"] == 2


def test_performance_by_horizon_step_empty_input():
    assert performance_by_horizon_step([]) == []
