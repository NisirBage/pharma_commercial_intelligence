"""ATC drug-class comparative analysis: per-class profiles (built from
app.analytics.kpis/trends/volatility) plus demand-concentration metrics
across the 8 observed classes. Classifications (growing/declining/stable,
most/least volatile) are always derived from an already-computed,
documented statistic — never assigned by inspection.
"""

import pandas as pd

from app.analytics import kpis, trends, volatility
from app.analytics.aggregate import period_label
from app.analytics.types import MetricResult


def build_atc_profiles(df: pd.DataFrame) -> list[dict]:
    """One profile per observed ATC class: total/average/peak/trough
    demand (daily grain), contribution share, statistical trend, and CV
    volatility — everything needed for a comparative table."""
    if df.empty:
        return []
    contributions = {m.entity: m for m in kpis.contribution_by_atc(df)}
    profiles = []
    for atc in sorted(df["atc_code"].unique()):
        profiles.append(
            {
                "atc_code": atc,
                "total_demand": kpis.total_demand(df, grain="daily", entity=atc),
                "average_daily_demand": kpis.average_demand(df, grain="daily", entity=atc),
                "peak_daily_demand": kpis.peak_demand(df, grain="daily", entity=atc),
                "trough_daily_demand": kpis.min_demand(df, grain="daily", entity=atc),
                "trend": trends.linear_trend(df, entity=atc),
                "volatility_cv": volatility.coefficient_of_variation(df, grain="daily", entity=atc),
                "contribution": contributions.get(atc),
            }
        )
    return profiles


def classify_by_trend(profiles: list[dict]) -> dict[str, list[str]]:
    """Buckets ATC codes by the statistical classification
    trends.linear_trend already computed (p < 0.05 required for
    growing/declining) — never a subjective read of a chart."""
    buckets: dict[str, list[str]] = {}
    for p in profiles:
        trend: MetricResult = p["trend"]
        cls = trend.metadata.get("classification") if trend.value is not None else trend.metadata.get(
            "reason", "insufficient_data"
        )
        buckets.setdefault(cls, []).append(p["atc_code"])
    return buckets


def rank_by_contribution(profiles: list[dict]) -> list[dict]:
    """Descending by contribution share — 'dominant classes' = the top of
    this ranking, read directly off contribution_by_atc, not asserted."""
    with_contribution = [p for p in profiles if p["contribution"] is not None]
    return sorted(with_contribution, key=lambda p: p["contribution"].value, reverse=True)


def demand_concentration(df: pd.DataFrame) -> dict:
    """Business question: is observed demand concentrated among a few ATC
    classes, or spread evenly across all 8? This is concentration WITHIN
    THIS OBSERVED DATASET's 8 drug classes — not "market concentration"
    (the dataset has no information about a broader pharmaceutical
    market, competitors, or total addressable demand).

    Metrics:
      - share_pct / cumulative_share_pct per class, ranked descending
      - concentration_ratio_top3_pct (CR3) — combined share of the 3
        largest classes
      - HHI — sum(share_i_in_percent^2), the standard Herfindahl-Hirschman
        formula on a 0-10000 scale. Conventional competition-economics
        reference bands (<1500 unconcentrated, 1500-2500 moderate, >2500
        highly concentrated) are cited only to give the number scale/
        context — this dataset is not a market study, so those bands are
        not asserted as a finding about this market.
    """
    contributions = kpis.contribution_by_atc(df)
    if not contributions:
        return {"reason": "no_data"}

    ranked_metrics = sorted(contributions, key=lambda m: m.value, reverse=True)
    cumulative = 0.0
    ranked = []
    for m in ranked_metrics:
        cumulative += m.value
        ranked.append({"atc_code": m.entity, "share_pct": m.value, "cumulative_share_pct": cumulative})

    cr3 = float(sum(m.value for m in ranked_metrics[:3]))
    hhi = float(sum(m.value**2 for m in ranked_metrics))

    return {
        "ranked": ranked,
        "concentration_ratio_top3_pct": cr3,
        "hhi": hhi,
        "hhi_scale_note": (
            "0-10000 scale (percentage shares squared and summed). Reference bands from "
            "competition economics (<1500 unconcentrated, 1500-2500 moderate, >2500 highly "
            "concentrated) are cited for scale only — this measures demand concentration within "
            "the observed dataset's 8 ATC classes, not a market-structure finding."
        ),
        "period": period_label(df),
    }
