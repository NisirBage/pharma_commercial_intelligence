"""Mandatory baseline forecasters (M4 Sec. 4). Every baseline uses ONLY the
training series it's given (values up to and including the forecast
origin) — the same chronological discipline as the statistical/ML
candidates, so comparisons across all models are apples-to-apples.
"""

import numpy as np


def naive_forecast(train_values: np.ndarray, horizon: int) -> np.ndarray:
    """forecast(t+h) = demand(t) for every h — the last observed value
    carried forward flat. The mandatory minimum bar every other model must
    beat."""
    last = float(train_values[-1])
    return np.full(horizon, last, dtype=float)


def seasonal_naive_forecast(train_values: np.ndarray, horizon: int, period: int = 7) -> np.ndarray:
    """forecast(t+h) = demand(t+h-period) — repeats the last observed full
    cycle. `period=7` (weekly) is the grain-appropriate default: M3 found
    a statistically significant (if modest) day-of-week effect at daily
    grain. Falls back to `naive_forecast` if there isn't a full cycle of
    history yet."""
    if len(train_values) < period:
        return naive_forecast(train_values, horizon)
    last_cycle = train_values[-period:]
    reps = int(np.ceil(horizon / period))
    return np.tile(last_cycle, reps)[:horizon].astype(float)


def moving_average_forecast(train_values: np.ndarray, horizon: int, window: int = 14) -> np.ndarray:
    """forecast(t+h) = mean(last `window` observed values) for every h — a
    flat forecast at the trailing average. `window=14` matches the chosen
    forecast horizon (docs/forecasting-methodology.md Sec. 1): long enough
    to smooth day-to-day noise without averaging in demand from over two
    weeks ago, which M3 found isn't representative at daily grain (weak
    weekly seasonality strength of only 0.234)."""
    w = min(window, len(train_values))
    avg = float(np.mean(train_values[-w:]))
    return np.full(horizon, avg, dtype=float)


BASELINES = {
    "naive": lambda train_values, horizon: naive_forecast(train_values, horizon),
    "seasonal_naive_7": lambda train_values, horizon: seasonal_naive_forecast(train_values, horizon, period=7),
    "moving_average_14": lambda train_values, horizon: moving_average_forecast(train_values, horizon, window=14),
}
