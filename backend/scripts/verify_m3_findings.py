"""Reproduces every number cited in docs/business-insights.md and the M3
completion report by running the full analytics layer against the real
downloaded dataset (data/raw/, populated by scripts/download_data.py at
the project root).

Usage (from backend/):
    python scripts/verify_m3_findings.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from app.analytics import anomalies, atc_analysis, kpis, reconciliation, seasonality, trends, volatility
from app.analytics.data_access import load_from_raw_csv

RAW_DIR = Path("../data/raw")


def dump(label, obj):
    print(f"\n--- {label} ---")
    print(obj)


def main() -> None:
    df = load_from_raw_csv(RAW_DIR)
    print(
        f"Loaded canonical frame: {len(df)} rows, {df['atc_code'].nunique()} ATC classes, "
        f"{df['observation_ts'].min()} -> {df['observation_ts'].max()}"
    )

    dump("total_demand (hourly)", kpis.total_demand(df))
    dump("average_demand (daily)", kpis.average_demand(df, grain="daily"))
    dump("median_demand (daily)", kpis.median_demand(df, grain="daily"))
    dump("peak_demand (daily)", kpis.peak_demand(df, grain="daily"))
    dump("min_demand (daily)", kpis.min_demand(df, grain="daily"))
    dump("period_over_period_growth (monthly, last vs prior)", kpis.period_over_period_growth(df, grain="monthly"))
    dump("contribution_by_atc", kpis.contribution_by_atc(df))

    dump("overall linear_trend", trends.linear_trend(df))
    dump("yearly_totals", trends.yearly_totals(df))

    dump("day_of_week_effect", seasonality.day_of_week_effect(df))
    dump("hour_of_day_effect", seasonality.hour_of_day_effect(df))
    dump("seasonal_strength weekly (daily grain, period=7)", seasonality.seasonal_strength(df, grain="daily", period=7))
    dump(
        "seasonal_strength annual (monthly grain, period=12)",
        seasonality.seasonal_strength(df, grain="monthly", period=12),
    )

    profiles = atc_analysis.build_atc_profiles(df)
    for p in profiles:
        print(
            f"\nATC {p['atc_code']}: total={p['total_demand'].value:.1f} contribution={p['contribution'].value:.2f}% "
            f"trend_slope={p['trend'].value} classification={p['trend'].metadata.get('classification')} "
            f"cv={p['volatility_cv'].value}"
        )

    dump("classify_by_trend", atc_analysis.classify_by_trend(profiles))
    dump(
        "rank_by_contribution (top3)",
        [(p["atc_code"], p["contribution"].value) for p in atc_analysis.rank_by_contribution(profiles)[:3]],
    )
    dump("demand_concentration", atc_analysis.demand_concentration(df))
    dump("rank_by_volatility", [(m.entity, m.value) for m in volatility.rank_by_volatility(df)])

    all_anomalies = anomalies.detect_anomalies(df, methods=("rolling_zscore",))
    print(f"\nTotal rolling-zscore anomalies detected: {len(all_anomalies)}")
    by_class: dict[str, list] = {}
    for a in all_anomalies:
        by_class.setdefault(a.atc_class, []).append(a)
    for cls, items in sorted(by_class.items()):
        high = sum(1 for i in items if i.severity == "high")
        print(f"  {cls}: {len(items)} anomalies ({high} high severity)")

    iqr_anomalies = anomalies.detect_anomalies(df, methods=("iqr",))
    print(f"Total IQR anomalies detected: {len(iqr_anomalies)}")

    for atc in sorted(df["atc_code"].unique()):
        ms = anomalies.detect_mean_shift(df, entity=atc, grain="monthly")
        print(f"  mean_shift {atc}: t={ms.value}, split={ms.period}, p={ms.metadata.get('p_value_uncorrected')}")
    dump("overall detect_mean_shift", anomalies.detect_mean_shift(df, grain="monthly"))

    report = reconciliation.build_reconciliation_report(RAW_DIR)
    print("\n--- reconciliation report ---")
    print(report["human_readable"])

    top_anomalies = sorted(all_anomalies, key=lambda a: abs(a.anomaly_score), reverse=True)[:5]
    print("\n--- top 5 anomalies by |z-score| ---")
    for a in top_anomalies:
        print(json.dumps(a.__dict__, default=str))


if __name__ == "__main__":
    main()
