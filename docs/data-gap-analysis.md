# Data Gap Analysis — What a Real Engagement Would Require

This document identifies what additional data would be required to turn
this prototype (M1–M5, built entirely on `milanzdravkovic/pharma-sales-data`)
into a real pharmaceutical supply-planning solution. Nothing below is
assumed to exist in the Kaggle dataset — each gap is explicit about what's
missing and why it matters for the corresponding milestone's methodology.

## Demand

| Gap | Why it matters | Where it would change this project |
|---|---|---|
| **Historical orders / actual prescriptions filled** | The Kaggle dataset is pharmacy-level *sales volume* by ATC class — not prescription-level, patient-level, or SKU-level (brand/dose/pack-size) data. Real demand planning typically operates at SKU grain. | M2's canonical model would need a finer entity grain than "ATC class"; M4's forecasts would need to be built per-SKU, not per-class. |
| **Channel demand** (retail vs. hospital vs. mail-order vs. online) | This dataset has no channel field — all demand is pooled. Different channels often have very different volatility and lead-time profiles. | M3's volatility/seasonality findings, and M4's forecasts, are channel-blind; a real engagement would need channel-level series. |
| **Censored demand due to historical stockouts** | If a stockout occurred in the observed period, recorded "sales" for that period understate true demand (you can't sell what isn't in stock) — M2/M3/M4 currently treat every observed value as true, uncensored demand. Without stockout records, this censoring can't be detected or corrected. | Would affect M2's data-quality framework (a new check), M3's demand-level findings, and M4's forecast accuracy (training on censored data biases the model toward underforecasting). |

## Inventory

| Gap | Why it matters | Where it would change this project |
|---|---|---|
| **Current inventory levels / stock-on-hand** | M5's reorder point/safety-stock outputs are policy PARAMETERS, not actionable order triggers, because there is no current stock position to compare against. | M5's `recommended_order_quantity` would become a real "how much to order right now" figure only once compared against actual on-hand + on-order inventory. |
| **Historical inventory positions over time** | Would let a real system validate whether the M5 policy would actually have prevented past stockouts/reduced past overstock — currently impossible to check against reality. | Would enable a genuine backtest of the M5 policy itself (not just the M4 forecast), the natural next validation step. |
| **Recorded stockout events** | Needed both to correct censored demand (see above) and to validate M5's expected-shortage estimates against what actually happened. | Would let M5 report a REAL (not simulated) service-level attainment metric. |

## Supply

| Gap | Why it matters | Where it would change this project |
|---|---|---|
| **Actual supplier lead times** (per SKU, possibly per supplier) | `lead_time_days=7` in this project is a scenario assumption, not a measured value (see [planning-assumptions.md](planning-assumptions.md)). Real lead times vary by product and supplier and are rarely a single constant. | M5's safety-stock/reorder-point formulas would use per-class (or per-SKU) real lead times, and could model lead-time VARIABILITY itself as an additional source of uncertainty (currently only demand uncertainty is modeled — a documented simplification). |
| **Minimum order quantities / order increments** | Real suppliers often require ordering in fixed lot sizes, not the continuous quantity this project's EOQ-style formula produces. | `app.optimization.reorder_point.compute_scenario_order_quantity`'s min/max bounds are placeholders for real MOQ constraints. |
| **Order schedules / supplier calendars** | Determines when a periodic-review policy's review dates can actually align with real ordering windows. | Would replace the fixed `review_period_days` scenario assumption. |
| **Supplier capacity constraints** | A supplier may not be able to fulfill an arbitrarily large order on short notice. | Would add a new constraint class to M5's LP (the capacity constraint currently only limits total safety stock across ATC classes, not per-supplier fulfillment capacity). |

## Commercial

| Gap | Why it matters | Where it would change this project |
|---|---|---|
| **Price / unit economics** | This project's `holding_cost_weight`/`stockout_cost_weight`/`ordering_cost_weight` (M5) are unitless SCENARIO weights specifically because no real cost data exists. Real holding cost depends on unit price + capital cost; real stockout cost depends on price + margin + patient-access considerations. | M5's objective function would use real monetary units, and its "expected shortage" outputs could be converted to a genuine dollar-cost estimate — currently explicitly avoided (M5 Sec. 22 restriction). |
| **Discounts / rebates / contract pricing** | Could materially change effective per-unit costs feeding the objective above. | Same as price. |
| **Promotions** | M4's anomaly detection (inherited from M3) explicitly could NOT attribute any detected demand spike to a promotion, because no promotional calendar exists. | Would let M3/M4 separate "promotional lift" from organic trend/seasonality — currently every anomaly is reported as an unexplained statistical deviation only. |
| **Product launches / discontinuations** | A new product has no history to forecast from; M4's forecasting entirely depends on having sufficient historical data per class (minimum 180-day training window). A real launch-forecasting problem needs an entirely different (analogy-based or judgmental) method. | Not currently supported at all — M4 would fail outright (insufficient history) for a genuinely new product. |

## Geography

| Gap | Why it matters | Where it would change this project |
|---|---|---|
| **Warehouse / distribution center identity** | The Kaggle dataset has no location field at all — M1 could not even confirm whether the data represents a single pharmacy or an aggregate. M5's `shared_capacity_budget` is a single, undifferentiated pool across all 8 classes; a real network would have per-location capacity. | M5's LP would need one capacity constraint per warehouse/DC, plus a network-flow or multi-echelon structure — a materially larger reformulation, not a parameter tweak. |
| **Market / region** | Demand patterns (and lead times, and regulations) commonly differ by region. | Would add a region dimension to every milestone's entity grain (M2's fact table, M3's analytics, M4's forecasts, M5's policies) — the single biggest structural change this project would need for a multi-site real engagement. |

## How this maps to a real ZS engagement

A real client conversation would typically start by establishing which of
the gaps above the client can actually fill (most clients have inventory
and supplier data even when they lack clean demand-forecasting
infrastructure — the reverse of this project's situation, which had
excellent demand history and nothing else). The realistic sequencing:

1. **Confirm demand data quality first** (M1/M2's discipline — verify
   grain, reconciliation, and any censoring from historical stockouts)
   before trusting any forecast built on top of it.
2. **Get real inventory positions** before presenting any output as an
   actionable order recommendation, not just a policy parameter.
3. **Get real lead times and cost data** before presenting any dollar
   figure — this project deliberately never did, and a real engagement
   should treat that as the single biggest gap to close before making
   business-impact claims.
4. **Geography/network structure** is usually the most complex addition
   and would typically come after the single-location model above is
   validated.
