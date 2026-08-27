"""Synthetic DemandInput builders for the optimization test suite —
deterministic, no randomness, no dependency on real data or the M4
registry."""

from app.optimization.demand_input import DemandInput


def make_demand_input(
    atc_class: str = "TEST",
    model: str = "ets",
    point_forecast: list[float] | None = None,
    residual_std: float = 2.0,
    wape: float = 30.0,
    horizon: int = 14,
    n_folds: int = 6,
) -> DemandInput:
    point_forecast = point_forecast or [10.0] * horizon
    return DemandInput(
        atc_class=atc_class,
        selected_model=model,
        evaluation_metrics={"mae": 1.0, "rmse": 1.5, "wape": wape, "mase": 0.7},
        point_forecast=point_forecast,
        forecast_dates=[f"2020-01-{i+1:02d}" for i in range(horizon)],
        historical_daily_demand=[10.0] * 100,
        residual_std_by_step=[residual_std] * horizon,
        fold_cumulative_errors={L: [0.0] * n_folds for L in range(1, horizon + 1)},
        forecast_output=None,
    )
