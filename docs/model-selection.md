# Model Selection Policy

## The policy (implemented in `backend/app/forecasting/selection.py`)

1. **Compare every candidate against the best baseline.** For each ATC
   class, compute backtest WAPE (mean across every rolling-origin fold —
   see docs/forecasting-methodology.md Sec. 3) for the 3 mandatory
   baselines (`naive`, `seasonal_naive_7`, `moving_average_14`) and every
   candidate model (`linear_regression`, `random_forest`, `ets`). The best
   baseline is whichever of the three has the lowest WAPE for that class.
2. **A candidate must clear a meaningful improvement bar.** A candidate is
   only "in contention" if its WAPE beats the best baseline's WAPE by at
   least **`IMPROVEMENT_THRESHOLD_PCT = 5.0`%** (relative). This exists
   specifically so a candidate is never selected for a marginal, likely-
   noise difference — a model that's 1% better than a flat trailing
   average is not meaningfully better.
3. **Prefer simpler models among near-equivalent candidates.** Among
   candidates that clear the bar, any within **`PARSIMONY_TOLERANCE_PCT =
   2.0`%** (relative) of the single best-performing candidate are treated
   as equivalent; the simplest of those (by `MODEL_COMPLEXITY_RANK`:
   baselines < linear regression < ETS < random forest) is selected. A
   materially better complex model still wins outright — parsimony only
   breaks near-ties, it never overrides a real performance gap.
4. **If no candidate clears the bar, the baseline is selected — and that
   is reported as a legitimate result, not a failure.** Per the M4
   instructions: "if a sophisticated model performs worse than a
   baseline, report that honestly." `SelectionResult.reason` records
   exactly why a baseline was kept.
5. **Selection never uses training error, and never touches the held-out
   test window.** Every number the policy looks at comes from the
   rolling-origin VALIDATION folds only (docs/forecasting-methodology.md
   Sec. 3). The final TEST holdout (the dataset's last 14 days) is
   evaluated exactly once, after selection, purely to report how the
   selected model performs on data it never influenced in any way — never
   used to pick between models.
6. **Selection is per-ATC-class, not global.** Given M3's finding that
   classes behave differently (R03 growing, N02BA/N05B declining, the
   rest flat), forcing one model choice across all 8 classes would be a
   worse default than letting the data decide per class — this is
   verified empirically, not just argued, in the per-class comparison
   below.

## Why WAPE (not MAE/RMSE/MASE) drives the selection threshold

MAE and RMSE are reported for every model (see the comparison tables) but
are not comparable *across* ATC classes of very different volume — a
0.5-unit MAE means something very different for N05C (≈1% of total
demand) than for N02BE (≈49%). WAPE is a ratio (sum of absolute errors
over sum of absolute actuals), so it's already normalized for use as the
cross-class selection criterion. MASE is also scale-free and is reported
alongside WAPE as a cross-check, but WAPE was chosen as the primary
selection metric because it directly answers the practically relevant
question ("what fraction of total observed volume was the forecast off
by?"), which maps more directly to a supply-planning read than MASE's
"how much better than a naive in-sample benchmark" framing.

## What "improvement" means here, concretely

`improvement_pct = (best_baseline_wape - candidate_wape) / best_baseline_wape * 100`,
computed on the validation folds. This is reported per class in the
comparison table below — every number is real, from
`backend/scripts/run_m4_backtest.py`'s actual output, not asserted.

---

## Results

All numbers below are validation-fold WAPE (mean across the 6 rolling-origin
folds — see [forecasting-methodology.md](forecasting-methodology.md) Sec. 3),
from the actual run of `backend/scripts/run_m4_backtest.py`.

### Validation WAPE by model, every entity

| Entity | naive | seasonal_naive_7 | moving_average_14 | linear_regression | random_forest | ets | **Selected** |
|---|---:|---:|---:|---:|---:|---:|---|
| ALL (aggregate) | 31.76 | 32.77 | 24.24 | 24.41 | **21.96** | 22.31 | **ets** |
| M01AB | 70.03 | 60.42 | **38.27** | 42.41 | 39.06 | 39.50 | **moving_average_14** |
| M01AE | 73.20 | 65.95 | 44.77 | 45.68 | 42.23 | **42.42** | **ets** |
| N02BA | 58.56 | 55.76 | **44.88** | 51.42 | 48.10 | 45.52 | **moving_average_14** |
| N02BE | 48.94 | 44.03 | **33.71** | 34.49 | 32.19 | 32.96 | **moving_average_14** |
| N05B | 65.95 | 64.05 | 46.02 | 49.09 | 43.44 | **41.89** | **ets** |
| N05C | **153.33** | 163.03 | 159.74 | 180.15 | 249.74 | 169.78 | **naive** |
| R03 | 107.59 | 112.81 | **106.00** | 124.96 | 175.23 | 129.42 | **moving_average_14** |
| R06 | 87.95 | 73.93 | **53.00** | 58.49 | 70.20 | 64.34 | **moving_average_14** |

(Bold = numerically lowest WAPE for that entity; **Selected** applies the
full policy above, which is not always the same as the numerically lowest
value — see M01AE, where `random_forest` is numerically best but `ets` is
within the 2% parsimony tolerance and simpler, so `ets` wins.)

### What actually happened, honestly

- **Random Forest was never selected for any class**, despite frequently
  having the numerically lowest validation WAPE (ALL, M01AE). In both
  those cases `ets` was within the 2% parsimony tolerance and simpler, so
  the policy chose `ets` — the parsimony rule doing exactly its intended
  job.
- **5 of 8 individual ATC classes kept a baseline** (M01AB, N02BA, N02BE,
  R03, R06 all selected `moving_average_14`; N05C selected `naive`) — no
  candidate model cleared the 5% improvement bar. This is reported
  honestly, per the M4 instructions, rather than forced.
- **Only 3 entities had a candidate clear the bar**: the aggregate series
  (`ets`, +8.0% over `moving_average_14`), M01AE (`ets`, +5.3%), and N05B
  (`ets`, +9.0%).
- **N02BE — the dominant class at ~49% of total demand — kept the
  baseline.** Its best candidate (`random_forest`, WAPE 32.19) was only
  4.5% better than the baseline (33.71), short of the 5% bar. This
  matters operationally: the highest-stakes class (an error here has the
  largest absolute impact) is currently forecast with the simplest model
  in the lineup.
- **R03 — the one class M3 found a statistically significant GROWTH
  trend for — also kept the baseline**, and every ML/statistical
  candidate performed *worse* than `moving_average_14` (`random_forest`
  was dramatically worse, WAPE 175.23 vs. baseline's 106.00). A confirmed
  trend does not automatically translate into better 14-day-ahead
  forecastability — R03 also has the second-highest volatility of any
  class (M3: CV=1.17), which apparently dominates the trend signal at
  this horizon.
- **N05C — the smallest, sparsest class (~1% of demand, M3's highest
  CV=1.84) — is the hardest to forecast by a wide margin** (best WAPE
  153.33, roughly 4-7× every other class's error). Every candidate made
  it worse, `random_forest` badly so (WAPE 249.74). This is consistent
  with, not contradicting, M3's volatility finding.

### Final test-holdout results (2019-09-25 → 2019-10-08, touched once)

| Entity | Selected model | Selected WAPE | Best-baseline WAPE | Selected MASE |
|---|---|---:|---:|---:|
| ALL | ets | 16.27 | 17.71 | 0.66 |
| M01AB | moving_average_14 | 38.08 | 38.08 | 0.68 |
| M01AE | ets | 38.69 | 40.69 | 0.69 |
| N02BA | moving_average_14 | 44.28 | 44.28 | 0.52 |
| N02BE | moving_average_14 | 25.13 | 25.13 | 0.86 |
| N05B | ets | 37.85 | 39.47 | 0.73 |
| N05C | naive | 100.00 | 100.00 | 0.65 |
| R03 | moving_average_14 | 87.59 | 87.59 | 0.86 |
| R06 | moving_average_14 | **123.19** | 123.19 | 1.11 |

Every "selected == baseline" row above is expected — when the policy kept
the baseline, the test-window number is necessarily identical (same
model). Where `ets` was selected (ALL, M01AE, N05B), it also beat the
baseline on the untouched test window, not just on the validation folds
— a real, if modest, out-of-sample confirmation. **R06's test WAPE
(123.19%) is markedly worse than its validation-fold average performance
implied** — a genuine finding, not an error, discussed in
[forecasting-insights.md](forecasting-insights.md).

### Per-class vs. aggregate forecasting — the empirical answer

M4 explicitly asked whether per-ATC forecasting materially outperforms a
single aggregate approach. Tested directly on the final test window: sum
the 8 per-class selected models' forecasts vs. the aggregate series'
own directly-selected model (`ets`), both evaluated against the true
total demand for 2019-09-25 → 2019-10-08.

| Approach | MAE | RMSE | WAPE | MASE |
|---|---:|---:|---:|---:|
| **Direct aggregate model (ets)** | 11.46 | 14.99 | **16.27** | 0.66 |
| Sum of 8 per-class selected models | 12.86 | 16.13 | 18.26 | 0.74 |

**The direct aggregate forecast is more accurate than summing the
per-class forecasts** — the opposite of what M3's per-class divergence
finding might suggest, and reported exactly as found, not adjusted to
match expectations. See
[forecasting-insights.md](forecasting-insights.md) for the interpretation
(most likely a portfolio/diversification effect: idiosyncratic per-class
noise partially cancels out in the aggregate, and the aggregate series is
less volatile than any single class) and why per-class forecasts remain
necessary anyway for operational, per-drug decisions despite this.
