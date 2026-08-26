"""Rolling-origin (expanding-window) backtesting. No random splitting,
ever — every fold's training window ends strictly before its validation
window begins, and training windows only ever grow forward in time. See
docs/forecasting-methodology.md Sec. 3 for the exact fold dates used in
this project.

Common forecaster interface every baseline/statistical/ML model is
adapted to: `forecaster(train_df: pd.DataFrame, horizon: int) -> np.ndarray`,
where `train_df` holds only rows up to and including the fold's
`train_end_date` (strictly chronological — the forecaster never sees
anything from the validation window or beyond).
"""

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from app.forecasting.metrics import evaluate

DATE_COL = "observation_date"
TARGET_COL = "units_sold"

Forecaster = Callable[[pd.DataFrame, int], np.ndarray]


@dataclass
class Fold:
    fold_id: int
    train_end_date: pd.Timestamp  # inclusive — last day the model may see
    validation_start_date: pd.Timestamp  # = train_end_date + 1 day
    validation_end_date: pd.Timestamp  # = validation_start_date + horizon - 1


def generate_folds(dates: pd.DatetimeIndex, horizon: int, n_folds: int, min_train_days: int) -> list[Fold]:
    """Evenly-spaced expanding-window fold origins across the ELIGIBLE
    range only. Callers must pass the eligible sub-range (i.e. already
    excluding any final held-out test horizon) — this function has no
    concept of a "test set", only of what history is long enough to train
    and validate on."""
    n = len(dates)
    last_train_end_idx = n - horizon - 1  # need `horizon` more days after train_end for validation
    first_train_end_idx = min_train_days - 1
    if last_train_end_idx < first_train_end_idx:
        raise ValueError(
            f"Not enough history to generate any fold: need >= {min_train_days + horizon} days, got {n}."
        )
    if n_folds == 1 or last_train_end_idx == first_train_end_idx:
        origin_indices = [last_train_end_idx]
    else:
        origin_indices = sorted(
            {int(round(i)) for i in np.linspace(first_train_end_idx, last_train_end_idx, num=n_folds)}
        )

    folds = []
    for fold_id, idx in enumerate(origin_indices, start=1):
        train_end = dates[idx]
        val_start = dates[idx + 1]
        val_end = dates[idx + horizon]
        folds.append(Fold(fold_id, train_end, val_start, val_end))
    return folds


def to_array_forecaster(fn: Callable[[np.ndarray, int], np.ndarray]) -> Forecaster:
    """Adapts a (train_values: np.ndarray, horizon) -> array function
    (e.g. every function in app.forecasting.baselines) to the common
    (train_df, horizon) -> array interface."""

    def _forecaster(train_df: pd.DataFrame, horizon: int) -> np.ndarray:
        return fn(train_df[TARGET_COL].to_numpy(), horizon)

    return _forecaster


def run_backtest(
    series_df: pd.DataFrame,
    forecaster: Forecaster,
    folds: list[Fold],
    seasonal_period: int = 7,
) -> list[dict]:
    """series_df: the FULL series (columns [observation_date, units_sold]),
    strictly chronological, no gaps (app.forecasting.datasets guarantees
    this). Returns one result dict per fold with actual/predicted arrays
    and every metric from app.forecasting.metrics.evaluate."""
    results = []
    for fold in folds:
        train_df = series_df[series_df[DATE_COL] <= fold.train_end_date]
        val_mask = (series_df[DATE_COL] >= fold.validation_start_date) & (
            series_df[DATE_COL] <= fold.validation_end_date
        )
        actual = series_df.loc[val_mask, TARGET_COL].to_numpy()
        horizon = len(actual)

        predicted = np.asarray(forecaster(train_df, horizon), dtype=float)[:horizon]
        train_values = train_df[TARGET_COL].to_numpy()
        metrics_result = evaluate(actual, predicted, train_values, seasonal_period=seasonal_period)

        results.append(
            {
                "fold_id": fold.fold_id,
                "train_end_date": str(fold.train_end_date.date()),
                "validation_start_date": str(fold.validation_start_date.date()),
                "validation_end_date": str(fold.validation_end_date.date()),
                "n_train_days": int(len(train_df)),
                "horizon": int(horizon),
                "actual": actual.tolist(),
                "predicted": predicted.tolist(),
                "residuals": (actual - predicted).tolist(),
                **metrics_result,
            }
        )
    return results


def summarize_backtest(fold_results: list[dict]) -> dict[str, float | None]:
    """Mean of each metric across folds — the number used for model
    comparison/selection (app.forecasting.selection)."""
    if not fold_results:
        return {"mae": None, "rmse": None, "wape": None, "mase": None}
    out = {}
    for metric_name in ("mae", "rmse", "wape", "mase"):
        values = [r[metric_name] for r in fold_results if r[metric_name] is not None]
        out[metric_name] = float(np.mean(values)) if values else None
    return out
