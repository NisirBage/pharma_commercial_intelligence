import { ATC_CLASSES } from "../types/api";

/** Shared "Aggregate + one of the 8 observed ATC classes" selector
 * options — used by Demand Intelligence's Trends/Seasonality/Anomalies
 * tabs (whose endpoints omit `atc_class` for the aggregate; see
 * backend/app/services/sales_service.py, seasonality_service.py,
 * anomaly_service.py) and by the Forecasting page (which maps the same
 * option list onto a route change instead — see
 * docs/frontend-forecasting-intelligence-page.md for why "aggregate"
 * means something different again for that page's diagnostics call).
 * The "Aggregate" option's value is always `""`; `toAtcClassParam`
 * converts it back to `undefined` for call sites that omit the param. */
export const ATC_SELECT_OPTIONS = [
  { value: "", label: "Aggregate (all classes)" },
  ...ATC_CLASSES.map((atcClass) => ({ value: atcClass, label: atcClass })),
];

/** `""` (the Select's "Aggregate" sentinel) -> `undefined` (what every
 * hook/API module expects for "omit this filter"). */
export function toAtcClassParam(selectValue: string): string | undefined {
  return selectValue === "" ? undefined : selectValue;
}
