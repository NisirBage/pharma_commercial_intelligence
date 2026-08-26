"""Forecast diagnostics (M4 Sec. 12): residual bias, spread, and
autocorrelation, plus performance broken out by fold (time) — so a single
overall error number never hides a systematic failure mode (e.g. the
model consistently underpredicting, or degrading during specific periods).
"""

import numpy as np
from statsmodels.stats.diagnostic import acorr_ljungbox


def residual_summary(fold_results: list[dict]) -> dict:
    """Pools residuals (actual - predicted) across every backtest fold for
    one model/ATC-class combination."""
    if not fold_results:
        return {"reason": "no_data"}
    all_residuals = np.concatenate([np.asarray(r["residuals"], dtype=float) for r in fold_results])
    if len(all_residuals) == 0:
        return {"reason": "no_data"}

    ljung_box = None
    if len(all_residuals) >= 10:
        try:
            lags = min(7, len(all_residuals) - 1)
            lb = acorr_ljungbox(all_residuals, lags=[lags], return_df=True)
            ljung_box = {"lags": lags, "lb_stat": float(lb["lb_stat"].iloc[0]), "lb_pvalue": float(lb["lb_pvalue"].iloc[0])}
        except Exception:
            ljung_box = None

    return {
        "n_residuals": int(len(all_residuals)),
        "mean_residual": float(np.mean(all_residuals)),
        "std_residual": float(np.std(all_residuals)),
        "pct_days_underpredicted": float(np.mean(all_residuals > 0) * 100),  # actual > predicted
        "pct_days_overpredicted": float(np.mean(all_residuals < 0) * 100),  # actual < predicted
        "ljung_box": ljung_box,
        "interpretation": (
            "mean_residual > 0 => systematic underprediction on average; < 0 => systematic overprediction. "
            "ljung_box.lb_pvalue < 0.05 => residuals show significant autocorrelation, meaning the model is "
            "leaving predictable structure on the table rather than producing white-noise errors."
        ),
    }


def performance_by_fold(fold_results: list[dict]) -> list[dict]:
    """One row per backtest fold — lets a reviewer see whether error grows
    over time, spikes in a particular period, or is stable."""
    return [
        {
            "fold_id": r["fold_id"],
            "validation_start_date": r["validation_start_date"],
            "validation_end_date": r["validation_end_date"],
            "mae": r["mae"],
            "wape": r["wape"],
        }
        for r in fold_results
    ]


def performance_by_horizon_step(fold_results: list[dict]) -> list[dict]:
    """MAE at each individual step of the forecast horizon (step 1 = next
    day, step H = the last day of the horizon), pooled across folds —
    reveals whether error compounds across the horizon (a known risk of
    the recursive ML forecasting strategy in app.forecasting.ml_models)."""
    if not fold_results:
        return []
    horizon = max(len(r["residuals"]) for r in fold_results)
    out = []
    for step in range(horizon):
        abs_errors = [abs(r["residuals"][step]) for r in fold_results if len(r["residuals"]) > step]
        if abs_errors:
            out.append({"horizon_step": step + 1, "mae": float(np.mean(abs_errors)), "n_observations": len(abs_errors)})
    return out
