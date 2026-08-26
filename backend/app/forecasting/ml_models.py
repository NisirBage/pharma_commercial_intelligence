"""ML candidates: Linear Regression and Random Forest, both trained on the
leakage-safe lag/rolling/calendar features from app.forecasting.features,
then applied RECURSIVELY to produce the full multi-step horizon — each
step's own forecast is fed back into the working history so the NEXT
step's lag/rolling features can reference it, exactly as a real deployment
would have to (the alternative, "direct" multi-horizon modeling — one
model per horizon step — was not used, to keep the model count and
runtime bounded; the tradeoff is that recursive forecasting can compound
errors across the horizon, which is measured directly in
docs/forecasting-insights.md's diagnostics section).

XGBoost was considered and deliberately NOT used — see
docs/forecasting-methodology.md Sec. 5: sklearn's RandomForestRegressor is
sufficient at this data scale (~2000 rows/class), and adding a new heavy
dependency for an unproven marginal benefit would be overengineering per
this project's stated principles.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from app.forecasting.features import DATE_COL, TARGET_COL, build_feature_frame, make_training_table

RANDOM_SEED = 42


def _recursive_forecast(model, history_df: pd.DataFrame, horizon: int, feature_cols: list[str]) -> np.ndarray:
    """history_df: [observation_date, units_sold] up to and including the
    forecast origin, strictly chronological. Extends it one day at a time:
    append a placeholder row for the next date, compute its features
    (which — by construction, see app.forecasting.features — never use
    that row's own target value), predict, then write the prediction into
    the placeholder so it becomes real input for the step after."""
    working = history_df[[DATE_COL, TARGET_COL]].copy()
    last_date = working[DATE_COL].max()
    predictions = []

    for step in range(horizon):
        next_date = last_date + pd.Timedelta(days=step + 1)
        working = pd.concat(
            [working, pd.DataFrame({DATE_COL: [next_date], TARGET_COL: [np.nan]})], ignore_index=True
        )
        featured = build_feature_frame(working, TARGET_COL, DATE_COL)
        row = featured.iloc[[-1]][feature_cols]

        na_mask = row.isna().any(axis=0)
        if na_mask.any():
            raise ValueError(f"NaN feature(s) forecasting step {step + 1}: {row.columns[na_mask].tolist()}")

        pred = max(float(model.predict(row)[0]), 0.0)  # demand volume cannot be negative
        predictions.append(pred)
        working.loc[working.index[-1], TARGET_COL] = pred

    return np.array(predictions)


def make_ml_forecaster(estimator_factory):
    """`estimator_factory` is a zero-arg callable returning an unfitted
    sklearn-API estimator, so a fresh model is trained per fold — never
    reused across folds, which would otherwise leak a later fold's fit
    into an earlier one's evaluation."""

    def _forecaster(train_df: pd.DataFrame, horizon: int) -> np.ndarray:
        featured = build_feature_frame(train_df, TARGET_COL, DATE_COL)
        X, y, feature_cols = make_training_table(featured, TARGET_COL)
        if len(X) == 0:
            # Insufficient warm-up history in this fold's training window
            # for even one complete feature row — fall back to the trailing
            # mean rather than fail the whole backtest.
            return np.full(horizon, float(train_df[TARGET_COL].mean()), dtype=float)
        model = estimator_factory()
        model.fit(X, y)
        return _recursive_forecast(model, train_df, horizon, feature_cols)

    return _forecaster


def linear_regression_forecaster():
    return make_ml_forecaster(lambda: LinearRegression())


def random_forest_forecaster(n_estimators: int = 200, max_depth: int = 8):
    return make_ml_forecaster(
        lambda: RandomForestRegressor(
            n_estimators=n_estimators, max_depth=max_depth, random_state=RANDOM_SEED, n_jobs=-1
        )
    )
