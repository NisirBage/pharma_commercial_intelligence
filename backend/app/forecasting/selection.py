"""Explicit, deterministic model-selection policy (M4 Sec. 10). Never
picks a model by lowest training error, and never defaults to the most
complex candidate — a candidate only wins if it demonstrates a
MEANINGFUL, backtest-measured improvement over the best baseline; ties
are broken toward the simpler model. Full policy write-up:
docs/model-selection.md.
"""

from dataclasses import dataclass
from typing import Any

BASELINE_MODELS = ("naive", "seasonal_naive_7", "moving_average_14")

# A candidate must beat the best baseline's WAPE by at least this relative
# percentage to be considered "in contention" at all.
IMPROVEMENT_THRESHOLD_PCT = 5.0

# Among in-contention candidates, any within this relative % of the single
# best one are considered equivalent — the simplest of those is chosen.
PARSIMONY_TOLERANCE_PCT = 2.0

# Lower = simpler/more interpretable — used only as a tie-break.
MODEL_COMPLEXITY_RANK = {
    "naive": 0,
    "seasonal_naive_7": 0,
    "moving_average_14": 0,
    "linear_regression": 1,
    "ets": 2,
    "random_forest": 3,
}


@dataclass
class SelectionResult:
    atc_class: str
    selected_model: str
    selected_wape: float
    best_baseline_model: str
    best_baseline_wape: float
    improvement_pct: float
    all_summaries: dict[str, dict[str, Any]]
    reason: str


def select_model(atc_class: str, summaries: dict[str, dict[str, float | None]]) -> SelectionResult:
    """`summaries`: {model_name: {"mae", "rmse", "wape", "mase"}} — the
    output of app.forecasting.backtesting.summarize_backtest per model,
    for one ATC class, averaged across every backtest fold."""
    baseline_wapes = {
        name: summaries[name]["wape"]
        for name in BASELINE_MODELS
        if summaries.get(name, {}).get("wape") is not None
    }
    if not baseline_wapes:
        raise ValueError(f"No baseline WAPE available for {atc_class!r} — cannot apply the selection policy.")

    best_baseline_model = min(baseline_wapes, key=baseline_wapes.get)
    best_baseline_wape = baseline_wapes[best_baseline_model]

    candidate_names = [n for n in summaries if n not in BASELINE_MODELS]
    in_contention = []
    for name in candidate_names:
        wape = summaries.get(name, {}).get("wape")
        if wape is None or best_baseline_wape == 0:
            continue
        improvement_pct = (best_baseline_wape - wape) / best_baseline_wape * 100
        if improvement_pct >= IMPROVEMENT_THRESHOLD_PCT:
            in_contention.append((name, wape, improvement_pct))

    if not in_contention:
        return SelectionResult(
            atc_class=atc_class,
            selected_model=best_baseline_model,
            selected_wape=best_baseline_wape,
            best_baseline_model=best_baseline_model,
            best_baseline_wape=best_baseline_wape,
            improvement_pct=0.0,
            all_summaries=summaries,
            reason=(
                f"No candidate model improved WAPE over the best baseline ({best_baseline_model}, "
                f"WAPE={best_baseline_wape:.2f}) by the required {IMPROVEMENT_THRESHOLD_PCT}% — "
                "baseline selected. This is a valid, honestly-reported outcome, not a failure."
            ),
        )

    best_in_contention_wape = min(w for _, w, _ in in_contention)
    equivalent = [
        c for c in in_contention if (c[1] - best_in_contention_wape) / best_in_contention_wape * 100 <= PARSIMONY_TOLERANCE_PCT
    ]
    equivalent.sort(key=lambda c: MODEL_COMPLEXITY_RANK.get(c[0], 99))
    chosen_name, chosen_wape, chosen_improvement = equivalent[0]

    return SelectionResult(
        atc_class=atc_class,
        selected_model=chosen_name,
        selected_wape=chosen_wape,
        best_baseline_model=best_baseline_model,
        best_baseline_wape=best_baseline_wape,
        improvement_pct=chosen_improvement,
        all_summaries=summaries,
        reason=(
            f"Selected {chosen_name} — WAPE improved {chosen_improvement:.1f}% over the best baseline "
            f"({best_baseline_model}); chosen among all candidates within {PARSIMONY_TOLERANCE_PCT}% of the "
            "single best-performing candidate, preferring the simplest (parsimony)."
        ),
    )


def select_all(per_class_summaries: dict[str, dict[str, dict[str, float | None]]]) -> dict[str, SelectionResult]:
    return {atc: select_model(atc, summaries) for atc, summaries in per_class_summaries.items()}
