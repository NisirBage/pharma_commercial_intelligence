"""Forecast evaluation metrics. MAE/RMSE are the primary metrics; WAPE and
MASE are included for cross-series comparability. Plain MAPE is
deliberately NOT implemented: daily per-ATC demand contains genuine zero
days (M1/M3 found the dataset-wide daily minimum is exactly 0.0, and
low-volume classes like N05C have many zero days), which makes
point-wise percentage error undefined/infinite for a meaningful fraction
of observations. WAPE (a ratio of SUMS, not of individual points) does
not have this problem and is used in its place.
"""

import numpy as np


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(np.asarray(actual) - np.asarray(predicted))))


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((np.asarray(actual) - np.asarray(predicted)) ** 2)))


def wape(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    """Weighted Absolute Percentage Error = sum(|actual-pred|) / sum(|actual|) * 100.
    Undefined (returns None, not inf) only when every actual in the window
    is exactly zero."""
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    denom = np.sum(np.abs(actual))
    if denom == 0:
        return None
    return float(np.sum(np.abs(actual - predicted)) / denom * 100)


def mase(actual: np.ndarray, predicted: np.ndarray, train_series: np.ndarray, seasonal_period: int = 1) -> float | None:
    """Mean Absolute Scaled Error (Hyndman & Koehler 2006): MAE of the
    forecast, scaled by the in-sample MAE of a naive (or seasonal-naive,
    with `seasonal_period`) forecast on the TRAINING period only — never
    the validation/test period, which would leak future information into
    the scale itself. MASE < 1 means the model beats that naive in-sample
    benchmark; MASE > 1 means it's worse.
    Undefined (returns None) when the training series is constant (the
    naive in-sample MAE is 0), which would otherwise divide by zero."""
    train_series = np.asarray(train_series, dtype=float)
    if len(train_series) <= seasonal_period:
        return None
    naive_errors = np.abs(train_series[seasonal_period:] - train_series[:-seasonal_period])
    scale = float(np.mean(naive_errors))
    if scale == 0:
        return None
    return float(mae(actual, predicted) / scale)


def evaluate(
    actual: np.ndarray, predicted: np.ndarray, train_series: np.ndarray, seasonal_period: int = 7
) -> dict[str, float | None]:
    return {
        "mae": mae(actual, predicted),
        "rmse": rmse(actual, predicted),
        "wape": wape(actual, predicted),
        "mase": mase(actual, predicted, train_series, seasonal_period=seasonal_period),
    }
