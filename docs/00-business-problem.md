# Business Problem — Draft, Pending Scope Decision

**Status: this document flags a scope conflict that needs an explicit
decision before Milestone 2 (data model / analytics design) starts.** Per
the project's own working rules, milestones do not proceed silently.

## The conflict

The project brief names this a "Pharma Commercial Intelligence & Territory
Optimization Platform" and lists opportunity identification, territory
optimization, and explainable recommendations among the required
capabilities. The mandated dataset
(`milanzdravkovic/pharma-sales-data`, see [01-data-dictionary.md](01-data-dictionary.md))
is a single time series of drug-class sales volumes with **no territory,
HCP, sales-rep, geography, customer, or revenue data of any kind** — just 8
ATC drug-class columns and a timestamp, at 4 rolled-up granularities.

Territory optimization is not a smaller/harder version of what's in this
data — it's a capability the data structurally cannot support, real or
inferred, because there is nothing in it that varies by territory, rep, or
account. Building it would mean inventing the entire commercial entity
layer (reps, territories, HCPs, call activity, targets) from nothing, which
is exactly what the brief's own rules forbid doing silently
("Do not invent... territories... sales representatives... unless they
actually exist in the source data").

## What the real data *does* support well

This dataset is a strong fit for a narrower but still substantial scope:

- **Demand forecasting** per ATC class, at daily/weekly/monthly grain, with
  a real 5.75-year history and visible seasonality (flu season effects on
  R03/R06, etc.) — this is a legitimate forecasting problem, not a toy one.
- **Trend and seasonality decomposition** per drug class — which
  categories are growing/declining, which are seasonal vs. stable.
- **Anomaly / opportunity detection** — periods or categories where actual
  sales deviate materially from forecast/expected pattern, which a
  commercial team would want flagged (stockout risk, demand spikes,
  under-forecasted categories).
- **Inventory/replenishment-style optimization** — e.g. reorder point or
  safety-stock recommendations per category, driven by the forecast and its
  uncertainty. This is a legitimate use of an optimization library (the
  brief calls for OR-Tools or similar) without inventing entities.
- **A relational data model, ETL pipeline, API, and dashboard** around all
  of the above — every other required capability in the brief (data
  engineering, DB design, API engineering, dashboard, testing, CI/CD) is
  fully achievable on real data.

## Two ways to close the gap, not mutually exclusive

**Option A — Rescope the project honestly.**
Rename/reframe as a **"Pharma Demand Intelligence & Inventory Optimization
Platform"** (exact name TBD). Drop territory optimization from the
requirements. This keeps 100% of the analytics on real, defensible data and
is the more interview-safe option: every number and every recommendation
traces to actual data, and "I identified early that the assumed schema
didn't support territory optimization and rescoped accordingly" is itself a
strong requirements-engineering story for a BTSA interview.

**Option B — Layer in a clearly-labelled synthetic commercial layer.**
Keep territory optimization, but only by generating a *separate, seeded,
documented, synthetic* layer — e.g. N synthetic territories each mapped to
a share of the real ATC-level demand, with synthetic rep assignments and
synthetic call-activity data — on top of the real demand series. Every
table/column from this layer would need a `synthetic_` prefix or an
equivalent clear marker, a documented generation method with a fixed
random seed, and explicit callouts in the dashboard ("synthetic data") so
nothing is presented as if it came from the source. This preserves the
original scope but roughly doubles the surface area of assumptions that
need defending in an interview, and the territory-optimization results
would only ever be "optimization on a plausible synthetic scenario," not a
finding about real pharmacy sales.

## Recommendation

Option A, with a light version of Option B if there's appetite for it: keep
the core platform (forecasting, seasonality, anomaly/opportunity detection,
inventory optimization, full-stack delivery) entirely on real data, and
optionally add a clearly-fenced-off synthetic territory-allocation module as
a bonus feature later — never as the load-bearing centerpiece — once the
real-data core is solid. This maximizes what's defensible in an interview
("I built the real thing the data supports, and I know exactly where I'd
need more data to go further") over a system whose headline feature rests
on invented entities.

## Requirements (draft, assuming Option A — revise on decision)

1. Forecast daily/weekly/monthly demand per ATC class with a documented
   train/test split that respects time order (no leakage).
2. Surface seasonality and trend per class in a way a commercial planner
   could act on (e.g. "R03 demand rises ~X% each Q4").
3. Flag demand anomalies (actual vs. expected) above a documented threshold.
4. Recommend inventory reorder points / safety stock per class from
   forecast + forecast uncertainty, via an explicit optimization
   formulation (not a heuristic dressed up as one).
5. Serve all of the above through a typed REST API backed by a normalized
   Postgres schema populated by a reproducible ETL pipeline from the raw
   CSVs.
6. Present it in a business-facing dashboard aimed at a commercial/supply
   planning audience, not a data-science audience.
7. Every metric and recommendation must be traceable to the ETL'd source
   data — no fabricated business impact numbers.

**This document is intentionally left without a final decision. Confirm
Option A, Option B, or a variant before Milestone 2 begins.**
