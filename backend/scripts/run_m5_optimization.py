"""Runs the complete M5 optimization engine against the REAL dataset and
the M4-selected models: builds demand inputs, runs all 3 scenarios
(conservative/balanced/lean), and prints/saves every number cited in
docs/optimization-methodology.md, docs/optimization-insights.md, and the
M5 completion report.

Usage (from backend/): python scripts/run_m5_optimization.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

from app.analytics import kpis
from app.analytics.data_access import load_from_raw_csv
from app.optimization.demand_input import build_all_demand_inputs
from app.optimization.runner import run_all_scenario_results
from app.optimization.sensitivity import elasticity, sensitivity_report
from app.optimization.validation import run_all_validations

RAW_DIR = Path("../data/raw")


def main() -> None:
    t0 = time.time()
    df = load_from_raw_csv(RAW_DIR)
    contributions = {m.entity: m.value for m in kpis.contribution_by_atc(df)}

    all_inputs = build_all_demand_inputs(RAW_DIR)
    per_class_inputs = {k: v for k, v in all_inputs.items() if k != "ALL"}
    print(f"Built demand inputs for {len(per_class_inputs)} ATC classes in {time.time()-t0:.1f}s")

    scenario_results = run_all_scenario_results(per_class_inputs, contributions)

    output = {"scenarios": {}, "sensitivity": {}, "validation": {}}

    for name, result in scenario_results.items():
        print(f"\n=== Scenario: {name} (target={result.to_dict()['scenario']}) ===")
        print(f"  capacity_budget: {result.capacity_budget:.2f}")
        print(f"  baseline total_weighted_shortage:  {result.allocation_baseline['total_weighted_expected_shortage']:.4f}")
        print(f"  optimized total_weighted_shortage: {result.allocation_optimized['total_weighted_expected_shortage']:.4f}")
        print(f"  improvement_pct: {result.optimization_summary['improvement_pct']:.2f}%")
        for atc in sorted(result.atc_results):
            r = result.atc_results[atc]
            b = result.allocation_baseline["per_class"][atc]
            print(
                f"    {atc}: model={r.model_used:16s} ss={r.safety_stock:8.2f} rop={r.reorder_point:9.2f} "
                f"service_level={r.service_level:.4f} (baseline would be {b['implied_service_level']:.4f}) "
                f"oq={r.recommended_order_quantity:.2f} shortage={r.expected_shortage:.4f}"
            )
        output["scenarios"][name] = result.to_dict()

    print("\n=== Sensitivity analysis (N02BE, N05C, R03) ===")
    for atc in ("N02BE", "N05C", "R03"):
        di = per_class_inputs[atc]
        report = sensitivity_report(di, lead_time_days=7, service_level_target=0.95)
        print(f"\n  {atc}:")
        elasticities = {}
        for param, points in report.items():
            e = elasticity(points)
            elasticities[param] = e
            print(f"    {param}: {[(p.value, round(p.safety_stock, 2)) for p in points]}  elasticity={e}")
        output["sensitivity"][atc] = {
            "points": {k: [vars(p) for p in v] for k, v in report.items()},
            "elasticities": elasticities,
        }

    print("\n=== Validation checks (all classes, balanced scenario) ===")
    all_valid = True
    for atc, di in per_class_inputs.items():
        result = run_all_validations(di, lead_time_days=7, service_level_target=0.95)
        passed = all(r["passed"] for r in result.values())
        all_valid = all_valid and passed
        print(f"  {atc}: {'PASS' if passed else 'FAIL'} -> {[k for k, v in result.items() if not v['passed']]}")
        output["validation"][atc] = result
    print(f"\nAll validations passed: {all_valid}")

    out_path = Path("data/reports/m5_optimization_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2, default=str), encoding="utf-8")
    print(f"\nFull results written to {out_path}")
    print(f"Total runtime: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
