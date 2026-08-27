"""Wraps app.forecasting (M4, via app.optimization.demand_input's reuse —
M5) for GET /api/v1/forecast/{atc_class}, GET /api/v1/forecast/aggregate,
and GET /api/v1/forecast/{atc_class}/diagnostics.

Never retrains or reruns the M4 backtest per request — reads from
app.services.cache.get_demand_inputs(), which does the (cached, one-time
per process) work of pulling M4's already-selected model, its point
forecast, and its backtested residuals (M6 Sec. 11/26).
"""

from app.api.errors import NotFoundError, ServiceUnavailableError
from app.forecasting import diagnostics as forecasting_diagnostics
from app.schemas.forecasts import (
    ForecastDiagnosticsResponse,
    ForecastMetrics,
    ForecastPoint,
    ForecastResponse,
    HorizonStepError,
    LjungBoxResult,
    ResidualDiagnostics,
)
from app.services import cache
from app.services.atc_registry import KNOWN_FORECAST_ENTITIES


def demand_inputs_or_503():
    try:
        return cache.get_demand_inputs()
    except ValueError as exc:
        raise ServiceUnavailableError(
            "Forecasting models are not available yet — run backend/scripts/run_m4_backtest.py."
        ) from exc


def get_forecast(atc_class: str) -> ForecastResponse:
    inputs = demand_inputs_or_503()
    if atc_class not in inputs:
        raise NotFoundError(f"Unknown ATC class {atc_class!r}. Known classes: {sorted(KNOWN_FORECAST_ENTITIES)}.")
    di = inputs[atc_class]
    fo = di.forecast_output
    return ForecastResponse(
        atc_class=atc_class,
        horizon_days=fo.horizon,
        model=fo.model,
        uncertainty_method=fo.uncertainty_method,
        forecast=[
            ForecastPoint(date=p["date"], prediction=p["point_forecast"], lower=p["lower_bound"], upper=p["upper_bound"])
            for p in fo.predictions
        ],
        metrics=ForecastMetrics(**di.evaluation_metrics),
    )


def get_aggregate_forecast() -> ForecastResponse:
    """M4 empirically found the DIRECT aggregate forecast (test WAPE
    ~16.27%) more accurate than summing the 8 per-class forecasts (test
    WAPE ~18.26%) — see docs/model-selection.md. This reads the "ALL"
    entity's own independently-selected, independently-backtested model;
    it never sums the per-class forecasts (M6 Sec. 12 — that distinction
    must be preserved, not silently replaced)."""
    return get_forecast("ALL")


def get_forecast_diagnostics(atc_class: str) -> ForecastDiagnosticsResponse:
    inputs = demand_inputs_or_503()
    if atc_class not in inputs:
        raise NotFoundError(f"Unknown ATC class {atc_class!r}. Known classes: {sorted(KNOWN_FORECAST_ENTITIES)}.")
    di = inputs[atc_class]

    residual = forecasting_diagnostics.residual_summary(di.fold_results)
    horizon_steps = forecasting_diagnostics.performance_by_horizon_step(di.fold_results)

    ljung_box = None
    lb = residual.get("ljung_box")
    if lb:
        ljung_box = LjungBoxResult(
            lags=lb["lags"], lb_stat=lb["lb_stat"], lb_pvalue=lb["lb_pvalue"], autocorrelation_detected=lb["lb_pvalue"] < 0.05
        )

    limitations = [
        "Residual diagnostics are computed from M4's 6 backtest validation folds — a small sample; read p-values as indicative, not definitive.",
        "This model was chosen by M4's documented selection policy (see docs/model-selection.md), not re-optimized here.",
    ]
    if di.selected_model in ("naive", "moving_average_14", "seasonal_naive_7"):
        limitations.append(f"M4 found no candidate model meaningfully improved on the '{di.selected_model}' baseline for this class.")

    return ForecastDiagnosticsResponse(
        atc_class=atc_class,
        model=di.selected_model,
        metrics=ForecastMetrics(**di.evaluation_metrics),
        residual_diagnostics=ResidualDiagnostics(
            n_residuals=residual.get("n_residuals", 0),
            mean_residual=residual.get("mean_residual"),
            std_residual=residual.get("std_residual"),
            pct_days_underpredicted=residual.get("pct_days_underpredicted"),
            pct_days_overpredicted=residual.get("pct_days_overpredicted"),
            ljung_box=ljung_box,
            interpretation=residual.get("interpretation", ""),
        ),
        performance_by_horizon_step=[HorizonStepError(**h) for h in horizon_steps],
        limitations=limitations,
    )
