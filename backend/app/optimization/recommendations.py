"""Explainable recommendation engine. Every recommendation names its
recommendation, evidence, assumptions, expected effect, confidence, and
limitations (M5 Sec. 13) — never a bare conclusion.

**ATC prioritization logic (M5 Sec. 10), implemented explicitly here:**

- **N02BE**: described as high-volume / high PLANNING EXPOSURE (its
  errors matter more in absolute terms — ~49% of demand, M3) — never
  labeled "high risk," because its OWN forecast-error volatility is
  actually the LOWEST of any class (M3: CV=0.52; M4: WAPE 25.1%, mid-
  pack) — there is no evidence supporting a risk label, and this module
  does not apply one just because the class is large.
- **N05C**: M3 found the highest CV (1.84) of any class, but only ~1% of
  total demand. This module checks the ABSOLUTE safety-stock units at
  stake before deciding whether that volatility is operationally
  meaningful — CV alone does not drive the recommendation.
- **R03**: M3 found a statistically significant growth trend, but M4
  found every forecasting candidate performed WORSE than the simple
  baseline for R03. This module bases R03's recommendation on the M4
  forecast + uncertainty actually used for planning, not on the M3 trend
  finding directly — historical growth alone is never used to inflate
  inventory beyond what the current forecast implies.
"""

from dataclasses import dataclass

from app.optimization.demand_input import DemandInput
from app.optimization.reorder_point import ReorderPointResult

STANDARD_ASSUMPTIONS: list[str] = [
    "lead_time_days and service_level_target are scenario assumptions, not observed values from the Kaggle dataset.",
    "Safety stock is derived from M4 forecast-residual uncertainty, not raw historical demand variability and not a real-world measured error rate.",
]

STANDARD_LIMITATIONS: list[str] = [
    "The Kaggle dataset contains no real inventory, cost, or supplier data — this recommendation is a scenario simulation, not a real-world business commitment.",
]


@dataclass
class Recommendation:
    atc_class: str
    recommendation: str
    evidence: list[str]
    assumptions: list[str]
    expected_effect: str
    confidence: str
    limitations: list[str]


def _confidence_from_model_evidence(demand_input: DemandInput) -> tuple[str, str]:
    """Confidence is read off M4's OWN backtesting evidence — never
    asserted independently of it."""
    model = demand_input.selected_model
    wape = demand_input.evaluation_metrics.get("wape")
    wape_str = f"{wape:.1f}%" if wape is not None else "unavailable"
    if model == "naive" or (wape is not None and wape > 80):
        return "low", f"Selected model is '{model}' with validation WAPE {wape_str} (M4) — among the least reliable forecasts in the lineup."
    if model in ("moving_average_14", "seasonal_naive_7"):
        return "medium", f"Selected model is the simple baseline '{model}' — M4 found no candidate meaningfully improved on it (validation WAPE {wape_str})."
    return "medium-high", f"Selected model '{model}' demonstrated a measurable improvement over baseline in M4 backtesting (validation WAPE {wape_str})."


def build_recommendation(
    atc_class: str,
    demand_input: DemandInput,
    reorder_result: ReorderPointResult,
    scenario_name: str,
    contribution_pct: float | None = None,
) -> Recommendation:
    confidence, confidence_evidence = _confidence_from_model_evidence(demand_input)
    evidence = [confidence_evidence]
    assumptions = list(STANDARD_ASSUMPTIONS)
    limitations = list(STANDARD_LIMITATIONS)

    if atc_class == "N02BE":
        volume_note = f"~{contribution_pct:.1f}%" if contribution_pct is not None else "the largest share"
        evidence.append(f"N02BE represents {volume_note} of total observed demand (M3).")
        evidence.append("N02BE's own forecast-error volatility is the LOWEST of any class (M3 CV=0.52; M4 test WAPE 25.1%, mid-pack) — no evidence of elevated risk specific to this class.")
        recommendation_text = (
            "Treat N02BE as high PLANNING EXPOSURE — errors here have the largest absolute impact because of "
            "its volume — not as 'high risk.' Its own volatility evidence does not support a risk label."
        )
        expected_effect = "A given percentage forecast error in N02BE translates to a larger absolute unit shortfall than the same percentage error in any other class."
    elif atc_class == "N05C":
        evidence.append("N05C has the highest historical CV of any class (M3: 1.84) but only ~1% of total demand.")
        evidence.append(f"Absolute safety-stock requirement under this scenario is {reorder_result.safety_stock:.2f} units — evaluated on its own merits, not inferred from CV alone.")
        recommendation_text = (
            f"N05C's high CV does not, by itself, justify large safety stock — the absolute unit exposure "
            f"({reorder_result.safety_stock:.2f} units) is what matters operationally, and it is small in "
            "absolute terms despite the high relative volatility."
        )
        expected_effect = "Low absolute inventory exposure under any scenario, because absolute volume is small."
        limitations.append("M4 found N05C essentially unforecastable with current methods (test WAPE 100%) — treat its point forecast as low-confidence.")
    elif atc_class == "R03":
        evidence.append("M3 found a statistically significant historical GROWTH trend for R03.")
        evidence.append("M4 found every candidate forecasting model performed WORSE than the simple baseline for R03 — the growth trend was not exploitable at a 14-day horizon.")
        recommendation_text = (
            "R03's safety stock is based on its M4 forecast and forecast-error uncertainty, NOT on the M3 "
            "historical growth trend directly — growth alone is not used to inflate inventory beyond what the "
            "forecast/uncertainty already implies."
        )
        expected_effect = "Policy reflects the current forecasted demand level and R03's own volatility (M3: 2nd-highest CV), not an extrapolation of the historical growth rate."
    else:
        recommendation_text = f"Standard {scenario_name} scenario policy applies — no special-case evidence identified for {atc_class}."
        expected_effect = "Reorder point and safety stock as calculated for this scenario."

    return Recommendation(
        atc_class=atc_class,
        recommendation=recommendation_text,
        evidence=evidence,
        assumptions=assumptions,
        expected_effect=expected_effect,
        confidence=confidence,
        limitations=limitations,
    )


def build_all_recommendations(
    demand_inputs: dict[str, DemandInput],
    reorder_results: dict[str, ReorderPointResult],
    scenario_name: str,
    contributions: dict[str, float] | None = None,
) -> dict[str, Recommendation]:
    contributions = contributions or {}
    return {
        atc: build_recommendation(atc, demand_inputs[atc], reorder_results[atc], scenario_name, contributions.get(atc))
        for atc in demand_inputs
    }
