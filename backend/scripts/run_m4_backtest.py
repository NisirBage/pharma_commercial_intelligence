"""Runs the complete M4 forecasting backtest against the REAL dataset:
builds per-ATC (+ aggregate) daily series, backtests every baseline and
candidate model across chronological rolling-origin folds, applies the
model-selection policy, evaluates the winner on a final untouched test
holdout, runs diagnostics, checks the per-class-vs-aggregate question, and
generates the final future forecast + model registry records.

This is the source of every number in docs/forecasting-methodology.md,
docs/model-selection.md, docs/forecasting-insights.md, and the M4
completion report. Results are also dumped to
backend/data/model_registry/m4_backtest_results.json for reference.

Usage (from backend/): python scripts/run_m4_backtest.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from app.analytics.data_access import load_from_raw_csv
from app.forecasting import diagnostics, registry, selection
from app.forecasting.backtesting import generate_folds, run_backtest, summarize_backtest, to_array_forecaster
from app.forecasting.baselines import BASELINES
from app.forecasting.datasets import build_all_series
from app.forecasting.features import FEATURE_COLUMNS
from app.forecasting.metrics import evaluate
from app.forecasting.ml_models import linear_regression_forecaster, random_forest_forecaster
from app.forecasting.predictions import generate_forecast
from app.forecasting.statistical_models import make_ets_forecaster

RAW_DIR = Path("../data/raw")
HORIZON = 14
N_FOLDS = 6
MIN_TRAIN_DAYS = 180
SEASONAL_PERIOD = 7

MODEL_FORECASTER_FACTORIES = {
    "naive": lambda: to_array_forecaster(BASELINES["naive"]),
    "seasonal_naive_7": lambda: to_array_forecaster(BASELINES["seasonal_naive_7"]),
    "moving_average_14": lambda: to_array_forecaster(BASELINES["moving_average_14"]),
    "linear_regression": linear_regression_forecaster,
    "random_forest": random_forest_forecaster,
    "ets": lambda: make_ets_forecaster(seasonal_period=SEASONAL_PERIOD),
}


def main() -> None:
    t_start = time.time()
    df = load_from_raw_csv(RAW_DIR)
    series_by_entity = build_all_series(df)
    print(f"Built {len(series_by_entity)} series: {list(series_by_entity.keys())}")

    results: dict = {"entities": {}}

    for entity, prep in series_by_entity.items():
        t_entity = time.time()
        full_frame = prep.frame
        test_start = full_frame["observation_date"].max() - pd.Timedelta(days=HORIZON - 1)
        eligible = full_frame[full_frame["observation_date"] < test_start]
        test_actual = full_frame[full_frame["observation_date"] >= test_start]["units_sold"].to_numpy()

        folds = generate_folds(eligible["observation_date"], horizon=HORIZON, n_folds=N_FOLDS, min_train_days=MIN_TRAIN_DAYS)

        model_fold_results = {}
        model_summaries = {}
        for model_name, factory in MODEL_FORECASTER_FACTORIES.items():
            forecaster = factory()
            fold_results = run_backtest(eligible, forecaster, folds, seasonal_period=SEASONAL_PERIOD)
            model_fold_results[model_name] = fold_results
            model_summaries[model_name] = summarize_backtest(fold_results)

        sel = selection.select_model(entity, model_summaries)

        # Final held-out TEST evaluation (never used for selection) —
        # train on everything up to test_start, predict the true last
        # HORIZON days, compare once.
        test_train_df = full_frame[full_frame["observation_date"] < test_start]
        selected_forecaster = MODEL_FORECASTER_FACTORIES[sel.selected_model]()
        test_predicted = np.asarray(selected_forecaster(test_train_df, HORIZON), dtype=float)
        test_metrics = evaluate(test_actual, test_predicted, test_train_df["units_sold"].to_numpy(), seasonal_period=SEASONAL_PERIOD)

        baseline_forecaster = MODEL_FORECASTER_FACTORIES[sel.best_baseline_model]()
        baseline_test_predicted = np.asarray(baseline_forecaster(test_train_df, HORIZON), dtype=float)
        baseline_test_metrics = evaluate(test_actual, baseline_test_predicted, test_train_df["units_sold"].to_numpy(), seasonal_period=SEASONAL_PERIOD)

        selected_fold_results = model_fold_results[sel.selected_model]
        diag = {
            "residual_summary": diagnostics.residual_summary(selected_fold_results),
            "performance_by_fold": diagnostics.performance_by_fold(selected_fold_results),
            "performance_by_horizon_step": diagnostics.performance_by_horizon_step(selected_fold_results),
        }

        # Final future forecast (beyond the whole dataset's last date),
        # using the FULL series and the selected model.
        forecast_output = generate_forecast(
            full_frame,
            entity,
            sel.selected_model,
            selected_fold_results,
            horizon=HORIZON,
            seasonal_period=SEASONAL_PERIOD,
            evaluation=model_summaries[sel.selected_model],
        )

        if sel.selected_model in ("linear_regression", "random_forest"):
            record_features = list(FEATURE_COLUMNS)
        else:
            record_features = []

        if sel.selected_model == "random_forest":
            record_hyperparameters = {"n_estimators": 200, "max_depth": 8, "random_state": 42}
        elif sel.selected_model in ("seasonal_naive_7", "ets"):
            record_hyperparameters = {"seasonal_period": SEASONAL_PERIOD}
        elif sel.selected_model == "moving_average_14":
            record_hyperparameters = {"window": 14}
        else:
            record_hyperparameters = {}

        dataset_hash = registry.dataset_version_hash(RAW_DIR)
        record = registry.ModelRecord(
            model_name=sel.selected_model,
            atc_class=entity,
            training_period=f"{eligible['observation_date'].min().date()}/{eligible['observation_date'].max().date()}",
            validation_period=f"{folds[0].validation_start_date.date()}/{folds[-1].validation_end_date.date()}",
            forecast_horizon=HORIZON,
            features=record_features,
            hyperparameters=record_hyperparameters,
            evaluation_metrics=model_summaries[sel.selected_model],
            trained_at=registry.now_iso(),
            dataset_version_hash=dataset_hash,
        )
        registry.save_record(record)

        print(
            f"\n=== {entity} ({time.time()-t_entity:.1f}s) ===\n"
            f"  validation WAPE by model: { {k: round(v['wape'], 2) if v['wape'] is not None else None for k, v in model_summaries.items()} }\n"
            f"  SELECTED: {sel.selected_model} | reason: {sel.reason}\n"
            f"  TEST holdout ({test_start.date()} -> {full_frame['observation_date'].max().date()}): "
            f"selected={test_metrics} vs best_baseline({sel.best_baseline_model})={baseline_test_metrics}\n"
        )

        results["entities"][entity] = {
            "n_days": prep.n_days,
            "start_date": str(prep.start_date.date()),
            "end_date": str(prep.end_date.date()),
            "folds": [
                {"fold_id": f.fold_id, "train_end": str(f.train_end_date.date()), "val_start": str(f.validation_start_date.date()), "val_end": str(f.validation_end_date.date())}
                for f in folds
            ],
            "model_summaries": model_summaries,
            "selection": {
                "selected_model": sel.selected_model,
                "selected_wape": sel.selected_wape,
                "best_baseline_model": sel.best_baseline_model,
                "best_baseline_wape": sel.best_baseline_wape,
                "improvement_pct": sel.improvement_pct,
                "reason": sel.reason,
            },
            "test_holdout": {
                "test_start": str(test_start.date()),
                "test_end": str(full_frame["observation_date"].max().date()),
                "selected_model_metrics": test_metrics,
                "best_baseline_metrics": baseline_test_metrics,
            },
            "diagnostics": diag,
            "future_forecast": forecast_output.to_dict(),
        }

    # Per-ATC vs aggregate comparison: sum of per-class forecasts vs
    # direct aggregate forecast, evaluated on the SAME final test window.
    print("\n=== Per-ATC vs aggregate comparison (final test window) ===")
    atc_codes = [e for e in series_by_entity if e != "ALL"]
    agg_test_start = series_by_entity["ALL"].frame["observation_date"].max() - pd.Timedelta(days=HORIZON - 1)
    agg_test_actual = series_by_entity["ALL"].frame[series_by_entity["ALL"].frame["observation_date"] >= agg_test_start]["units_sold"].to_numpy()

    # Sum each class's SELECTED model applied to ITS OWN final test window
    # (same dates as the aggregate's test window, since all series share
    # the same date range) for a fair apples-to-apples comparison against
    # the direct aggregate model's test-window forecast.
    summed_per_class_test_predicted = np.zeros(HORIZON)
    for atc in atc_codes:
        prep = series_by_entity[atc]
        atc_test_start = prep.frame["observation_date"].max() - pd.Timedelta(days=HORIZON - 1)
        atc_train_df = prep.frame[prep.frame["observation_date"] < atc_test_start]
        model_name = results["entities"][atc]["selection"]["selected_model"]
        forecaster = MODEL_FORECASTER_FACTORIES[model_name]()
        pred = np.asarray(forecaster(atc_train_df, HORIZON), dtype=float)
        summed_per_class_test_predicted += pred

    direct_aggregate_metrics = results["entities"]["ALL"]["test_holdout"]["selected_model_metrics"]
    summed_metrics = evaluate(
        agg_test_actual, summed_per_class_test_predicted, series_by_entity["ALL"].frame["units_sold"].to_numpy(), seasonal_period=SEASONAL_PERIOD
    )
    print(f"Direct aggregate model test metrics: {direct_aggregate_metrics}")
    print(f"Sum-of-per-class-models test metrics: {summed_metrics}")
    results["per_atc_vs_aggregate"] = {
        "direct_aggregate_metrics": direct_aggregate_metrics,
        "sum_of_per_class_metrics": summed_metrics,
    }

    out_path = Path("data/model_registry/m4_backtest_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\nFull results written to {out_path}")
    print(f"Total runtime: {time.time()-t_start:.1f}s")


if __name__ == "__main__":
    main()
