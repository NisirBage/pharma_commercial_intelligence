# Forecasting Insights — M4 Findings

Every number below is from `backend/scripts/run_m4_backtest.py`'s actual
run against the real dataset. Framework (mandatory, per M4 Sec. 14):

- **Observed** — a fact directly readable from the data.
- **Predicted** — what the selected model forecasts going forward.
- **Model evidence** — how the model actually performed in backtesting.
- **Planning implication** — what a supply planner might reasonably do.
- **Limitation** — what the dataset/model cannot tell us.

No claim below asserts reduced stockouts, increased revenue, improved
profit, or improved service level — none of those were measured, and the
dataset contains no cost, price, or inventory data that could measure
them (see [01-data-dictionary.md](01-data-dictionary.md)).

---

## 1. Aggregate demand forecast

**Observed:** Total daily demand (all 8 ATC classes combined) over the
full history averages ~60.6 units/day (M3), with the final observed value
on 2019-10-08.

**Predicted:** The selected model for the aggregate series (`ets`,
additive trend + weekly seasonality) forecasts **64.7 → ~69 units/day**
for the 14 days following the dataset's end (2019-10-09 → 2019-10-22),
with a 90% interval of roughly **[35, 100]** units/day throughout —
i.e., the point forecast could very plausibly be off by ±45% on any
given day.

**Model evidence:** `ets` beat the best baseline (`moving_average_14`) by
8.0% on validation-fold WAPE (22.31 vs. 24.24) and confirmed that edge on
the untouched final test window (16.27 vs. 17.71 WAPE) — a real, if
modest, improvement.

**Planning implication:** The aggregate forecast is usable as a rough
total-volume planning number, but the wide interval means it should never
be read as a precise commitment — a planner using it for, say, warehouse
throughput planning should plan for the interval's upper end during
uncertain periods, not the point estimate alone.

**Limitation:** This is a forecast of *total observed units across 8
otherwise-unrelated drug classes* — it says nothing about which specific
drugs will be needed, and (see Finding 6) is **not** well-approximated by
summing independent per-class forecasts.

---

## 2. Per-class forecastability varies enormously — and doesn't track M3's trend findings cleanly

**Observed:** M3 found R03 has a statistically significant *growth*
trend and N02BA/N05B have significant *decline* trends.

**Analytical finding (backtesting):** Despite its confirmed trend, **R03
was one of the hardest classes to improve on with any candidate model** —
`random_forest`'s WAPE (175.23) was dramatically *worse* than the simple
baseline (106.00), and no candidate cleared the 5% bar. N05B, by
contrast, *did* see a real improvement (`ets`, +9.0% over baseline). The
best-forecast class overall by test WAPE is the aggregate series (16.27%)
and N02BE (25.13%); the worst is R06 (123.19% on the test window) and
N05C (100.00%, essentially unforecastable).

**Model evidence:** See [model-selection.md](model-selection.md)'s full
comparison table — every number is a real backtest result.

**Predicted:** Per-class 14-day-ahead point forecasts and intervals are
available for all 8 classes via `app.forecasting.predictions.generate_forecast`
(structured output, ready for a future API — see
[forecasting-methodology.md](forecasting-methodology.md) Sec. 19).

**Planning implication:** A confirmed statistical trend (M3) is not by
itself evidence that a class is easy to forecast operationally — R03's
volatility (M3: CV=1.17, the 2nd-highest of any class) appears to
dominate its trend signal at a 14-day horizon. Trend and volatility
should be considered together, not trend alone, when deciding how much
to trust a forecast for planning.

**Limitation:** The dataset offers no way to distinguish whether R03's
volatility is itself seasonal/explainable (e.g. respiratory drugs and
weather) or genuinely close to noise at daily grain — only that current
methods can't exploit the trend at this horizon.

---

## 3. The dominant class is forecast with the simplest model

**Observed:** N02BE is ~49.4% of all observed demand (M3).

**Analytical finding:** N02BE's best candidate model
(`random_forest`, validation WAPE 32.19) was only 4.5% better than the
simple 14-day trailing average (33.71) — short of the 5% improvement bar
— so the **baseline was selected** for the highest-volume, highest-
stakes class in the dataset.

**Model evidence:** Test-window WAPE for N02BE: 25.13% (baseline,
identical since no candidate was chosen). Residual diagnostics
(Section 7) show this baseline's errors have **statistically significant
autocorrelation** (Ljung-Box p ≈ 0.00007) — meaning there IS predictable
structure in N02BE's errors that no candidate model here managed to
capture well enough to clear the selection bar.

**Planning implication:** N02BE is simultaneously the class where
forecast accuracy matters most (its errors dominate total-volume error
by sheer size) and where the current model lineup has the most
demonstrated room to improve. This is the strongest candidate for
investment in a better model in a future milestone — not because it
performs badly in absolute terms (25% WAPE is mid-pack), but because of
its outsized operational weight.

**Limitation:** "Room to improve" is inferred from residual
autocorrelation, not from having actually built and tested a better
model — that's future work, not a claim about what a better model would
achieve.

---

## 4. The smallest class is effectively unforecastable with current methods

**Observed:** N05C is ~1.0% of total demand (M3) and has the highest
coefficient of variation of any class (CV=1.84, M3).

**Analytical finding:** N05C's best model — the plain `naive` baseline —
still has a validation WAPE of 153.33%, roughly 4-9× worse than every
other class, and every candidate model made it *worse* (`random_forest`:
WAPE 249.74). Test-window WAPE is exactly 100% (the single day's forecast
missed the actual value by its full magnitude).

**Model evidence:** Residual diagnostics show N05C's errors are also
significantly autocorrelated (Ljung-Box p ≈ 0.0000058), but unlike
N02BE, more sophisticated models made this *worse*, not better —
consistent with N05C being dominated by sparse, near-random small-integer
counts rather than a smooth signal any of these model classes can
extract more from.

**Planning implication:** Do not build automated reorder logic on N05C's
point forecast without a human review step — its forecast is the least
reliable of any class by a wide margin.

**Limitation:** This may reflect a genuinely low, sporadic real-world
demand pattern (consistent with its 1% share) rather than a model
inadequacy — the dataset provides no way to tell the two apart.

---

## 5. Residual diagnostics: where models are (and aren't) leaving structure on the table

**Observed / Analytical finding** (Ljung-Box test on pooled validation-fold
residuals, per selected model):

| Entity | Selected | Mean residual | Ljung-Box p-value | Autocorrelation? |
|---|---|---:|---:|---|
| ALL | ets | +4.84 (underpredicts) | 0.0002 | **Yes** |
| M01AB | moving_average_14 | +0.66 | 0.75 | No |
| M01AE | ets | −0.31 | 0.62 | No |
| N02BA | moving_average_14 | +0.17 | 0.08 | Borderline |
| N02BE | moving_average_14 | +3.54 (underpredicts) | 0.00007 | **Yes** |
| N05B | ets | +1.41 | 0.0026 | **Yes** |
| N05C | naive | +0.17 | 0.0000058 | **Yes** |
| R03 | moving_average_14 | +0.63 | 0.58 | No |
| R06 | moving_average_14 | −0.44 | 0.99 | No |

**Interpretation:** A significant Ljung-Box result means the model's
errors are not white noise — there is exploitable structure the model
isn't using. Notably, this happens for the **aggregate series, N02BE, and
N05B — three of the highest-volume entities** — even though N05B's `ets`
model was the one selected as an improvement over baseline. An improvement
over baseline does not mean the model has extracted all available signal.

Several classes (M01AB, M01AE, N02BA borderline, R03, R06) show residuals
statistically indistinguishable from white noise — for those, the
selected model (mostly the simple baseline) is plausibly close to
extracting what structure is realistically available at this horizon.

**Also observed:** every entity's mean residual is small relative to its
std (e.g. ALL: mean +4.84 vs. std 15.59) — there's a mild systematic
underprediction bias in most series (positive mean residual = actual >
predicted more often than not), but it's not large enough to be the
dominant source of error anywhere.

**Planning implication:** ALL, N02BE, and N05B are the priority
candidates for future model improvement work (M5+) — not because their
absolute error is worst, but because there's demonstrated, testable
evidence (autocorrelated residuals) that a better model exists in
principle.

**Limitation:** Ljung-Box tells us structure exists, not what it is or
how to capture it — that requires actual further modeling work, not
asserted here.

---

## 6. Per-class forecasts do NOT sum to a better aggregate forecast than forecasting the aggregate directly

**Observed:** M3 found N02BE alone is ~49% of demand and the top 3
classes are ~73% — a strong argument, on its face, for per-class
attention.

**Analytical finding:** On the final test window, **summing the 8
per-class selected models' forecasts (WAPE 18.26%) was LESS accurate
than the aggregate series' own directly-selected model (WAPE 16.27%)**
— see [model-selection.md](model-selection.md) for the full comparison.
This is the opposite of what the per-class divergence finding might
suggest, and is reported exactly as found.

**Hypothesis (not verified from this data):** The most likely
explanation is a **portfolio/diversification effect** — each class's
idiosyncratic day-to-day noise partially cancels out when summed into the
aggregate, so the aggregate series is inherently *less volatile*
(consistent with M3: the aggregate's implied volatility, via its
much-lower WAPE across every single model tested, is well below any
individual class's). Most of the 8 per-class models are also the
*simplest* baseline (`moving_average_14`/`naive`), which don't track
each class's own dynamics as well as `ets` tracks the smoother aggregate
— compounding the gap.

**Planning implication:** For a business question that's genuinely about
*total* volume (e.g. total shelf space, aggregate logistics capacity),
forecast the aggregate directly — it's measurably more accurate. For any
question that requires knowing *which drug* — which is every actual
inventory/reorder decision — the per-class forecasts remain necessary
regardless of this result; the aggregate number cannot be disaggregated
back into per-drug quantities.

**Limitation:** This finding is specific to the current model lineup and
the 14-day test window observed — it is not a general theorem that
aggregation always beats disaggregation; a stronger per-class model
lineup (Section 5) could close or reverse this gap.

---

## 7. Forecast uncertainty and horizon behavior

**Observed / Analytical finding:** For the aggregate series' `ets`
forecast, per-horizon-step MAE (pooled across the 6 validation folds)
does **not** increase monotonically with the forecast step — it ranges
from as low as 3.68 (step 5) to as high as 23.87 (step 12), with no clean
compounding pattern. This is expected for ETS, which forecasts the full
horizon directly from the fitted model rather than recursively feeding
its own predictions forward (unlike the recursive ML candidates — see
[forecasting-leakage-audit.md](forecasting-leakage-audit.md) — though
notably, no ML candidate was actually selected for any of the 9 series,
so the theoretical recursive-compounding risk didn't end up mattering for
the final selected models).

**Planning implication:** There's no simple "trust the first week more
than the second week" rule to apply here — a planner using this
forecast should look at the actual per-day interval (available in the
structured output) rather than assuming uncertainty grows steadily
across the horizon.

**Limitation:** This was only examined in detail for the aggregate
series; per-class horizon-step behavior is available in
`backend/data/model_registry/m4_backtest_results.json` but not
exhaustively analyzed here.

---

## What this milestone does NOT claim

- No reduction in stockouts, waste, or holding cost — no inventory,
  lead-time, or cost data exists in this dataset to measure any of those.
- No revenue or profit impact — no price data exists.
- No causal explanation for any trend, seasonal pattern, or forecast
  error — every finding here is descriptive/predictive, not causal (same
  discipline as M3's Observed/Analytical/Hypothesis framing).
- No claim that this specific model lineup is the ceiling of what's
  achievable — Section 5 explicitly identifies where residual structure
  suggests more is possible.
