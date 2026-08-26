# Business Insights — M3 Demand Intelligence Findings

Every number below was computed by `backend/app/analytics/` against the
**real, full dataset** (404,256 canonical hourly observations, 2014-01-02
08:00 → 2019-10-08 19:00, 8 ATC drug classes) — none is estimated,
rounded from memory, or fabricated. Reproduce any of it with
`backend/scripts/verify_m3_findings.py` (or the corresponding pytest suite
for the underlying calculations).

Every finding is labeled using this framework — required reading before
acting on anything here:

- **Observed** — a fact directly readable from the dataset.
- **Analytical finding** — something calculated/tested from the data (a
  statistic, a p-value, a ranking).
- **Hypothesis** — a possible explanation that **cannot** be verified from
  this dataset (no external-event, marketing, or clinical data exists
  here).
- **Recommendation** — a proposed next action, always operational
  ("investigate," "validate"), never a business conclusion asserted as
  fact.

---

## 1. Overall demand level

**Observed:** Total demand across the full observed period is **127,595.5
units**. The average day sees **60.6 units** (median 58.5); the single
highest day was **198.95 units on 2016-12-30**; the single lowest was
**0.0 units on 2014-01-07** (a genuine recorded zero, not a data gap — see
[01-data-dictionary.md](01-data-dictionary.md)).

**Analytical finding:** There is **no statistically significant overall
linear trend** across the whole 2014–2019 period (slope ≈ −0.76
units/month, p = 0.75, R² ≈ 0.001) — total demand across all 8 classes is
essentially flat over the long run, once normal month-to-month variation
is accounted for.

**Hypothesis:** A flat aggregate trend could mean genuinely stable overall
demand for this observation point, or it could mean growth in some
classes is offsetting decline in others (see Section 4) — the dataset
can't distinguish these without the per-class breakdown, which Section 4
provides.

**Recommendation:** Do not describe this dataset's aggregate demand as
"growing" or "declining" without qualifying by ATC class — the aggregate
trend is not significant.

---

## 2. Year-over-year movement — and a partial-period trap

**Observed:** Yearly totals: 2014 = 20,238 (364/365 days observed),
2015 = 22,752 (+12.4% YoY), 2016 = 25,235 (+10.9% YoY), 2017 = 19,399
(−23.1% YoY), 2018 = 22,885 (+18.0% YoY), 2019 = **17,086, but only 281 of
365 days observed (data ends 2019-10-08) — 2019 is explicitly NOT a
complete year.**

**Analytical finding:** The most recent month-over-month figure the KPI
layer computes (September 2019 → October 2019) shows a **−70.5% decline**
(538.6 vs. 1,824.8 units). October 2019 contains only 8 days of data in
the source (the dataset simply ends there) — this "decline" is **almost
entirely a partial-month artifact**, not a real drop in demand. The same
caution applies to 2019's −25.3% YoY figure, which compares a 281-day year
against a full 365-day prior year.

**Hypothesis:** None needed — this is a known, fully-explained data
boundary effect, not a mystery.

**Recommendation:** **Never** report the raw September→October 2019
month-over-month figure, or full-year 2019 vs. 2018, without the
partial-period caveat attached. `trends.yearly_totals`'s
`is_complete_year` flag exists specifically to prevent this mistake being
made silently downstream (e.g. in a future dashboard).

---

## 3. Seasonality

**Observed / Analytical finding:** Demand varies by **day of week**
(Kruskal-Wallis H = 25.9, p = 0.00023 — statistically significant, but a
modest effect size: Saturday averages 65.7 units/day vs. Thursday's 57.2,
about a 15% spread) and much more sharply by **hour of day** (H ≈ 56,950,
p ≈ 0 — hours 0–7 average essentially zero recorded sales, consistent
with the hourly file only meaningfully covering pharmacy business hours;
demand peaks around 11:00 and again 19:00–20:00). **Weekly seasonality
strength is weak-to-moderate (0.234 on the 0–1 STL scale)**; **annual/
monthly seasonality is moderate-to-strong (0.553)**.

**Hypothesis:** The near-zero overnight hours are most plausibly a
**pharmacy operating-hours artifact** (no transactions recorded when
closed) rather than genuine "zero overnight demand" in a clinical sense —
but the dataset contains no store-hours field to confirm this directly.
The moderate annual seasonality is consistent with (but not proven to be
caused by) seasonal illness patterns affecting respiratory (R03, R06) and
analgesic (N02BA, N02BE) classes.

**Recommendation:** Any inventory/supply-planning use of this data (M4+)
should account for the **strong intraday** and **moderate annual**
patterns explicitly — a single flat safety-stock assumption would be
wrong at both horizons. The weekday effect is real but small enough that
it's a secondary planning factor, not a primary one.

---

## 4. ATC class contribution and per-class trend

**Observed:** Contribution to total demand (share of the 127,595.5-unit
total): **N02BE 49.4%**, N05B 14.6%, R03 9.1%, M01AB 8.3%, M01AE 6.4%,
N02BA 6.4%, R06 4.8%, **N05C 1.0%** (smallest by a wide margin).

**Analytical finding:** Per-class linear-trend classification (p < 0.05
required): **R03 is growing** (slope ≈ +1.58 units/month, statistically
significant) — the only class with a significant positive trend. **N02BA
and N05B are declining** (slopes ≈ −0.97 and −1.37/month, both
significant). The remaining five classes (M01AB, M01AE, N02BE, N05C, R06)
show **no statistically significant trend** over the full period —
including N02BE, despite it being roughly half of all observed demand.

**Hypothesis:** None asserted for *why* R03 is growing or N02BA/N05B are
declining — the dataset has no product, marketing, regulatory, or
clinical-guideline information that could explain a cause.

**Recommendation:** If this were feeding a real planning decision, R03's
growth and N02BA/N05B's decline are the two findings worth investigating
operationally (e.g., against any known external record of formulary
changes, seasonal patterns, or supplier changes) before being used as a
forecasting assumption in M4.

---

## 5. Demand concentration

**Observed / Analytical finding:** The top 3 classes (N02BE, N05B, R03)
account for **73.1%** of total observed demand (CR3 = 73.09%). The
Herfindahl-Hirschman Index across all 8 classes is **HHI = 2,909.9**
(0–10,000 scale) — above the commonly cited 2,500 "highly concentrated"
reference band from competition economics, cited here only for scale, not
as a market-structure claim (this dataset covers one data source's 8 ATC
classes, not a market).

**Hypothesis:** N/A — this is a direct calculation, not an inference.

**Recommendation:** Supply-planning effort (M4) should be weighted toward
N02BE in particular, given it alone is essentially half of all observed
volume — errors in its forecast or safety-stock assumption would dominate
total error far more than any other single class.

---

## 6. Volatility

**Observed / Analytical finding:** Ranked by coefficient of variation
(daily grain, most to least volatile): **N05C (CV = 1.84)**, R03 (1.17),
R06 (0.83), N05B (0.63), N02BA (0.61), M01AE (0.55), M01AB (0.54),
**N02BE (0.52, least volatile)**.

**Hypothesis:** N05C's high CV is most plausibly a **low-volume effect**
— it's the smallest class (0.98% of total demand) with many near-zero
days, which mechanically inflates CV (documented in
[analytics-methodology.md](analytics-methodology.md)) — rather than
evidence of genuinely erratic underlying demand. N02BE's low CV is
consistent with it also being the highest-volume class (law-of-large-
numbers smoothing), not necessarily "more predictable" in a deeper sense.

**Recommendation:** Treat N05C's volatility ranking with caution in any
downstream safety-stock calculation (M4) — a CV-based buffer sized
naively off this number could be disproportionate relative to its actual
(small) volume.

---

## 7. Anomalies

**Observed / Analytical finding:** The rolling-z-score method (30-day
trailing baseline, |z| ≥ 2 flagged) detected **1,048 anomalous
class-days** across the full history; the independent IQR (Tukey-fence)
method detected **713**. Per class (rolling-z-score, high-severity count
in parentheses): M01AB 116 (28), M01AE 119 (28), N02BA 108 (27), N02BE 157
(34), N05B 123 (33), **N05C 155 (59)**, **R03 148 (61)**, R06 122 (33).
The five single largest deviations by |z-score| are all in **N05C**
(4 of 5) and one in **R03** (2019-09-26, observed 31 vs. an expected
baseline of ~2.9 — the single most extreme R03 anomaly, notably near the
very end of the observed series).

**Hypothesis:** None of these anomalies can be attributed to a supply
disruption, marketing campaign, epidemic, competitor action, or product
launch — the dataset contains no evidence for any of those. They are
reported as exactly what they are: statistically unusual deviations from
each class's own recent history.

**Recommendation:** The R03 anomaly on 2019-09-26 is worth flagging
operationally given its timing (the last month of usable data, and R03 is
also the one class with a significant growth trend — Section 4) — but
this is a prompt to investigate, not a conclusion to act on directly.

---

## 8. Structural change screening

**Observed / Analytical finding:** A grid-searched Welch's t-test across
the monthly overall-demand series identifies **September 2014** as the
single strongest candidate change point (t = −3.14, uncorrected
p = 0.0072; mean before ≈ 1,561 units/month, mean after ≈ 1,857). Per-class
candidate change points vary widely: M01AB (2015-03), M01AE (2014-12),
N02BA (2017-03), N02BE (2019-04), N05B (2015-02), N05C (2014-09), R03
(2014-10), R06 (2015-04).

**Hypothesis:** None of these candidate change points can be attributed
to a business cause from this dataset alone. **Important statistical
caveat:** because this method grid-searches every possible split point
and reports only the single best one, the p-values above are **not
corrected for multiple comparisons** and should be read as indicative
screening, not confirmed change points.

**Recommendation:** Use these as a starting list for operational
investigation (e.g., "was there a known change around September 2014?"),
never as a pre-validated finding.

---

## 9. Data reliability (cross-granularity reconciliation)

**Observed:** Re-running M2's reconciliation checks as an ongoing
analytical QC signal confirms: **Daily: Reconciled ✓**, **Weekly:
Reconciled ✓**, **Monthly: Source inconsistency detected ⚠** — identical
to the M2 finding (61/560 cells, 33/70 months mismatched in
`salesmonthly.csv`; see [data-quality-decisions.md](data-quality-decisions.md)).

**Recommendation:** Every monthly figure in this document was derived
from the canonical hourly fact table, **not** `salesmonthly.csv` — this
is what makes the monthly figures above trustworthy despite the known
source-file defect. Any future addition to this platform that touches
monthly data must go through the same derivation, never read
`salesmonthly.csv` directly.
